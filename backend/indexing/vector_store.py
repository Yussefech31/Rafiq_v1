"""Vector store abstraction for RAFIQ — FAISS and Qdrant backends."""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import numpy as np

from backend.config import get_settings, Chunk, SearchResult

logger = logging.getLogger(__name__)


class VectorStoreBase(ABC):
    """Abstract base class for vector store implementations."""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks with their embeddings to the store."""
        ...

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[SearchResult]:
        """Search for similar chunks. Returns list sorted by score descending."""
        ...

    @abstractmethod
    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks by their IDs."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return number of vectors in the store."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all vectors from the store."""
        ...


class FAISSStore(VectorStoreBase):
    """
    FAISS-based vector store with disk persistence.

    Stores:
    - {persist_dir}/{collection_name}/index.faiss  — the FAISS index
    - {persist_dir}/{collection_name}/metadata.json — chunk metadata keyed by FAISS int id
    """

    def __init__(self, collection_name: str):
        super().__init__(collection_name)
        settings = get_settings()
        self._persist_dir = Path(settings.faiss_persist_dir) / collection_name
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self._persist_dir / "index.faiss"
        self._meta_path = self._persist_dir / "metadata.json"

        self._dimension = settings.embedding_dimension
        self._index = None
        self._metadata: dict[int, dict] = {}
        self._next_id = 0

        self._load()

    def _load(self):
        """Load existing index and metadata from disk."""
        import faiss

        if self._index_path.exists() and self._meta_path.exists():
            try:
                self._index = faiss.read_index(str(self._index_path))
                with open(self._meta_path, 'r', encoding='utf-8') as f:
                    raw_meta = json.load(f)
                # JSON keys are strings, convert back to int
                self._metadata = {int(k): v for k, v in raw_meta.items()}
                self._next_id = max(self._metadata.keys(), default=-1) + 1
                logger.info(f"Loaded FAISS index '{self.collection_name}': "
                            f"{self._index.ntotal} vectors")
            except Exception as e:
                logger.warning(f"Failed to load FAISS index '{self.collection_name}': {e}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self):
        """Initialize an empty FAISS index."""
        import faiss
        self._index = faiss.IndexFlatIP(self._dimension)  # Inner product (cosine for normalized vecs)
        self._metadata = {}
        self._next_id = 0

    def _save(self):
        """Persist index and metadata to disk."""
        import faiss
        faiss.write_index(self._index, str(self._index_path))
        with open(self._meta_path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunk count ({len(chunks)}) != embedding count ({embeddings.shape[0]})")

        if embeddings.shape[0] == 0:
            return

        # Ensure float32
        embeddings = embeddings.astype(np.float32)

        # Add to FAISS index
        start_id = self._next_id
        self._index.add(embeddings)

        # Store metadata
        for i, chunk in enumerate(chunks):
            faiss_id = start_id + i
            self._metadata[faiss_id] = {
                'chunk_id': chunk.chunk_id,
                'text': chunk.text,
                'source_id': chunk.source_id,
                'title': chunk.title,
                'collection': self.collection_name,
                'metadata': chunk.metadata,
            }

        self._next_id = start_id + len(chunks)
        self._save()
        logger.info(f"Added {len(chunks)} chunks to '{self.collection_name}' "
                     f"(total: {self._index.ntotal})")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[SearchResult]:
        if self._index.ntotal == 0:
            return []

        query = query_embedding.astype(np.float32).reshape(1, -1)
        actual_k = min(top_k, self._index.ntotal)

        scores, indices = self._index.search(query, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for missing results
                continue
            meta = self._metadata.get(int(idx))
            if meta is None:
                continue
            results.append(SearchResult(
                chunk_id=meta['chunk_id'],
                text=meta['text'],
                score=float(score),
                source_id=meta['source_id'],
                title=meta['title'],
                collection=meta['collection'],
                metadata=meta.get('metadata', {}),
            ))

        return results

    def delete(self, chunk_ids: list[str]) -> None:
        """Delete by chunk_ids. Rebuilds the index (FAISS doesn't support in-place delete)."""
        import faiss

        ids_to_keep = {fid: meta for fid, meta in self._metadata.items()
                       if meta['chunk_id'] not in set(chunk_ids)}

        if len(ids_to_keep) == len(self._metadata):
            return  # Nothing to delete

        # Reconstruct index
        new_index = faiss.IndexFlatIP(self._dimension)
        new_metadata = {}
        new_id = 0

        for old_id in sorted(ids_to_keep.keys()):
            vec = self._index.reconstruct(old_id)
            new_index.add(vec.reshape(1, -1))
            new_metadata[new_id] = ids_to_keep[old_id]
            new_id += 1

        self._index = new_index
        self._metadata = new_metadata
        self._next_id = new_id
        self._save()
        logger.info(f"Deleted {len(chunk_ids)} chunks from '{self.collection_name}'")

    def count(self) -> int:
        return self._index.ntotal

    def clear(self) -> None:
        self._init_empty()
        self._save()
        logger.info(f"Cleared '{self.collection_name}'")


class QdrantStore(VectorStoreBase):
    """Qdrant-based vector store using the Python client."""

    def __init__(self, collection_name: str):
        super().__init__(collection_name)
        settings = get_settings()
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._dimension = settings.embedding_dimension

        # Create collection if it doesn't exist
        collections = [c.name for c in self._client.get_collections().collections]
        if collection_name not in collections:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self._dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for i, chunk in enumerate(chunks):
            points.append(PointStruct(
                id=hash(chunk.chunk_id) & 0x7FFFFFFFFFFFFFFF,  # Positive int64
                vector=embeddings[i].tolist(),
                payload={
                    'chunk_id': chunk.chunk_id,
                    'text': chunk.text,
                    'source_id': chunk.source_id,
                    'title': chunk.title,
                    'collection': self.collection_name,
                    'metadata': chunk.metadata,
                },
            ))

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=self.collection_name,
                points=points[i:i + batch_size],
            )

        logger.info(f"Added {len(chunks)} chunks to Qdrant '{self.collection_name}'")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[SearchResult]:
        results = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=top_k,
        )

        return [
            SearchResult(
                chunk_id=hit.payload['chunk_id'],
                text=hit.payload['text'],
                score=hit.score,
                source_id=hit.payload['source_id'],
                title=hit.payload['title'],
                collection=hit.payload.get('collection', self.collection_name),
                metadata=hit.payload.get('metadata', {}),
            )
            for hit in results
        ]

    def delete(self, chunk_ids: list[str]) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchAny

        self._client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="chunk_id", match=MatchAny(any=chunk_ids))]
            ),
        )
        logger.info(f"Deleted {len(chunk_ids)} chunks from Qdrant '{self.collection_name}'")

    def count(self) -> int:
        info = self._client.get_collection(self.collection_name)
        return info.points_count

    def clear(self) -> None:
        from qdrant_client.models import Distance, VectorParams
        self._client.delete_collection(self.collection_name)
        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self._dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Cleared Qdrant '{self.collection_name}'")


# ── Factory ────────────────────────────────────────────────────────

_stores: dict[str, VectorStoreBase] = {}


def get_vector_store(collection_name: str) -> VectorStoreBase:
    """
    Factory: return the appropriate vector store based on settings.

    Caches store instances by collection name.
    """
    if collection_name not in _stores:
        settings = get_settings()

        if settings.vector_store_backend == "qdrant":
            try:
                store = QdrantStore(collection_name)
                logger.info(f"Using Qdrant for '{collection_name}'")
            except Exception as e:
                logger.warning(f"Qdrant unavailable ({e}), falling back to FAISS")
                store = FAISSStore(collection_name)
        else:
            store = FAISSStore(collection_name)
            logger.info(f"Using FAISS for '{collection_name}'")

        _stores[collection_name] = store

    return _stores[collection_name]
