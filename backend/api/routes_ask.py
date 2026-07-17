"""
POST /api/ask endpoint — wires the full RAFIQ RAG pipeline.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from backend.retrieval.search import search_all
from backend.retrieval.fuse import fuse_results
from backend.retrieval.confidence import compute_confidence
from backend.generation.generate import generate_answer

logger = logging.getLogger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
    regime: str  # 'high', 'medium', 'low'
    abstained: bool
    qa_match_id: Optional[str] = None


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Ask a question to RAFIQ.

    Pipeline: search → fuse → confidence → generate/abstain.

    Returns cited answer with confidence regime.
    """
    try:
        logger.info(f"Question received: {request.question[:100]}...")

        # 1. Search both stores
        docs_results, qa_results = search_all(request.question, request.top_k)
        logger.info(f"Search results: {len(docs_results)} docs, {len(qa_results)} qa")

        # 2. Fuse results
        fused = fuse_results(docs_results, qa_results)

        # 3. Compute confidence and route
        fused = compute_confidence(fused)
        logger.info(f"Confidence: {fused.confidence:.3f}, Regime: {fused.regime.value}")

        # 4. Generate (or abstain)
        result = generate_answer(request.question, fused)

        return AskResponse(
            answer=result.answer,
            sources=result.sources,
            confidence=result.confidence,
            regime=result.regime,
            abstained=result.abstained,
            qa_match_id=result.qa_match_id,
        )
    except Exception as e:
        logger.error(f"Error in /ask: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
