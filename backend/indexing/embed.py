"""Embedding wrapper for RAFIQ — lazy-loaded sentence-transformers model."""
import logging
from typing import Optional

import numpy as np

from backend.config import get_settings

logger = logging.getLogger(__name__)


class Embedder:
    """Wrapper around a sentence-transformers model for text embedding."""

    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._model = None
        self._dimension = None

    def _load_model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            # Get dimension from a test embedding
            test = self._model.encode(["test"], convert_to_numpy=True)
            self._dimension = test.shape[1]
            logger.info(f"Model loaded. Dimension: {self._dimension}")

    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Embed a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (N, dimension).
        """
        self._load_model()
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        logger.info(f"Embedding {len(texts)} texts...")
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 50,
            batch_size=64,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        return embeddings.astype(np.float32)

    def embed_single(self, text: str) -> np.ndarray:
        """
        Embed a single text.

        Args:
            text: Text string to embed.

        Returns:
            numpy array of shape (dimension,).
        """
        result = self.embed([text])
        return result[0]

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension


# ── Singleton ──────────────────────────────────────────────────────

_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Return a lazy-loaded singleton Embedder."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
