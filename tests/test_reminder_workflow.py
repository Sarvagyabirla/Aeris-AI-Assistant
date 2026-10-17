import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.reminders import ReminderStore
from aeris.tools.reminders import ReminderTools


def test_today_at_nine_uses_configured_india_timezone():
    now = datetime(2026, 10, 17, 2, tzinfo=timezone.utc)
    parsed = ReminderTools._parse_when("today at 9am", "Asia/Kolkata", now)
    assert parsed == datetime(2026, 10, 17, 3, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("text", ["in 30 minutes and delete a file", "today at 25:00", "tomorrow at 0pm", "2026-10-18T09:00:00"])
def test_ambiguous_or_malformed_schedule_is_rejected(text):
    with pytest.raises(ValueError):
        ReminderTools._parse_when(text)


def test_due_record_is_not_consumed_without_delivery_listener(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    store.add("fixture", datetime.now(timezone.utc) - timedelta(minutes=1))
    store._check_due_reminders()
    assert len(store.list_pending()) == 1


def test_callbacks_run_after_commit_outside_store_lock(tmp_path):
    store = ReminderStore(tmp_path / "reminders.db")
    store.add("fixture", datetime.now(timezone.utc) - timedelta(minutes=1))
    locks = []
    def callback(record):
        acquired = store._lock.acquire(blocking=False)
        locks.append(acquired)
        if acquired:
            store._lock.release()
    store.on_reminder(callback)
    store._check_due_reminders()
    assert locks == [True]


def test_overdue_recurring_reminder_reschedules_once_after_sleep(tmp_path):
    now = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
    clock = [now]
    store = ReminderStore(tmp_path / "reminders.db", clock=lambda: clock[0])
    events = []
    store.on_reminder(events.append)
    store.add("fixture daily", now - timedelta(days=5), "daily")
    store._check_due_reminders()
    store._check_due_reminders()
    assert len(events) == 1 and events[0]["overdue"]
    pending = store.list_pending()
    assert len(pending) == 1
    assert datetime.fromisoformat(pending[0]["fire_at"]) > now


def test_snoozed_overdue_reminder_becomes_pending_again(tmp_path):
    now = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
    store = ReminderStore(tmp_path / "reminders.db", clock=lambda: now)
    store.on_reminder(lambda _: None)
    reminder_id = store.add("fixture", now - timedelta(minutes=10))
    store._check_due_reminders()
    assert store.list_recent()[0]["overdue"]
    assert store.snooze(reminder_id, 10)
    assert store.list_pending()[0]["overdue"] == 0


def test_two_stores_claim_once_and_restart_does_not_redispatch(tmp_path):
    now = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
    path = tmp_path / "reminders.db"
    first = ReminderStore(path, clock=lambda: now)
    second = ReminderStore(path, clock=lambda: now)
    events = []
    first.on_reminder(events.append)
    second.on_reminder(events.append)
    first.add("fixture occurrence", now - timedelta(minutes=1))
    barrier = threading.Barrier(2)
    def check(store):
        barrier.wait(timeout=2)
        store._check_due_reminders()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(check, store) for store in (first, second)]
        for future in futures:
            future.result(timeout=3)
    assert len(events) == 1
    restarted = ReminderStore(path, clock=lambda: now)
    restarted.on_reminder(events.append)
    restarted._check_due_reminders()
    assert len(events) == 1 and len(restarted.list_recent()) == 1


def test_reminder_text_commands_use_registry_without_provider_and_stop_pauses_delivery(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    events = []
    now = [datetime(2026, 10, 17, 2, tzinfo=timezone.utc)]
    assistant.reminder_store._clock = lambda: now[0]
    assistant.reminder_store.on_reminder(events.append)
    try:
        created = assistant.handle("remind me in 2 minutes to drink water")
        assert created.success and created.results
        assert "Asia/Kolkata" in created.reply
        assert assistant.memory.inspect() == []
        assistant.permissions.stop()
        now[0] += timedelta(minutes=3)
        assistant.reminder_store._check_due_reminders()
        assert events == []
        assistant.permissions.resume()
        assistant.reminder_store._check_due_reminders()
        assistant.reminder_store._check_due_reminders()
        assert len(events) == 1
        listed = assistant.handle("list reminders", lambda *_: True)
        assert listed.success
    finally:
        assistant.close()
