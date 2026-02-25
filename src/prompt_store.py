"""
Local Prompt Trace Store — SQLite-backed storage for prompt versioning and tracing.

Captures the full assembled prompt, raw LLM response, processed output, template
version (auto-detected via hash), token usage, and latency for every generate_prompt
run. Persists to data/prompts.db across server restarts.

Zero external dependencies — uses Python's built-in sqlite3.
"""

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# DB lives next to the project root, gitignored
_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = _DB_DIR / "prompts.db"


class PromptStore:
    """SQLite-backed store for prompt traces and template versions."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Database setup
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS template_versions (
                    hash            TEXT PRIMARY KEY,
                    version_number  INTEGER NOT NULL,
                    template_text   TEXT NOT NULL,
                    first_seen      TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS prompt_traces (
                    trace_id         TEXT PRIMARY KEY,
                    job_id           TEXT,
                    template_hash    TEXT NOT NULL,
                    assembled_prompt TEXT NOT NULL,
                    model            TEXT NOT NULL,
                    inputs_snapshot  TEXT NOT NULL,
                    raw_response     TEXT,
                    processed_output TEXT,
                    token_usage      TEXT,
                    latency_ms       INTEGER,
                    created_at       TEXT NOT NULL,
                    FOREIGN KEY (template_hash) REFERENCES template_versions(hash)
                );

                CREATE INDEX IF NOT EXISTS idx_traces_job
                    ON prompt_traces(job_id);
                CREATE INDEX IF NOT EXISTS idx_traces_template
                    ON prompt_traces(template_hash);
                CREATE INDEX IF NOT EXISTS idx_traces_created
                    ON prompt_traces(created_at DESC);
            """)
        logger.info(f"Prompt store ready at {self._db_path}")

    # ------------------------------------------------------------------
    # Template version management
    # ------------------------------------------------------------------

    @staticmethod
    def hash_template(template_text: str) -> str:
        return hashlib.sha256(template_text.encode()).hexdigest()

    def _ensure_template_version(self, conn: sqlite3.Connection, template_hash: str, template_text: str) -> int:
        """Return the version_number for this hash, creating a new version if needed."""
        row = conn.execute(
            "SELECT version_number FROM template_versions WHERE hash = ?",
            (template_hash,),
        ).fetchone()
        if row:
            return row["version_number"]

        # New hash — assign next version number
        max_row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) AS mx FROM template_versions"
        ).fetchone()
        next_version = max_row["mx"] + 1

        conn.execute(
            "INSERT INTO template_versions (hash, version_number, template_text, first_seen) VALUES (?, ?, ?, ?)",
            (template_hash, next_version, template_text, _now_iso()),
        )
        logger.info(f"New template version v{next_version} (hash: {template_hash[:12]}...)")
        return next_version

    # ------------------------------------------------------------------
    # Save a trace
    # ------------------------------------------------------------------

    def save_trace(
        self,
        *,
        template_text: str,
        assembled_prompt: str,
        model: str,
        inputs_snapshot: dict[str, Any],
        job_id: Optional[str] = None,
        raw_response: Optional[str] = None,
        processed_output: Optional[dict[str, Any]] = None,
        token_usage: Optional[dict[str, int]] = None,
        latency_ms: Optional[int] = None,
    ) -> str:
        """
        Record a prompt trace. Auto-creates template version if hash is new.

        Returns the trace_id (UUID).
        """
        trace_id = str(uuid.uuid4())
        template_hash = self.hash_template(template_text)

        with self._get_conn() as conn:
            self._ensure_template_version(conn, template_hash, template_text)
            conn.execute(
                """INSERT INTO prompt_traces
                   (trace_id, job_id, template_hash, assembled_prompt, model,
                    inputs_snapshot, raw_response, processed_output,
                    token_usage, latency_ms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trace_id,
                    job_id,
                    template_hash,
                    assembled_prompt,
                    model,
                    json.dumps(inputs_snapshot),
                    raw_response,
                    json.dumps(processed_output) if processed_output else None,
                    json.dumps(token_usage) if token_usage else None,
                    latency_ms,
                    _now_iso(),
                ),
            )

        logger.info(f"Saved trace {trace_id[:8]}... for job {(job_id or 'none')[:8]}")
        return trace_id

    # ------------------------------------------------------------------
    # Query traces
    # ------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        """Return full trace data including template version number."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT t.*, tv.version_number
                   FROM prompt_traces t
                   JOIN template_versions tv ON t.template_hash = tv.hash
                   WHERE t.trace_id = ?""",
                (trace_id,),
            ).fetchone()
        return _row_to_trace(row) if row else None

    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        template_version: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return trace summaries (no assembled_prompt or raw_response for efficiency)."""
        query = """
            SELECT t.trace_id, t.job_id, t.template_hash, t.model,
                   t.token_usage, t.latency_ms, t.created_at,
                   tv.version_number
            FROM prompt_traces t
            JOIN template_versions tv ON t.template_hash = tv.hash
            WHERE 1=1
        """
        params: list[Any] = []

        if template_version is not None:
            query += " AND tv.version_number = ?"
            params.append(template_version)
        if job_id is not None:
            query += " AND t.job_id = ?"
            params.append(job_id)

        query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_summary(r) for r in rows]

    def get_template_versions(self) -> list[dict[str, Any]]:
        """Return all template versions with run counts."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT tv.hash, tv.version_number, tv.first_seen,
                          COUNT(t.trace_id) AS run_count
                   FROM template_versions tv
                   LEFT JOIN prompt_traces t ON tv.hash = t.template_hash
                   GROUP BY tv.hash
                   ORDER BY tv.version_number DESC"""
            ).fetchall()

        return [
            {
                "hash": r["hash"],
                "version_number": r["version_number"],
                "first_seen": r["first_seen"],
                "run_count": r["run_count"],
            }
            for r in rows
        ]

    def compare_traces(self, trace_id_a: str, trace_id_b: str) -> Optional[dict[str, Any]]:
        """Return two full traces side by side for comparison."""
        a = self.get_trace(trace_id_a)
        b = self.get_trace(trace_id_b)
        if not a or not b:
            return None
        return {"a": a, "b": b}

    def get_trace_by_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """Return the trace for a given job_id (most recent if multiple)."""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT t.*, tv.version_number
                   FROM prompt_traces t
                   JOIN template_versions tv ON t.template_hash = tv.hash
                   WHERE t.job_id = ?
                   ORDER BY t.created_at DESC
                   LIMIT 1""",
                (job_id,),
            ).fetchone()
        return _row_to_trace(row) if row else None


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_store: Optional[PromptStore] = None


def get_prompt_store() -> PromptStore:
    """Return (and lazily create) the global PromptStore singleton."""
    global _store
    if _store is None:
        _store = PromptStore()
    return _store


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json_field(val: Optional[str]) -> Any:
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def _row_to_trace(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "job_id": row["job_id"],
        "template_hash": row["template_hash"],
        "template_version": row["version_number"],
        "assembled_prompt": row["assembled_prompt"],
        "model": row["model"],
        "inputs_snapshot": _parse_json_field(row["inputs_snapshot"]),
        "raw_response": row["raw_response"],
        "processed_output": _parse_json_field(row["processed_output"]),
        "token_usage": _parse_json_field(row["token_usage"]),
        "latency_ms": row["latency_ms"],
        "created_at": row["created_at"],
    }


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "job_id": row["job_id"],
        "template_hash": row["template_hash"],
        "template_version": row["version_number"],
        "model": row["model"],
        "token_usage": _parse_json_field(row["token_usage"]),
        "latency_ms": row["latency_ms"],
        "created_at": row["created_at"],
    }
