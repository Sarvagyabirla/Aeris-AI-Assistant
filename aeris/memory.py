from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    """Small local conversation store. It never stores secrets intentionally."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
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

    def add(self, role: str, content: str) -> None:
        if not content.strip():
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(created_at, role, content) VALUES (?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), role, content[:10_000]),
            )

    def recent(self, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content, created_at FROM messages ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in reversed(rows)
        ]
