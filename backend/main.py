"""FastAPI application entrypoint for RAFIQ."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import get_settings

app = FastAPI(
    title="RAFIQ",
    description="RAG system for administrative questions — Ministère de la Transition Numérique",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

# Import and include API routers
from backend.api.routes_ask import router as ask_router
from backend.api.routes_validate import router as validate_router
from backend.api.routes_documents import router as documents_router
from backend.validation.models import init_db

# Initialize SQLite database tables
init_db()

app.include_router(ask_router, prefix="/api", tags=["ask"])
app.include_router(validate_router, prefix="/api", tags=["validate"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "ok",
        "project": "RAFIQ",
        "vector_store_backend": settings.vector_store_backend,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
    }


@app.get("/")
async def root():
    """Redirect to frontend."""
    from fastapi.responses import FileResponse
    frontend_path = _FRONTEND_DIR / "index.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path))
    return {"message": "RAFIQ API is running. Visit /docs for API documentation."}
