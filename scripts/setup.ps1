# RAFIQ Setup Script (PowerShell)
# Creates venv, installs deps, starts vector store, builds initial index.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  RAFIQ — Setup Script (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Create virtual environment
Write-Host "--- Step 1: Python virtual environment ---" -ForegroundColor Yellow
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created .venv"
} else {
    Write-Host ".venv already exists"
}

# Activate
& .\.venv\Scripts\Activate.ps1
Write-Host "Activated .venv (Python: $(python --version))"

# 2. Install dependencies
Write-Host ""
Write-Host "--- Step 2: Installing dependencies ---" -ForegroundColor Yellow
pip install --upgrade pip -q
pip install -r requirements.txt -q
Write-Host "Dependencies installed."

# 3. Create data directories
Write-Host ""
Write-Host "--- Step 3: Creating data directories ---" -ForegroundColor Yellow
$dirs = @("data\raw", "data\processed", "data\faiss_index", "data\documents")
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}
Write-Host "Data directories created."

# 4. Copy .env if needed
if (-Not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Copied .env.example → .env (edit ANTHROPIC_API_KEY!)" -ForegroundColor Red
    }
}

# 5. Vector store backend
Write-Host ""
Write-Host "--- Step 4: Vector store setup ---" -ForegroundColor Yellow
$dockerAvailable = $false
try {
    docker info 2>$null | Out-Null
    $dockerAvailable = $true
} catch {
    $dockerAvailable = $false
}

if ($dockerAvailable) {
    Write-Host "Docker detected. Starting Qdrant..."
    try {
        docker-compose up -d qdrant 2>$null
        Start-Sleep -Seconds 3
        $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -ErrorAction SilentlyContinue
        Write-Host "Qdrant is running on port 6333" -ForegroundColor Green
        (Get-Content .env) -replace 'VECTOR_STORE_BACKEND=faiss', 'VECTOR_STORE_BACKEND=qdrant' | Set-Content .env
        Write-Host "VECTOR_STORE_BACKEND set to qdrant"
    } catch {
        Write-Host "Qdrant failed to start. Using FAISS." -ForegroundColor Yellow
    }
} else {
    Write-Host "Docker not available. Using FAISS (local persistence)."
}

# 6. Build initial index
Write-Host ""
Write-Host "--- Step 5: Building initial index ---" -ForegroundColor Yellow
python -m backend.indexing.build_index

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  RAFIQ Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the API:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn backend.main:app --reload --port 8000"
Write-Host ""
Write-Host "Then visit:"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Frontend:  http://localhost:8000/static/index.html"
Write-Host ""
