"""
backend.retrieval.search
~~~~~~~~~~~~~~~~~~~~~~~~
Recherche sémantique sur les vector stores.
Phase 1 : seul docs_store est interrogé.
Phase 2 : les deux stores seront interrogés en parallèle.
"""

from backend.config import SearchResult
from backend.indexing.vector_store import get_vector_store
from backend.indexing.embed import get_embedder


def search_docs(query: str, top_k: int = 5) -> list[SearchResult]:
    """Search docs_store only."""
    embedder = get_embedder()
    query_emb = embedder.embed_single(query)
    store = get_vector_store("docs_store")
    return store.search(query_emb, top_k=top_k)


def search_qa(query: str, top_k: int = 5) -> list[SearchResult]:
    """Search qa_store only. Returns empty list if qa_store is empty/missing."""
    embedder = get_embedder()
    query_emb = embedder.embed_single(query)
    store = get_vector_store("qa_store")
    try:
        return store.search(query_emb, top_k=top_k)
    except Exception:
        return []


def search_all(
    query: str, top_k: int = 5
) -> tuple[list[SearchResult], list[SearchResult]]:
    """Search both stores. Returns (docs_results, qa_results)."""
    return search_docs(query, top_k), search_qa(query, top_k)
