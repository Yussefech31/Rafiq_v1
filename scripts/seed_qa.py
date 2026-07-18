"""Script to seed the SQLite database and qa_store vector index with expert Q&As.

Usage:
    python -m scripts.seed_qa
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import Chunk
from backend.indexing.embed import get_embedder
from backend.indexing.vector_store import get_vector_store
from backend.validation.models import get_db_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def seed_data():
    logger.info("Initializing database...")
    init_db()

    qa_items = [
        {
            "qa_id": "qa_seed_001",
            "question": "Quels sont les documents nécessaires pour obtenir un certificat de résidence ?",
            "original_answer": "Pour obtenir un certificat de résidence, il faut des documents.",
            "validated_answer": (
                "Pour obtenir un certificat de résidence au Maroc, vous devez fournir :\n"
                "1. Une copie de la carte d'identité nationale (CNI).\n"
                "2. Un justificatif de domicile récent (facture d'eau, d'électricité ou contrat de bail).\n"
                "3. Deux photos d'identité récentes.\n"
                "4. Le formulaire de demande de certificat dûment rempli."
            ),
            "validator_name": "Dr. Amina Benali",
            "original_confidence": 0.88,
            "original_regime": "high",
            "sources": [{"chunk_id": "c1", "text": "Certificat de résidence pièces", "collection": "docs"}]
        },
        {
            "qa_id": "qa_seed_002",
            "question": "Comment renouveler le passeport biométrique ?",
            "original_answer": "Le renouvellement se fait en ligne ou au consulat.",
            "validated_answer": (
                "Le renouvellement du passeport biométrique s'effectue en suivant ces étapes :\n"
                "1. Remplir le formulaire de demande en ligne sur le site officiel (passeport.ma).\n"
                "2. Acheter le timbre fiscal (actuellement de 500 DHS).\n"
                "3. Préparer les pièces : CNI (ou copie), l'ancien passeport, et deux photos d'identité conformes aux normes.\n"
                "4. Déposer le dossier auprès de l'autorité administrative locale compétente (Annexe administrative ou Caïdat)."
            ),
            "validator_name": "Youssef Alaoui",
            "original_confidence": 0.92,
            "original_regime": "high",
            "sources": [{"chunk_id": "c2", "text": "Passeport biométrique étapes", "collection": "docs"}]
        },
        {
            "qa_id": "qa_seed_003",
            "question": "ما هي الوثائق المطلوبة للحصول على شهادة السكنى؟",
            "original_answer": "شهادة السكنى تتطلب بعض الوثائق الشخصية وإثبات السكن.",
            "validated_answer": (
                "للحصول على شهادة السكنى بالمغرب، يجب تقديم الوثائق التالية :\n"
                "1. نسخة من بطاقة التعريف الوطنية الإلكترونية.\n"
                "2. إثبات السكن (فاتورة الماء أو الكهرباء باسم المعني بالأمر، أو عقد الكراء، أو شهادة الملكية).\n"
                "3. صورتان شمسيتان حديثتان.\n"
                "4. ملء استمارة الطلب المخصصة لذلك."
            ),
            "validator_name": "Dr. Amina Benali",
            "original_confidence": 0.90,
            "original_regime": "high",
            "sources": [{"chunk_id": "c3", "text": "شهادة السكنى الوثائق", "collection": "docs"}]
        },
        {
            "qa_id": "qa_seed_004",
            "question": "كيف يمكن تجديد جواز السفر البيومتري؟",
            "original_answer": "تجديد الجواز يتطلب التمبر والبطاقة الوطنية.",
            "validated_answer": (
                "يتم تجديد جواز السفر البيومتري المغربي عبر الإجراءات التالية :\n"
                "1. تعبئة استمارة الطلب عبر البوابة الإلكترونية المخصصة (passeport.ma).\n"
                "2. اقتناء التمبر الإلكتروني (بقيمة 500 درهم).\n"
                "3. تقديم البطاقة الوطنية للتعريف الإلكترونية (أو نسخة منها) وجواز السفر القديم.\n"
                "4. إرفاق صورتين فوتوغرافيتين حديثتين توافقان المعايير المطلوبة.\n"
                "5. إيداع الملف لدى الملحقة الإدارية أو القيادة التابع لها مقر السكن."
            ),
            "validator_name": "Youssef Alaoui",
            "original_confidence": 0.95,
            "original_regime": "high",
            "sources": [{"chunk_id": "c4", "text": "جواز السفر البيومتري المغربي", "collection": "docs"}]
        }
    ]

    conn = get_db_connection()
    try:
        # Seed SQLite database
        for item in qa_items:
            date_str = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO validated_answers (
                    qa_id, question, original_answer, validated_answer,
                    validator_name, validation_date, original_confidence,
                    original_regime, sources, written_back, writeback_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["qa_id"],
                    item["question"],
                    item["original_answer"],
                    item["validated_answer"],
                    item["validator_name"],
                    date_str,
                    item["original_confidence"],
                    item["original_regime"],
                    json.dumps(item["sources"]),
                    1,
                    date_str
                )
            )
        conn.commit()
        logger.info(f"Seeded {len(qa_items)} records into validated_answers table.")
    finally:
        conn.close()

    # Seed Vector Store (qa_store)
    logger.info("Seeding qa_store vector index...")
    qa_store = get_vector_store("qa_store")
    qa_store.clear()  # Start fresh for seed

    embedder = get_embedder()
    chunks = []
    for item in qa_items:
        # Index question text only; answer lives in metadata for reuse
        chunks.append(
            Chunk(
                chunk_id=item["qa_id"],
                text=item["question"],
                source_id=item["qa_id"],
                title=f"Precedent: {item['question']}",
                metadata={
                    "question": item["question"],
                    "validated_answer": item["validated_answer"],
                    "validator_name": item["validator_name"]
                }
            )
        )

    texts = [c.text for c in chunks]
    embeddings = embedder.embed(texts)
    qa_store.add_chunks(chunks, embeddings)
    logger.info(f"Seeded {qa_store.count()} vectors into qa_store.")
    logger.info("Seeding completed successfully.")


if __name__ == "__main__":
    seed_data()
