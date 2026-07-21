# RAFIQ

**Réponse Automatisée Fondée sur l'Intelligence documentaire et la Qualité experte**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Status](https://img.shields.io/badge/status-in%20development-yellow)
![License](https://img.shields.io/badge/license-internal-lightgrey)

A grounded, human-validated RAG system for administrative Q&A, built for the *Ministère de la Transition Numérique* (Morocco). RAFIQ answers recurring administrative questions with cited, source-grounded responses, routes uncertain cases to human experts instead of guessing, learns from every expert validation, and produces signable Word/PDF correspondence from the final answer.

---

## Table of contents

- [Why RAFIQ](#why-rafiq)
- [Key features](#key-features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Data](#data)
- [Evaluation](#evaluation)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why RAFIQ

Most RAG chatbots stop at "retrieve a chunk, generate an answer." RAFIQ is built around three things a generic RAG pipeline doesn't do:

| | Generic RAG | RAFIQ |
|---|---|---|
| Knowledge sources | One flat document index | **Two memories**: regulatory documentation (`docs_store`) and expert-validated precedent (`qa_store`), queried and weighted separately |
| Uncertainty | Always generates an answer | **Confidence-gated routing**: reuse a validated precedent, generate a grounded answer with citations, or **abstain** and escalate to a human when nothing is reliable enough |
| Improvement over time | Static until re-indexed or fine-tuned | **Capitalization loop**: every expert-validated answer is written back into `qa_store`, so the system answers more from trusted precedent the more it's used — no retraining required |
| Final output | Text in a chat window | A formal **Word/PDF document** (header, objet, question, corps, date, signature) auto-filled from the validated answer, editable before export |

The result is a system designed to be *trustworthy by construction*: it cites everything it says, refuses to answer when it isn't confident, and gets measurably better with expert use rather than degrading or hallucinating on edge cases.

## Key features

- **Grounded generation** — every claim in a generated answer is tied to a source chunk or a validated precedent; nothing is asserted without a citation.
- **Three-regime response**: `high` confidence reuses a validated precedent, `medium` generates a fresh grounded answer, `low` abstains and escalates.
- **Expert validation workflow** — every answer (auto-generated or abstained) can be reviewed, corrected, and validated by a human before anything is finalized.
- **Self-capitalizing knowledge base** — validated answers feed back into `qa_store`, continuously improving future retrieval without model retraining.
- **Formal document generation** — one click turns a validated answer into a ministry-formatted Word document and PDF, ready for signature.
- **Bilingual** — built to handle Arabic and French administrative content.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (HTML/JS)                       │
│                  [Ask View]    [Validate View]                  │
└──────────────┬──────────────────────────┬───────────────────────┘
               │ POST /api/ask            │ POST /api/validate
               ▼                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌────────────┐   ┌───────────┐    │
│  │ Ingestion│──▶│ Indexing │──▶│ docs_store │   │ qa_store  │    │
│  │ (Excel)  │   │ (Embed)  │   │ (FAISS/    │   │ (FAISS/   │    │
│  └──────────┘   └──────────┘   │  Qdrant)   │   │  Qdrant)  │    │
│                                 └─────┬──────┘   └─────┬─────┘    │
│                                       │                │          │
│                                       ▼                ▼          │
│                              ┌───────────────────────────┐        │
│                              │   Retrieval + Fusion      │        │
│                              │   (parallel search, fuse) │        │
│                              └───────────┬───────────────┘        │
│                                          ▼                        │
│                              ┌───────────────────────────┐        │
│                              │   Confidence Scoring      │        │
│                              │   HIGH / MEDIUM / LOW      │        │
│                              └───────────┬───────────────┘        │
│                                          ▼                        │
│                    ┌─────────────────────────────────────┐        │
│                    │         Generation (Claude)          │        │
│                    │  HIGH   → reuse precedent             │        │
│                    │  MEDIUM → generate with citations     │        │
│                    │  LOW    → ABSTAIN, escalate to human  │        │
│                    └─────────────────┬───────────────────┘        │
│                                      ▼                            │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────────┐        │
│  │ Document │◀──│ Validation │◀──│ Expert Review         │        │
│  │ (docx /  │   │ Writeback  │──▶│ (edits → qa_store)    │        │
│  │  pdf)    │   │ to qa_store│   └──────────────────────┘        │
│  └──────────┘   └────────────┘                                    │
└──────────────────────────────────────────────────────────────────┘
```

Every response carries its confidence regime and its sources end to end, from retrieval through generation to the final document — nothing is generated or exported without a traceable origin.

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| API | FastAPI | REST endpoints, auto-generated docs at `/docs` |
| LLM | Anthropic Claude API | Grounded generation, citation enforcement |
| Embeddings | Multilingual sentence embeddings | Arabic + French administrative text |
| Vector store | Qdrant (Docker) or FAISS (local fallback) | Auto-detected at setup |
| Metadata / audit trail | SQLite | Validation history, document generation log |
| Document generation | `docxtpl` + LibreOffice headless | Word template fill → PDF export |
| Frontend | Static HTML/JS | Ask view + expert validation view |

## Project structure

```
rafiq/
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Configuration, thresholds, model names
│   ├── ingestion/           # Excel loading + chunking
│   ├── indexing/            # Embeddings + vector store (docs_store, qa_store)
│   ├── retrieval/           # Search, fusion, confidence scoring
│   ├── generation/          # Prompts + Claude-based grounded generation
│   ├── validation/          # Validation workflow + qa_store writeback
│   ├── documents/           # Word/PDF template rendering
│   └── api/                 # FastAPI routes
├── frontend/                # Ask view + validation view (HTML/JS)
├── eval/                    # Test question set + evaluation script
├── data/raw/                # Source Excel files
├── scripts/                 # Setup scripts (Linux/Mac + Windows)
└── DECISIONS.md             # Log of technical decisions and trade-offs
```

## Prerequisites

- **Python 3.11+**
- **Docker** *(optional)* — for Qdrant; FAISS is used automatically if unavailable
- **LibreOffice** *(optional)* — required for PDF export
- **Anthropic API key** — for Claude-based generation

## Quick start

### 1. Configure

```bash
cd rafiq/
cp .env.example .env
# → fill in ANTHROPIC_API_KEY in .env
```

### 2. Run setup

**Linux/Mac**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows (PowerShell)**
```powershell
.\scripts\setup.ps1
```

The setup script:
- creates a Python virtual environment and installs dependencies
- starts Qdrant via Docker if available, otherwise configures FAISS
- places source Excel files into `data/raw/`
- builds the initial vector index

### 3. Run the API

```bash
source .venv/bin/activate       # Linux/Mac
.\.venv\Scripts\Activate        # Windows

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Use it

| Resource | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Ask view | http://localhost:8000/static/index.html |
| Validation view | http://localhost:8000/static/validate.html |
| Health check | http://localhost:8000/health |

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/ask` | Submit a question → grounded, sourced answer |
| `POST` | `/api/validate` | Validate or edit an answer → written back to `qa_store` |
| `GET` | `/api/document/{id}` | Download a generated Word/PDF document |

### `POST /api/ask`

**Request**
```json
{
  "question": "Quels sont les documents nécessaires pour obtenir un certificat de résidence ?",
  "top_k": 5
}
```

**Response**
```json
{
  "answer": "Pour obtenir un certificat de résidence, vous devez... [source: proc_123_doc_0]",
  "sources": [
    { "chunk_id": "proc_123_doc_0", "text": "...", "collection": "docs" }
  ],
  "confidence": 0.72,
  "regime": "medium",
  "abstained": false
}
```

### Confidence regimes

| Regime | Trigger | Behavior |
|---|---|---|
| `high` | Close match found in validated precedent (`qa_store`) | Reuse and lightly reformulate the precedent, cite it directly |
| `medium` | Relevant documentation found, no exact precedent | Generate a fresh answer strictly grounded in retrieved chunks, with citations |
| `low` | No sufficiently relevant source in either store | Abstain — no answer generated; escalate to a human expert with the best available snippets |

## Data

`data/raw/` holds the source Excel files used to build `docs_store`. During development, an existing administrative-procedures dataset is used as a realistic stand-in corpus while the final ministry documentation is being finalized — the ingestion pipeline is built against its structure so it transfers directly once the definitive corpus is delivered.

## Evaluation

`eval/` contains a hand-annotated test question set (`test_questions.csv`) and `run_eval.py`, which reports:
- citation/grounding accuracy
- abstention correctness (abstains when it should, answers when it should)
- regime accuracy (matches `expected_regime` in CSV)
- precedent reuse rate (regime=high — direct measure of the capitalization loop)
- per-language breakdown (FR / AR)

**Seed expert Q&A precedents** (required before testing HIGH reuse):

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_qa
```

Demo questions that should route to **HIGH** regime after seeding:
- FR: *Quels sont les documents nécessaires pour obtenir un certificat de résidence ?*
- FR: *Comment renouveler le passeport biométrique ?*
- AR: *ما هي الوثائق المطلوبة للحصول على شهادة السكنى؟*
- AR: *كيف يمكن تجديد جواز السفر البيومتري؟*

Run evaluation (API must be running, valid `ANTHROPIC_API_KEY` in `.env`):

```powershell
.\.venv\Scripts\python.exe -m eval.run_eval
```

## Roadmap

- [x] **Phase 1** — Single-memory RAG: ingestion, indexing, grounded generation with citations
- [x] **Phase 2** — Double memory (`qa_store`), confidence scoring, abstention
- [x] **Phase 3** — Validation workflow, `qa_store` writeback, document generation, frontend
- [x] **Phase 4** — Evaluation, hardening, polish

See `DECISIONS.md` for the reasoning behind each technical trade-off made along the way.

## Contributing

This is a capstone (PFA) project developed under academic and ministerial supervision. Issues and suggestions are welcome via the repository's issue tracker; external pull requests are not being accepted at this stage.

## License

PFA project — internal use, Ministère de la Transition Numérique. No public license is granted at this time.
