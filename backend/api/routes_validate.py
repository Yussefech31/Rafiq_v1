"""POST /api/validate — validate an answer, write back to qa_store, optionally generate document."""

import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.validation.writeback import writeback_validated_answer
from backend.documents.render import render_docx, convert_to_pdf
from backend.validation.models import get_db_connection

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
    """Validate an answer, store it in the database and vector store, and optionally generate document."""
    try:
        logger.info(f"Validate called for question: {request.question[:80]}...")

        # 1. Write validated answer to SQLite and qa_store
        qa_id = writeback_validated_answer(
            question=request.question,
            validated_answer=request.validated_answer,
            validator_name=request.validator_name,
            original_confidence=request.confidence,
            original_regime=request.regime,
            sources=request.sources,
            original_answer=request.original_answer,
        )

        doc_id = None
        message = "Réponse validée et enregistrée avec succès."

        # 2. Optionally generate document
        if request.generate_document:
            logger.info("Generating Word document for the validated response...")
            try:
                # Render Word document
                docx_path = render_docx(
                    question=request.question,
                    answer=request.validated_answer,
                    objet="Réponse officielle",
                    signature=request.validator_name
                )

                doc_id = f"doc_{uuid.uuid4().hex[:12]}"
                final_path = docx_path
                doc_format = "docx"

                # Try converting to PDF (will fall back to docx if LibreOffice is missing)
                try:
                    logger.info("Attempting PDF conversion...")
                    pdf_path = convert_to_pdf(docx_path)
                    final_path = pdf_path
                    doc_format = "pdf"
                    logger.info(f"Converted successfully to PDF: {pdf_path}")
                except FileNotFoundError:
                    logger.warning("LibreOffice not found. Sticking to DOCX format.")
                    message += " (Note: Exporté au format Word uniquement car LibreOffice n'est pas installé sur le serveur)."
                except Exception as pdf_err:
                    logger.error(f"PDF conversion failed: {pdf_err}", exc_info=True)
                    message += f" (Note: Échec de la conversion PDF: {pdf_err}. Fichier Word disponible)."

                # Log document in SQLite database
                conn = get_db_connection()
                try:
                    conn.execute(
                        """
                        INSERT INTO document_logs (doc_id, qa_id, format, filepath, created_date)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            qa_id,
                            doc_format,
                            final_path,
                            datetime.now().isoformat()
                        )
                    )
                    conn.commit()
                    logger.info(f"Recorded document {doc_id} in SQLite document_logs.")
                finally:
                    conn.close()

            except Exception as doc_err:
                logger.error(f"Document generation failed: {doc_err}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Échec de la génération du document: {str(doc_err)}")

        return ValidateResponse(
            status="success",
            qa_id=qa_id,
            document_id=doc_id,
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /validate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
