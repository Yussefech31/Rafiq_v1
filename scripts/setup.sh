#!/bin/bash
# RAFIQ Setup Script
# Creates venv, installs deps, starts vector store, builds initial index.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "============================================"
echo "  RAFIQ — Setup Script"
echo "============================================"
echo ""

# 1. Create virtual environment
echo "--- Step 1: Python virtual environment ---"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Created .venv"
else
    echo ".venv already exists"
fi

# Activate
source .venv/bin/activate
echo "Activated .venv (Python: $(python --version))"

# 2. Install dependencies
echo ""
echo "--- Step 2: Installing dependencies ---"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Dependencies installed."

# 3. Create data directories
echo ""
echo "--- Step 3: Creating data directories ---"
mkdir -p data/raw data/processed data/faiss_index data/documents
echo "Data directories created."

# 4. Copy .env if needed
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Copied .env.example → .env (edit ANTHROPIC_API_KEY!)"
    fi
fi

# 5. Vector store backend
echo ""
echo "--- Step 4: Vector store setup ---"
if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    echo "Docker detected. Starting Qdrant..."
    docker-compose up -d qdrant 2>/dev/null || docker compose up -d qdrant 2>/dev/null || true

    # Check if Qdrant is accessible
    sleep 3
    if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "Qdrant is running on port 6333"
        # Update .env to use qdrant
        sed -i 's/VECTOR_STORE_BACKEND=faiss/VECTOR_STORE_BACKEND=qdrant/' .env 2>/dev/null || true
        echo "VECTOR_STORE_BACKEND set to qdrant"
    else
        echo "Qdrant failed to start. Falling back to FAISS."
    fi
else
    echo "Docker not available. Using FAISS (local persistence)."
    echo "VECTOR_STORE_BACKEND=faiss (in .env)"
fi

# 6. Build initial index
echo ""
echo "--- Step 5: Building initial index ---"
python -m backend.indexing.build_index

echo ""
echo "============================================"
echo "  RAFIQ Setup Complete!"
echo "============================================"
echo ""
echo "To start the API:"
echo "  source .venv/bin/activate"
echo "  uvicorn backend.main:app --reload --port 8000"
echo ""
echo "Then visit:"
echo "  API docs:  http://localhost:8000/docs"
echo "  Frontend:  http://localhost:8000/static/index.html"
echo ""
