"""
POST /api/validate — validate an answer, write back to qa_store, optionally generate document.
Phase 1: stub implementation. Phase 3: full validation loop.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ValidateRequest(BaseModel):
    question: str
    original_answer: str
    validated_answer: str
    validator_name: str = "expert"
    confidence: float = 0.0
    regime: str = "medium"
    sources: list[dict] = []
    generate_document: bool = False


class ValidateResponse(BaseModel):
    status: str
    qa_id: Optional[str] = None
    document_id: Optional[str] = None
    message: str


@router.post("/validate", response_model=ValidateResponse)
async def validate(request: ValidateRequest):
    """
    Validate an answer and write it back to qa_store.

    Phase 1: stub — returns placeholder response.
    Phase 3: full writeback + document generation.
    """
    # TODO Phase 3: full implementation
    # 1. Write validated answer to SQLite (validation/models.py)
    # 2. Embed and write to qa_store (validation/writeback.py)
    # 3. Optionally generate document (documents/render.py)
    logger.info(f"Validate stub called for question: {request.question[:80]}...")
    return ValidateResponse(
        status="stub",
        qa_id=None,
        document_id=None,
        message="Validation endpoint is a Phase 1 stub. Full implementation in Phase 3."
    )
