"""GET /api/document/{doc_id} — download generated documents."""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.validation.models import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/document/{doc_id}")
async def get_document(doc_id: str):
    """Retrieve and serve the generated document file by its qa_id or doc_id."""
    logger.info(f"Retrieving document for ID: {doc_id}")

    conn = get_db_connection()
    try:
        # Match against either doc_id or qa_id to support flexible retrieval
        row = conn.execute(
            """
            SELECT filepath, format FROM document_logs
            WHERE qa_id = ? OR doc_id = ?
            ORDER BY created_date DESC LIMIT 1
            """,
            (doc_id, doc_id)
        ).fetchone()
    except Exception as e:
        logger.error(f"Database query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database query failed.")
    finally:
        conn.close()

    if not row:
        logger.warning(f"No document record found for ID: {doc_id}")
        raise HTTPException(status_code=404, detail="Document record not found.")

    filepath = row["filepath"]
    doc_format = row["format"]
    path_obj = Path(filepath)

    if not path_obj.exists():
        logger.error(f"Physical file not found on disk: {filepath}")
        raise HTTPException(status_code=404, detail="Document file not found on server.")

    # Determine media type
    if doc_format == "pdf":
        media_type = "application/pdf"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    logger.info(f"Serving document file: {filepath} ({doc_format})")
    return FileResponse(
        path=str(path_obj),
        media_type=media_type,
        filename=path_obj.name
    )
