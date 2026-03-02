"""
PromptStore — SQLite-backed prompt versioning with content-addressable hashing.

Immutable prompt versions, mutable labels, and generation traces.
"""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PromptStore:
    def __init__(self, db_path: str | Path = "data/prompts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id TEXT PRIMARY KEY,
                content_hash TEXT UNIQUE NOT NULL,
                version INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                negative_prompt TEXT NOT NULL DEFAULT '',
                name TEXT,
                change_note TEXT,
                model_config TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS labels (
                name TEXT PRIMARY KEY,
                prompt_version_id TEXT NOT NULL REFERENCES prompt_versions(id),
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generation_traces (
                id TEXT PRIMARY KEY,
                prompt_version_id TEXT NOT NULL REFERENCES prompt_versions(id),
                job_id TEXT,
                start_image_url TEXT,
                end_image_url TEXT,
                product_images TEXT,
                product_video_url TEXT,
                video_url TEXT,
                elapsed_seconds REAL,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                rating INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    @staticmethod
    def hash_prompt(prompt: str, negative_prompt: str = "") -> str:
        content = prompt + "\x00" + negative_prompt
        return hashlib.sha256(content.encode()).hexdigest()

    def _next_version(self) -> int:
        row = self.conn.execute(
            "SELECT MAX(version) as max_v FROM prompt_versions"
        ).fetchone()
        return (row["max_v"] or 0) + 1

    def save_version(
        self,
        prompt: str,
        negative_prompt: str = "",
        name: str | None = None,
        change_note: str | None = None,
        model_config: dict | None = None,
    ) -> dict[str, Any]:
        content_hash = self.hash_prompt(prompt, negative_prompt)

        existing = self.conn.execute(
            "SELECT id, version FROM prompt_versions WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()

        if existing:
            return {"id": existing["id"], "version": existing["version"], "is_new": False}

        version_id = str(uuid.uuid4())
        version_num = self._next_version()
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            """INSERT INTO prompt_versions
               (id, content_hash, version, prompt, negative_prompt, name, change_note, model_config, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                version_id,
                content_hash,
                version_num,
                prompt,
                negative_prompt,
                name,
                change_note,
                json.dumps(model_config) if model_config else None,
                now,
            ),
        )
        self.conn.commit()
        return {"id": version_id, "version": version_num, "is_new": True}

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM prompt_versions WHERE id = ?", (version_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d["model_config"]:
            d["model_config"] = json.loads(d["model_config"])
        return d

    def list_versions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                pv.id, pv.version, pv.prompt, pv.negative_prompt,
                pv.name, pv.created_at,
                COUNT(gt.id) as trace_count,
                AVG(CASE WHEN gt.rating IS NOT NULL THEN gt.rating END) as avg_rating
            FROM prompt_versions pv
            LEFT JOIN generation_traces gt ON gt.prompt_version_id = pv.id
            GROUP BY pv.id
            ORDER BY pv.version DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            d["prompt_preview"] = d.pop("prompt")[:80]
            d.pop("negative_prompt")
            # Attach labels
            label_rows = self.conn.execute(
                "SELECT name FROM labels WHERE prompt_version_id = ?", (d["id"],)
            ).fetchall()
            d["labels"] = [lr["name"] for lr in label_rows]
            results.append(d)
        return results

    def save_trace(
        self,
        prompt_version_id: str,
        job_id: str | None = None,
        start_image_url: str | None = None,
        end_image_url: str | None = None,
        product_images: list[str] | None = None,
        product_video_url: str | None = None,
        video_url: str | None = None,
        elapsed_seconds: float | None = None,
        status: str = "pending",
        error_message: str | None = None,
    ) -> str:
        trace_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO generation_traces
               (id, prompt_version_id, job_id, start_image_url, end_image_url,
                product_images, product_video_url, video_url, elapsed_seconds,
                status, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace_id,
                prompt_version_id,
                job_id,
                start_image_url,
                end_image_url,
                json.dumps(product_images) if product_images else None,
                product_video_url,
                video_url,
                elapsed_seconds,
                status,
                error_message,
                now,
            ),
        )
        self.conn.commit()
        return trace_id

    def update_trace(
        self,
        trace_id: str,
        video_url: str | None = None,
        elapsed_seconds: float | None = None,
        status: str | None = None,
        error_message: str | None = None,
        rating: int | None = None,
        notes: str | None = None,
    ) -> None:
        updates = []
        params = []
        if video_url is not None:
            updates.append("video_url = ?")
            params.append(video_url)
        if elapsed_seconds is not None:
            updates.append("elapsed_seconds = ?")
            params.append(elapsed_seconds)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if rating is not None:
            updates.append("rating = ?")
            params.append(rating)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if not updates:
            return
        params.append(trace_id)
        self.conn.execute(
            f"UPDATE generation_traces SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        self.conn.commit()

    def get_traces(self, prompt_version_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT * FROM generation_traces
               WHERE prompt_version_id = ?
               ORDER BY created_at DESC""",
            (prompt_version_id,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d["product_images"]:
                d["product_images"] = json.loads(d["product_images"])
            results.append(d)
        return results

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM generation_traces WHERE id = ?", (trace_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d["product_images"]:
            d["product_images"] = json.loads(d["product_images"])
        return d

    def set_label(self, name: str, prompt_version_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO labels (name, prompt_version_id, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET prompt_version_id = ?, updated_at = ?""",
            (name, prompt_version_id, now, prompt_version_id, now),
        )
        self.conn.commit()

    def remove_label(self, name: str) -> None:
        self.conn.execute("DELETE FROM labels WHERE name = ?", (name,))
        self.conn.commit()

    def list_labels(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get_labels_for_version(self, prompt_version_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM labels WHERE prompt_version_id = ? ORDER BY name",
            (prompt_version_id,),
        ).fetchall()
        return [r["name"] for r in rows]
