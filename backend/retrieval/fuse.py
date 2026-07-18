"""
backend.retrieval.fuse
~~~~~~~~~~~~~~~~~~~~~~
Fusion pondérée des résultats des deux stores.
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

    Weighted scores are used only for ranking merged results.
    Raw (unweighted) scores drive confidence and qa_match detection.
    """
    settings = get_settings()
    all_results: list[SearchResult] = []

    # Weight and merge results (ranking only)
    for r in docs_results:
        all_results.append(
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score * settings.docs_store_weight,
                source_id=r.source_id,
                title=r.title,
                collection="docs",
                metadata={**r.metadata, "raw_score": r.score},
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
                metadata={**r.metadata, "raw_score": r.score},
            )
        )

    all_results.sort(key=lambda x: x.score, reverse=True)

    # Best QA match based on raw similarity
    qa_match = None
    if qa_results:
        best_qa = max(qa_results, key=lambda x: x.score)
        if best_qa.score >= settings.qa_match_threshold:
            qa_match = best_qa

    # Confidence from raw scores across both stores
    raw_scores = [r.score for r in docs_results] + [r.score for r in qa_results]
    raw_scores.sort(reverse=True)
    top_scores = raw_scores[:3] if raw_scores else [0.0]
    top_score = top_scores[0]
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
