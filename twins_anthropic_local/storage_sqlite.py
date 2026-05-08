"""SQLite implementation of the Anthropic twin's TwinStorage.

Persistent across restarts; configurable via ``TWIN_DB_PATH``.

Every resource table carries a ``tenant_id`` column. Twin Plane operations
scope by ``tenant_id``; provider operations scope by api-key, and the row
the api-key resolves to carries the ``tenant_id`` so isolation can be
enforced at the data plane.
"""

import json
import sqlite3
import threading
from typing import Optional

from twins_anthropic.storage import TwinStorage


_VALID_FEEDBACK_COLUMNS = frozenset({"status", "date_updated"})


class SQLiteStorage(TwinStorage):
    """SQLite-backed storage for the Anthropic twin."""

    def __init__(self, db_path: str = "data/anthropic_twin.db"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS api_keys (
                        key_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        key_hash TEXT NOT NULL UNIQUE,
                        friendly_name TEXT NOT NULL DEFAULT '',
                        date_created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);

                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        request_json TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        beta_headers TEXT NOT NULL DEFAULT '[]',
                        date_created TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_messages_tenant ON messages(tenant_id);

                    CREATE TABLE IF NOT EXISTS feedback (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        body TEXT NOT NULL,
                        category TEXT NOT NULL DEFAULT '',
                        context_json TEXT NOT NULL DEFAULT '{}',
                        status TEXT NOT NULL DEFAULT 'pending',
                        date_created TEXT NOT NULL,
                        date_updated TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_feedback_tenant ON feedback(tenant_id);

                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_logs_tenant ON logs(tenant_id);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    # -- api keys --

    def create_api_key(
        self,
        *,
        tenant_id: str,
        key_id: str,
        key_hash: str,
        friendly_name: str,
    ) -> dict:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO api_keys (key_id, tenant_id, key_hash, friendly_name) VALUES (?, ?, ?, ?)",
                    (key_id, tenant_id, key_hash, friendly_name),
                )
                conn.commit()
            finally:
                conn.close()
        return {
            "key_id": key_id,
            "tenant_id": tenant_id,
            "key_hash": key_hash,
            "friendly_name": friendly_name,
        }

    def get_api_key_by_hash(self, key_hash: str) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_api_keys(self, *, tenant_id: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        try:
            if tenant_id is None:
                rows = conn.execute(
                    "SELECT * FROM api_keys ORDER BY date_created DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY date_created DESC",
                    (tenant_id,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_api_key(self, key_id: str) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM api_keys WHERE key_id = ?", (key_id,))
                conn.commit()
            finally:
                conn.close()

    # -- messages --

    def create_message(self, data: dict) -> dict:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT INTO messages
                        (id, tenant_id, model, request_json, response_json, beta_headers, date_created)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["id"],
                        data["tenant_id"],
                        data["model"],
                        json.dumps(data.get("request_json", {})),
                        json.dumps(data.get("response_json", {})),
                        json.dumps(data.get("beta_headers", [])),
                        data["date_created"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return data

    def get_message(self, message_id: str) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
            return self._row_to_message(row) if row else None
        finally:
            conn.close()

    def list_messages(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        conn = self._get_conn()
        try:
            if tenant_id is None:
                rows = conn.execute(
                    "SELECT * FROM messages ORDER BY date_created DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE tenant_id = ? ORDER BY date_created DESC LIMIT ?",
                    (tenant_id, limit),
                ).fetchall()
            return [self._row_to_message(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_message(row) -> dict:
        return {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "model": row["model"],
            "request_json": json.loads(row["request_json"] or "{}"),
            "response_json": json.loads(row["response_json"] or "{}"),
            "beta_headers": json.loads(row["beta_headers"] or "[]"),
            "date_created": row["date_created"],
        }

    # -- feedback --

    def create_feedback(self, data: dict) -> dict:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT INTO feedback
                        (id, tenant_id, body, category, context_json, status, date_created, date_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["id"],
                        data["tenant_id"],
                        data["body"],
                        data.get("category", ""),
                        json.dumps(data.get("context", {}) or {}),
                        data.get("status", "pending"),
                        data["date_created"],
                        data["date_updated"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return self.get_feedback(data["id"])

    def get_feedback(self, feedback_id: str) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            return self._row_to_feedback(row) if row else None
        finally:
            conn.close()

    def list_feedback(
        self,
        *,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        conn = self._get_conn()
        try:
            sql = "SELECT * FROM feedback WHERE 1=1"
            params: list = []
            if status:
                sql += " AND status = ?"
                params.append(status)
            if tenant_id is not None:
                sql += " AND tenant_id = ?"
                params.append(tenant_id)
            sql += " ORDER BY date_created DESC"
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_feedback(r) for r in rows]
        finally:
            conn.close()

    def update_feedback(self, feedback_id: str, updates: dict) -> Optional[dict]:
        cols = [k for k in updates.keys() if k in _VALID_FEEDBACK_COLUMNS]
        if not cols:
            return self.get_feedback(feedback_id)
        sql = f"UPDATE feedback SET {', '.join(c + ' = ?' for c in cols)} WHERE id = ?"
        params = [updates[c] for c in cols] + [feedback_id]
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(sql, params)
                conn.commit()
            finally:
                conn.close()
        return self.get_feedback(feedback_id)

    @staticmethod
    def _row_to_feedback(row) -> dict:
        return {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "body": row["body"],
            "category": row["category"],
            "context": json.loads(row["context_json"] or "{}"),
            "status": row["status"],
            "date_created": row["date_created"],
            "date_updated": row["date_updated"],
        }

    # -- logs --

    def append_log(self, entry: dict) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO logs (tenant_id, record_json, timestamp) VALUES (?, ?, ?)",
                    (
                        entry.get("tenant_id", ""),
                        json.dumps(entry),
                        entry.get("timestamp", ""),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_logs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        conn = self._get_conn()
        try:
            sql = "SELECT id, record_json FROM logs"
            params: list = []
            if tenant_id is not None:
                sql += " WHERE tenant_id = ?"
                params.append(tenant_id)
            sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()
            out = []
            for r in rows:
                rec = json.loads(r["record_json"])
                rec["id"] = r["id"]
                out.append(rec)
            return out
        finally:
            conn.close()
