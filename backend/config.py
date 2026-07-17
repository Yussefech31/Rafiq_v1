"""Central configuration and shared types for RAFIQ."""
import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    # API keys
    anthropic_api_key: str = ""

    # Models
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    llm_model: str = "claude-sonnet-4-6"

    # Vector store
    vector_store_backend: str = "faiss"  # 'qdrant' or 'faiss'
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    faiss_persist_dir: str = str(_PROJECT_ROOT / "data" / "faiss_index")

    # Confidence thresholds
    confidence_high_threshold: float = 0.85
    confidence_low_threshold: float = 0.55

    # Fusion weights
    qa_store_weight: float = 0.6
    docs_store_weight: float = 0.4

    # Database
    sqlite_db_path: str = str(_PROJECT_ROOT / "data" / "rafiq.db")

    # Document generation
    documents_output_dir: str = str(_PROJECT_ROOT / "data" / "documents")
    template_path: str = str(_PROJECT_ROOT / "backend" / "documents" / "templates" / "reponse_template.docx")

    # Paths
    raw_data_dir: str = str(_PROJECT_ROOT / "data" / "raw")
    processed_data_dir: str = str(_PROJECT_ROOT / "data" / "processed")

    # Embedding dimension (paraphrase-multilingual-MiniLM-L12-v2 = 384)
    embedding_dimension: int = 384

    # Retrieval
    top_k: int = 5

    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


# ── Shared data types ──────────────────────────────────────────────

class ConfidenceRegime(str, Enum):
    """Three-regime confidence routing."""
    HIGH = "high"       # Near-identical validated precedent in qa_store
    MEDIUM = "medium"   # Relevant docs found, no exact precedent
    LOW = "low"         # Nothing sufficiently relevant → abstain


@dataclass
class Chunk:
    """A text chunk ready for embedding and indexing."""
    chunk_id: str
    text: str
    source_id: str
    title: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single result from vector search."""
    chunk_id: str
    text: str
    score: float
    source_id: str
    title: str
    collection: str  # 'docs' or 'qa'
    metadata: dict = field(default_factory=dict)


@dataclass
class FusedResult:
    """Combined results from both stores with confidence assessment."""
    results: list  # List[SearchResult]
    top_score: float
    agreement_score: float
    confidence: float
    regime: ConfidenceRegime
    qa_match: Optional[SearchResult] = None


@dataclass
class GenerationResult:
    """Final answer output from the generation pipeline."""
    answer: str
    sources: list  # List of {chunk_id, text_snippet, collection} dicts
    confidence: float
    regime: str
    abstained: bool
    qa_match_id: Optional[str] = None
