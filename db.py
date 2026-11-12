"""SQLite storage for saved voices. Audio and prompt files live in data/voices/<id>/."""
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS voices (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    ref_text      TEXT,
    x_vector_only INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def add_voice(voice_id: str, name: str, ref_text: str | None, x_vector_only: bool):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO voices (id, name, ref_text, x_vector_only, created_at) VALUES (?, ?, ?, ?, ?)",
            (voice_id, name, ref_text, int(x_vector_only), datetime.now(timezone.utc).isoformat()),
        )


def list_voices():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM voices ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_voice(voice_id: str):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM voices WHERE id = ?", (voice_id,)).fetchone()
    return dict(row) if row else None


def delete_voice(voice_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM voices WHERE id = ?", (voice_id,))
