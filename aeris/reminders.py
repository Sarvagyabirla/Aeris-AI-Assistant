"""Durable, timezone-aware reminders with restart persistence.

Reminders survive application restarts, handle sleep/wake events, support
snooze/cancel, and deliver overdue notifications without replaying actions.
They do not promise delivery when the application is closed.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def reminder_timezone(name):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name in {"Asia/Kolkata", "Asia/Calcutta"}:
            return timezone(timedelta(hours=5, minutes=30), name)
        if name in {"UTC", "Etc/UTC"}:
            return timezone.utc
        raise ValueError("Timezone data is unavailable. Choose Asia/Kolkata or UTC, or explicitly configure IANA timezone data.") from None


class ReminderStore:
    """Persists reminders to a local SQLite database and fires them on schedule.

    Delivery guarantee: reminders fire only while Aeris is running.
    Overdue reminders are surfaced as "missed" notifications rather than
    replaying past actions. Duplicate suppression uses a 5-second window.
    """

    def __init__(self, db_path: Path, timezone_name: str = "Asia/Kolkata", clock=None, enabled=None):
        self.db_path = db_path
        self.timezone_name = timezone_name
        self.timezone = reminder_timezone(timezone_name)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.enabled = enabled or (lambda: True)
        self.last_error = ""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._callback_lock = threading.Lock()
        self._callbacks: list[Callable[[dict], None]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._initialize()

    def now(self):
        current = self._clock()
        if current.tzinfo is None:
            raise ValueError("Reminder clock must be timezone-aware")
        return current.astimezone(timezone.utc)

    @contextmanager
    def _connect(self, token=None):
        conn = sqlite3.connect(self.db_path, timeout=1)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                if token:
                    token.raise_if_cancelled()
                yield conn
                if token:
                    token.raise_if_cancelled()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    fire_at TEXT NOT NULL,
                    recurrence TEXT,
                    snoozed_until TEXT,
                    fired_at TEXT,
                    cancelled INTEGER NOT NULL DEFAULT 0,
                    overdue INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_fire ON reminders(fire_at)")

    def add(
        self,
        message: str,
        fire_at: datetime,
        recurrence: str | None = None,
        token=None,
    ) -> str:
        """Add a new reminder. Returns the reminder ID.

        Args:
            message: Human-readable reminder text (max 500 chars).
            fire_at: When to fire the reminder. Must be timezone-aware.
            recurrence: Optional recurrence spec ('daily', 'weekly', or None).

        Returns:
            The unique reminder ID.
        """
        if not message.strip() or len(message) > 500:
            raise ValueError("Reminder message must be 1-500 characters.")
        if fire_at.tzinfo is None:
            raise ValueError("fire_at must be timezone-aware.")
        if recurrence not in {None, "daily", "weekly"}:
            raise ValueError("Recurrence must be None, 'daily', or 'weekly'.")
        # Deduplicate: same message + same fire_at within 5 seconds
        fire_utc = fire_at.astimezone(timezone.utc)
        window_start = (fire_utc - timedelta(seconds=5)).isoformat()
        window_end = (fire_utc + timedelta(seconds=5)).isoformat()
        with self._lock, self._connect(token) as conn:
            existing = conn.execute(
                "SELECT id FROM reminders WHERE message = ? AND fire_at BETWEEN ? AND ? AND cancelled = 0 AND fired_at IS NULL AND recurrence IS ?",
                (message.strip(), window_start, window_end, recurrence),
            ).fetchone()
            if existing:
                return existing["id"]
            reminder_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO reminders(id, message, fire_at, recurrence, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    reminder_id,
                    message.strip(),
                    fire_utc.isoformat(),
                    recurrence,
                    self.now().isoformat(),
                ),
            )
        return reminder_id

    def cancel(self, reminder_id: str, token=None) -> bool:
        """Cancel a pending reminder. Returns True if cancelled."""
        with self._lock, self._connect(token) as conn:
            return conn.execute(
                "UPDATE reminders SET cancelled = 1 WHERE id = ? AND fired_at IS NULL AND cancelled = 0",
                (reminder_id,),
            ).rowcount == 1

    def snooze(self, reminder_id: str, minutes: int = 10, token=None) -> bool:
        """Snooze a reminder by the given number of minutes."""
        if not 1 <= minutes <= 1440:
            raise ValueError("Snooze must be 1-1440 minutes.")
        snoozed_until = (self.now() + timedelta(minutes=minutes)).isoformat()
        with self._lock, self._connect(token) as conn:
            return conn.execute(
                "UPDATE reminders SET snoozed_until = ?, fired_at = NULL, overdue = 0 WHERE id = ? AND cancelled = 0",
                (snoozed_until, reminder_id),
            ).rowcount == 1

    def list_pending(self) -> list[dict]:
        """List all pending (unfired, uncancelled) reminders."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE cancelled = 0 AND fired_at IS NULL ORDER BY COALESCE(snoozed_until, fire_at) LIMIT 1000"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_recent(self, limit: int = 20) -> list[dict]:
        """List recently fired or missed reminders."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE fired_at IS NOT NULL ORDER BY fired_at DESC LIMIT ?",
                (min(limit, 100),),
            ).fetchall()
        return [dict(row) for row in rows]

    def on_reminder(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for when a reminder fires or is overdue."""
        with self._callback_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def off_reminder(self, callback):
        with self._callback_lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def start(self) -> None:
        """Start the background scheduler thread."""
        if not self._callbacks or self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="Aeris-reminders"
        )
        self._thread.start()

    def stop(self) -> bool:
        """Stop the background scheduler thread."""
        self._stop_event.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        return not self._thread or not self._thread.is_alive()

    def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_due_reminders()
            except Exception as exc:
                self.last_error = type(exc).__name__
            self._stop_event.wait(timeout=1.0)

    def _check_due_reminders(self) -> None:
        if not self.enabled():
            return
        now_utc = self.now()
        now_str = now_utc.isoformat()
        # Mark overdue (missed by more than 5 minutes)
        deliveries = []
        with self._callback_lock:
            callbacks = tuple(self._callbacks)
        if not callbacks:
            return
        with self._lock, self._connect() as conn:
            if not self.enabled():
                return
            # Claim before publishing notifications. This also serializes separate
            # Aeris instances using the same database, without deleting/migrating rows.
            conn.execute("BEGIN IMMEDIATE")
            # Find due reminders: fire_at <= now, not cancelled, not already fired,
            # and either not snoozed or snooze window has passed
            due_rows = conn.execute(
                """SELECT * FROM reminders
                   WHERE cancelled = 0 AND fired_at IS NULL
                   AND COALESCE(snoozed_until, fire_at) <= ?
                   ORDER BY COALESCE(snoozed_until, fire_at) LIMIT 100""",
                (now_str,),
            ).fetchall()

            for row in due_rows:
                reminder = dict(row)
                try:
                    fire_at = datetime.fromisoformat(reminder["fire_at"])
                    effective = datetime.fromisoformat(reminder["snoozed_until"] or reminder["fire_at"])
                    if fire_at.tzinfo is None or effective.tzinfo is None or reminder["recurrence"] not in {None, "daily", "weekly"}:
                        raise ValueError("Malformed reminder record")
                except (ValueError, TypeError):
                    self.last_error = "malformed_reminder_record"
                    continue
                is_overdue = effective < now_utc - timedelta(minutes=5)
                reminder["overdue"] = is_overdue
                conn.execute(
                    "UPDATE reminders SET fired_at = ?, overdue = ? WHERE id = ?",
                    (now_str, 1 if is_overdue else 0, reminder["id"]),
                )
                # Schedule recurrence if configured
                if reminder["recurrence"]:
                    days = 1 if reminder["recurrence"] == "daily" else 7
                    local_now = now_utc.astimezone(self.timezone)
                    next_fire = fire_at.astimezone(self.timezone) + timedelta(days=days)
                    if next_fire <= local_now:
                        next_fire += timedelta(days=((local_now - next_fire).days // days + 1) * days)
                    next_fire = next_fire.astimezone(timezone.utc)
                    conn.execute(
                        """INSERT OR IGNORE INTO reminders(id, message, fire_at, recurrence, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            str(uuid.uuid5(uuid.NAMESPACE_URL, reminder["id"] + next_fire.isoformat())),
                            reminder["message"],
                            next_fire.isoformat(),
                            reminder["recurrence"],
                            now_str,
                        ),
                    )
                deliveries.append(reminder)
        # SQLite commit and store lock finish before any UI callback is invoked.
        for reminder in deliveries:
            for callback in callbacks:
                try:
                    callback(reminder)
                except Exception:
                    self.last_error = "notification_delivery_failed"
