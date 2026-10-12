from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    """Small local conversation store. It never stores secrets intentionally."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            # Migration: add classification column if missing
            cursor = connection.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            columns = [col[1] for col in cursor.fetchall()]
            if "classification" not in columns:
                connection.execute(
                    "ALTER TABLE messages ADD COLUMN classification TEXT NOT NULL DEFAULT 'LOCAL_ONLY'"
                )
            # Conversation identity is the row ID, never the content.
            connection.execute("DROP INDEX IF EXISTS idx_messages_content")
            connection.execute("PRAGMA user_version = 2")

    def add(self, role: str, content: str, classification: str = "LOCAL_ONLY") -> None:
        if classification not in {"LOCAL_ONLY", "SHAREABLE", "SENSITIVE", "DO_NOT_STORE"}:
            raise ValueError("Unknown memory privacy classification")
        if not content.strip() or classification in {"SENSITIVE", "DO_NOT_STORE"}:
            return
            
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(created_at, role, content, classification) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), role, content[:10_000], classification),
            )

    def recent(self, limit: int = 12, exclude_sensitive: bool = False) -> list[dict[str, str]]:
        with self._connect() as connection:
            query = "SELECT role, content, created_at FROM messages "
            if exclude_sensitive:
                query += "WHERE classification != 'SENSITIVE' "
            query += "ORDER BY id DESC LIMIT ?"
            
            rows = connection.execute(query, (max(1, min(limit, 100)),)).fetchall()
        return [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in reversed(rows)
        ]

    def provider_context(self, limit: int = 8) -> list[dict[str, str]]:
        """Only explicitly shareable history may cross a network boundary."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content, created_at FROM messages WHERE classification = 'SHAREABLE' "
                "ORDER BY id DESC LIMIT ?", (max(1, min(limit, 20)),),
            ).fetchall()
        return [dict(role=role, content=content, created_at=created) for role, content, created in reversed(rows)]

    def inspect(self, limit: int = 100) -> list[dict]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(
                "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (max(1, min(limit, 1000)),))]

    def forget(self, message_id: int) -> bool:
        with self._lock, self._connect() as connection:
            return connection.execute("DELETE FROM messages WHERE id = ?", (message_id,)).rowcount == 1

    def correct(self, message_id: int, content: str) -> bool:
        if not content.strip() or len(content) > 10_000:
            raise ValueError("Correction must contain 1–10000 characters")
        with self._lock, self._connect() as connection:
            return connection.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id)).rowcount == 1

    def clear(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM messages")

    def retain_since(self, cutoff: datetime) -> int:
        if cutoff.tzinfo is None:
            raise ValueError("Retention cutoff must be timezone-aware")
        with self._lock, self._connect() as connection:
            return connection.execute("DELETE FROM messages WHERE created_at < ?", (
                cutoff.astimezone(timezone.utc).isoformat(),)).rowcount

    def export(self) -> list[dict]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM messages ORDER BY id")]
