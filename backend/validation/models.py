"""SQLite schema for RAFIQ validation, document logs, and query logs."""

import sqlite3
from pathlib import Path
from datetime import datetime
from backend.config import get_settings


def get_db_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    settings = get_settings()
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't already exist."""
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS validated_answers (
            qa_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            original_answer TEXT NOT NULL,
            validated_answer TEXT NOT NULL,
            validator_name TEXT NOT NULL,
            validation_date TEXT NOT NULL,
            original_confidence REAL,
            original_regime TEXT,
            sources TEXT,  -- JSON serialized
            written_back BOOLEAN DEFAULT 0,
            writeback_date TEXT
        );

        CREATE TABLE IF NOT EXISTS document_logs (
            doc_id TEXT PRIMARY KEY,
            qa_id TEXT REFERENCES validated_answers(qa_id),
            format TEXT NOT NULL,  -- 'docx' or 'pdf'
            filepath TEXT NOT NULL,
            created_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS query_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            confidence REAL,
            regime TEXT,
            abstained BOOLEAN,
            sources TEXT,  -- JSON serialized
            timestamp TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()
