"""SQLite schema + connection. Queries are added by the steps that need them."""

import sqlite3
from pathlib import Path

TASK_TYPES = ("code", "review", "docs", "other")

# Timestamps are ISO 8601 text in UTC.
SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL,              -- a file name in types/, without .yaml
    status      TEXT NOT NULL DEFAULT 'active',
    path        TEXT NOT NULL UNIQUE,       -- the project folder
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    type        TEXT NOT NULL CHECK (type IN ('code', 'review', 'docs', 'other')),
    agent       TEXT NOT NULL DEFAULT 'auto',   -- an adapter name, or 'auto'
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL
);

-- A run row is inserted when the run starts and filled in when it ends,
-- so everything known only afterwards is nullable.
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY,
    task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent         TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    duration_s    REAL,
    exit_code     INTEGER,
    stdout        TEXT,
    stderr        TEXT,
    brief_path    TEXT,
    diff          TEXT,
    files_changed TEXT,                     -- JSON list of paths
    tokens_in     INTEGER,
    tokens_out    INTEGER
);

CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,              -- relative to the project folder
    type        TEXT NOT NULL,
    size        INTEGER NOT NULL,           -- bytes
    tags        TEXT NOT NULL DEFAULT '',   -- comma-separated
    UNIQUE (project_id, path)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database with foreign keys on and rows readable by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create any missing tables. Safe to run on every startup."""
    conn.executescript(SCHEMA)
    conn.commit()
