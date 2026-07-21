"""Write validated answers back into qa_store and SQLite database."""

import json
import uuid
import logging
from datetime import datetime

from backend.config import get_settings, Chunk
from backend.indexing.embed import get_embedder
from backend.indexing.vector_store import get_vector_store
from backend.validation.models import get_db_connection

logger = logging.getLogger(__name__)


def writeback_validated_answer(
    question: str,
    validated_answer: str,
    validator_name: str,
    original_confidence: float,
    original_regime: str,
    sources: list[dict],
    original_answer: str = "",
) -> str:
    """Write a validated answer into qa_store and SQLite. Returns qa_id."""
    qa_id = f"qa_{uuid.uuid4().hex[:12]}"
    date_str = datetime.now().isoformat()

    logger.info(f"Writing back validated answer for question: {question[:60]}... (qa_id: {qa_id})")

    # 1. Store in SQLite database
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO validated_answers (
                qa_id, question, original_answer, validated_answer,
                validator_name, validation_date, original_confidence,
                original_regime, sources, written_back, writeback_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                qa_id,
                question,
                original_answer,
                validated_answer,
                validator_name,
                date_str,
                original_confidence,
                original_regime,
                json.dumps(sources),
                1,  # written_back
                date_str
            )
        )
        conn.commit()
        logger.info(f"Recorded QA record {qa_id} in SQLite validated_answers.")
    except Exception as e:
        logger.error(f"Failed to write to SQLite validated_answers: {e}", exc_info=True)
        raise e
    finally:
        conn.close()

    # 2. Add to qa_store Vector Database
    try:
        chunk = Chunk(
            chunk_id=qa_id,
            text=question,
            source_id=qa_id,
            title=f"Precedent: {question}",
            metadata={
                "question": question,
                "validated_answer": validated_answer,
                "validator_name": validator_name,
                "validation_date": date_str
            }
        )

        embedder = get_embedder()
        embeddings = embedder.embed([chunk.text])

        store = get_vector_store("qa_store")
        store.add_chunks([chunk], embeddings)
        logger.info(f"Added and embedded QA record {qa_id} into qa_store vector index.")
    except Exception as e:
        logger.error(f"Failed to add QA record to qa_store: {e}", exc_info=True)
        raise e

    return qa_id
