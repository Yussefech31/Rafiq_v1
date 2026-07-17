"""
GET /api/document/{doc_id} — download generated documents.
Phase 1: stub. Phase 3: full implementation.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/document/{doc_id}")
async def get_document(doc_id: str, format: str = "docx"):
    """
    Download a generated document by ID.

    Phase 1: returns 501 Not Implemented.
    Phase 3: retrieves and serves the document file.
    """
    # TODO Phase 3: look up doc_id in document_logs table,
    # return the file via FileResponse
    raise HTTPException(
        status_code=501,
        detail="Document generation not yet implemented (Phase 3)."
    )
