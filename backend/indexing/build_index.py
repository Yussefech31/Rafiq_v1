"""CLI script: build the docs_store index from raw Excel data.

Usage:
    python -m backend.indexing.build_index
"""
import logging
import shutil
import sys
import time
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import get_settings
from backend.ingestion.chunk import chunk_all
from backend.indexing.embed import get_embedder
from backend.indexing.vector_store import get_vector_store

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def copy_data_files():
    """Copy Excel files from parent workspace into data/raw/ if they exist."""
    settings = get_settings()
    raw_dir = Path(settings.raw_data_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Parent workspace (one level up from rafiq/)
    workspace = _PROJECT_ROOT.parent

    files_to_copy = [
        'data_apres_split.xlsx',
        'BD_idarati_consolidée_190126.xlsx',
    ]

    for filename in files_to_copy:
        src = workspace / filename
        dst = raw_dir / filename
        if src.exists() and not dst.exists():
            shutil.copy2(str(src), str(dst))
            logger.info(f"Copied {filename} to data/raw/")
        elif src.exists():
            logger.info(f"{filename} already in data/raw/")
        else:
            logger.info(f"{filename} not found in workspace ({workspace})")

    # Also check in a 'data' subdirectory of workspace
    data_dir = workspace / 'data'
    if data_dir.exists():
        for xlsx in data_dir.glob('*.xlsx'):
            dst = raw_dir / xlsx.name
            if not dst.exists():
                shutil.copy2(str(xlsx), str(dst))
                logger.info(f"Copied {xlsx.name} from workspace/data/")


def build_index():
    """Main pipeline: raw Excel → chunks → embeddings → vector store."""
    settings = get_settings()
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("RAFIQ Index Builder")
    logger.info("=" * 60)
    logger.info(f"Vector store backend: {settings.vector_store_backend}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Raw data dir: {settings.raw_data_dir}")

    # Step 0: Copy data files if available
    logger.info("\n--- Step 0: Copying data files ---")
    copy_data_files()

    # Step 1: Chunk all raw data
    logger.info("\n--- Step 1: Chunking raw data ---")
    chunks = chunk_all(settings.raw_data_dir)

    # Apply chunk indexing limit for speed in Phase 1 / MVP execution
    import os
    limit = os.getenv("INDEX_LIMIT")
    if limit:
        if limit.lower() != "all":
            try:
                limit_val = int(limit)
                logger.info(f"INDEX_LIMIT set to {limit_val}. Limiting index to the first {limit_val} chunks.")
                chunks = chunks[:limit_val]
            except ValueError:
                pass
    else:
        logger.info("No INDEX_LIMIT environment variable found. Defaulting to 2000 chunks for fast MVP execution.")
        chunks = chunks[:2000]

    if not chunks:
        logger.warning("No chunks produced! Check that xlsx files exist in data/raw/")
        logger.info("Creating data/raw/ directory. Place xlsx files there and re-run.")
        Path(settings.raw_data_dir).mkdir(parents=True, exist_ok=True)
        return

    logger.info(f"Total chunks: {len(chunks)}")

    # Step 2: Embed all chunks
    logger.info("\n--- Step 2: Embedding chunks ---")
    embedder = get_embedder()
    texts = [chunk.text for chunk in chunks]
    embeddings = embedder.embed(texts)
    logger.info(f"Embeddings shape: {embeddings.shape}")

    # Step 3: Store in docs_store
    logger.info("\n--- Step 3: Storing in docs_store ---")
    store = get_vector_store("docs_store")
    store.clear()  # Fresh build
    store.add_chunks(chunks, embeddings)

    # Also ensure qa_store collection exists (empty for now)
    logger.info("\n--- Step 4: Initializing qa_store (empty) ---")
    qa_store = get_vector_store("qa_store")
    logger.info(f"qa_store ready ({qa_store.count()} vectors)")

    # Report
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("BUILD COMPLETE")
    logger.info(f"  Chunks indexed: {store.count()}")
    logger.info(f"  Embedding dimension: {embedder.dimension}")
    logger.info(f"  Backend: {settings.vector_store_backend}")
    logger.info(f"  Time: {elapsed:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    build_index()
