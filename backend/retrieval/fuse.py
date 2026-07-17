"""
backend.retrieval.fuse
~~~~~~~~~~~~~~~~~~~~~~
Fusion pondérée des résultats des deux stores.
Phase 1 (stub) : encapsule uniquement les résultats docs dans un FusedResult.
Phase 2 : fusion pondérée favorisant qa_store sur les correspondances proches.
"""

from backend.config import (
    get_settings,
    SearchResult,
    FusedResult,
    ConfidenceRegime,
)


def fuse_results(
    docs_results: list[SearchResult],
    qa_results: list[SearchResult],
) -> FusedResult:
    """
    Fuse results from docs_store and qa_store.
    Phase 1: only uses docs_results (qa_results will be empty).
    Phase 2: weighted fusion favoring qa_store on close matches.
    """
    settings = get_settings()
    all_results: list[SearchResult] = []

    # Weight and merge results
    for r in docs_results:
        all_results.append(
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score * settings.docs_store_weight,
                source_id=r.source_id,
                title=r.title,
                collection="docs",
                metadata=r.metadata,
            )
        )
    for r in qa_results:
        all_results.append(
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score * settings.qa_store_weight,
                source_id=r.source_id,
                title=r.title,
                collection="qa",
                metadata=r.metadata,
            )
        )

    # Sort by weighted score descending
    all_results.sort(key=lambda x: x.score, reverse=True)

    # Find best QA match (if any)
    qa_match = None
    if qa_results:
        best_qa = max(qa_results, key=lambda x: x.score)
        if best_qa.score >= settings.confidence_high_threshold:
            qa_match = best_qa

    # Compute agreement: how similar are top-3 scores
    top_scores = (
        [r.score for r in all_results[:3]] if all_results else [0.0]
    )
    top_score = top_scores[0] if top_scores else 0.0
    agreement = (
        1.0 - (max(top_scores) - min(top_scores))
        if len(top_scores) > 1
        else 0.5
    )

    return FusedResult(
        results=all_results[: settings.top_k],
        top_score=top_score,
        agreement_score=agreement,
        confidence=0.0,  # Will be set by confidence.py
        regime=ConfidenceRegime.MEDIUM,  # Will be set by confidence.py
        qa_match=qa_match,
    )
