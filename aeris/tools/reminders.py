"""Reminder tools exposed to the AI planner.

Provides set/list/snooze/cancel operations over the durable ReminderStore.
Time parsing converts natural-language "when" strings to timezone-aware
datetimes without accessing the network.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ..models import ActionResult
from ..reminders import ReminderStore


class ReminderTools:
    """Stateful tool class wrapping a ReminderStore.

    All datetime arithmetic is in UTC internally; display times use the
    store's configured timezone name.
    """

    def __init__(self, store: ReminderStore):
        self._store = store

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_when(when_str: str, timezone_name="Asia/Kolkata", now=None) -> datetime:
        """Strict whole schedule in the configured timezone; ISO requires an offset."""
        from ..reminders import reminder_timezone
        zone = reminder_timezone(timezone_name)
        now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        stripped = when_str.strip()
        try:
            parsed = datetime.fromisoformat(stripped)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                raise ValueError("ISO schedules must include a timezone offset, for example +05:30.")
            return parsed.astimezone(timezone.utc)
        relative = re.fullmatch(r"in\s+([0-9]+)\s+(second|minute|hour|day)s?", stripped, re.I)
        if relative:
            amount = int(relative[1])
            seconds = amount * {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[relative[2].lower()]
            if not 1 <= seconds <= 3650 * 86400:
                raise ValueError("Choose a positive reminder interval of at most ten years.")
            return now_utc + timedelta(seconds=seconds)
        days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}
        match = re.fullmatch(r"(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
                             r"(?: at ([0-9]{1,2})(?::([0-9]{2}))?\s*(am|pm)?)?", stripped, re.I)
        if not match:
            raise ValueError("Use 'in 15 minutes', 'tomorrow at 9am', or an ISO datetime with timezone offset.")
        day, hour, minute, period = match.groups()
        day, period = day.lower(), (period or "").lower()
        hour, minute = int(hour or 9), int(minute or 0)
        if minute > 59 or (period and not 1 <= hour <= 12) or (not period and not 0 <= hour <= 23):
            raise ValueError("Use a valid time, for example 9am or 21:30.")
        if period:
            hour = hour % 12 + (12 if period == "pm" else 0)
        local_now = now_utc.astimezone(zone)
        delta_days = 1 if day == "tomorrow" else (days[day] - local_now.weekday()) % 7 if day in days else 0
        target = (local_now + timedelta(days=delta_days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day in days and target <= local_now:
            target += timedelta(days=7)
        if target <= local_now:
            raise ValueError("That local time has passed. Choose a future schedule.")
        if target.replace(fold=0).utcoffset() != target.replace(fold=1).utcoffset():
            raise ValueError("That local time is ambiguous or skipped by daylight saving. Use an explicit ISO offset.")
        return target.astimezone(timezone.utc)

    def set_reminder(self, arguments: dict, token=None) -> ActionResult:
        """Add a new reminder."""
        try:
            message = str(arguments["message"]).strip()
            when_str = str(arguments["when"]).strip()
            recurrence = arguments.get("recurrence")
            fire_at = self._parse_when(when_str, self._store.timezone_name, self._store.now())
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), error="invalid_reminder_args")

        if fire_at <= self._store.now():
            return ActionResult(False, "The requested time is in the past.", error="past_time")

        try:
            reminder_id = self._store.add(message, fire_at, recurrence, token=token)
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_reminder_args")

        fire_local = fire_at.astimezone(self._store.timezone).strftime("%Y-%m-%d %H:%M:%S") + " " + self._store.timezone_name
        rec_str = f" (recurring {recurrence})" if recurrence else ""
        return ActionResult(
            not (token and token.is_cancelled),
            f"Reminder set for {fire_local}{rec_str}: '{message}'.",
            data={"reminder_id": reminder_id, "fire_at": fire_at.isoformat(), "stored": True, "timezone": self._store.timezone_name},
            error="cancelled_after_publication" if token and token.is_cancelled else None,
        )

    def list_reminders(self, arguments: dict, token=None) -> ActionResult:
        """List pending reminders."""
        pending = self._store.list_pending()
        if not pending:
            return ActionResult(True, "No pending reminders.", data={"reminders": []})
        lines = []
        for r in pending[:20]:
            try:
                fire = datetime.fromisoformat(r.get("snoozed_until") or r["fire_at"]).astimezone(self._store.timezone).isoformat() + " " + self._store.timezone_name
            except (TypeError, ValueError):
                fire = "Invalid saved schedule"
            snooze = f" (snoozed until {r['snoozed_until']})" if r.get("snoozed_until") else ""
            rec = f" [{r['recurrence']}]" if r.get("recurrence") else ""
            lines.append(f"[{r['id'][:8]}] {fire}{snooze}{rec}: {r['message']}")
        return ActionResult(
            True,
            f"{len(pending)} pending reminder(s):\n" + "\n".join(lines),
            data={"reminders": pending[:20]},
        )

    def snooze_reminder(self, arguments: dict, token=None) -> ActionResult:
        """Snooze a reminder by ID."""
        try:
            reminder_id = str(arguments["reminder_id"]).strip()
            minutes = int(arguments.get("minutes", 10))
        except (KeyError, ValueError, TypeError) as exc:
            return ActionResult(False, str(exc), error="invalid_snooze_args")
        try:
            ok = self._store.snooze(reminder_id, minutes, token=token)
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_snooze_args")
        if not ok:
            return ActionResult(False, f"Reminder {reminder_id[:8]} not found or already cancelled.", error="not_found")
        return ActionResult(True, f"Reminder snoozed for {minutes} minutes.", data={"reminder_id": reminder_id})

    def cancel_reminder(self, arguments: dict, token=None) -> ActionResult:
        """Cancel a reminder by ID."""
        try:
            reminder_id = str(arguments["reminder_id"]).strip()
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), error="invalid_cancel_args")
        if self._store.cancel(reminder_id, token=token):
            return ActionResult(True, f"Reminder {reminder_id[:8]} cancelled.", data={"reminder_id": reminder_id})
        return ActionResult(False, f"Reminder {reminder_id[:8]} not found or already cancelled.", error="not_found")
