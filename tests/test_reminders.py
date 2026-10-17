from datetime import datetime, timedelta, timezone

from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest
from aeris.reminders import ReminderStore
from aeris.tools.reminders import ReminderTools


def test_reminder_store_add_and_list_pending(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    now = datetime.now(timezone.utc)
    fire_at = now + timedelta(hours=1)

    rid = store.add("Drink water", fire_at)
    assert rid is not None

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == rid
    assert pending[0]["message"] == "Drink water"
    assert pending[0]["recurrence"] is None


def test_reminder_store_deduplication(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    now = datetime.now(timezone.utc)
    fire_at = now + timedelta(hours=1)

    rid1 = store.add("Take medication", fire_at)
    # Adding same message within 5s window returns existing id
    rid2 = store.add("Take medication", fire_at + timedelta(seconds=2))
    assert rid1 == rid2

    pending = store.list_pending()
    assert len(pending) == 1


def test_reminder_store_restart_persistence(tmp_path):
    db_path = tmp_path / "reminders.db"
    store1 = ReminderStore(db_path)
    fire_at = datetime.now(timezone.utc) + timedelta(days=1)
    rid = store1.add("Review code changes", fire_at)
    store1.stop()

    # Re-open with new store instance pointing to same file
    store2 = ReminderStore(db_path)
    pending = store2.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == rid
    assert pending[0]["message"] == "Review code changes"
    store2.stop()


def test_reminder_store_cancel_and_snooze(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    fire_at = datetime.now(timezone.utc) + timedelta(hours=2)
    rid = store.add("Meeting with team", fire_at)

    # Snooze
    ok = store.snooze(rid, minutes=15)
    assert ok is True
    pending = store.list_pending()
    assert pending[0]["snoozed_until"] is not None

    # Cancel
    cancelled = store.cancel(rid)
    assert cancelled is True
    assert len(store.list_pending()) == 0


def test_reminder_store_due_and_overdue_handling(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    events = []
    store.on_reminder(lambda r: events.append(r))

    now = datetime.now(timezone.utc)
    # Reminder scheduled 10 minutes ago -> overdue
    overdue_fire = now - timedelta(minutes=10)
    store.add("Overdue task", overdue_fire)

    # Reminder scheduled 1 minute ago -> due (not overdue)
    due_fire = now - timedelta(minutes=1)
    store.add("Just due task", due_fire)

    store._check_due_reminders()

    assert len(events) == 2
    overdue_item = next(e for e in events if e["message"] == "Overdue task")
    assert overdue_item["overdue"] is True

    due_item = next(e for e in events if e["message"] == "Just due task")
    assert due_item["overdue"] is False


def test_reminder_store_recurrence(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    events = []
    store.on_reminder(lambda r: events.append(r))

    now = datetime.now(timezone.utc)
    fire_at = now - timedelta(seconds=10)
    store.add("Daily standup", fire_at, recurrence="daily")

    store._check_due_reminders()
    assert len(events) == 1
    assert events[0]["message"] == "Daily standup"

    # A recurring reminder should have been spawned for tomorrow
    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0]["message"] == "Daily standup"
    assert pending[0]["recurrence"] == "daily"


def test_reminder_tools_nlp_parsing_and_execution(tmp_path):
    db_path = tmp_path / "reminders.db"
    store = ReminderStore(db_path)
    tools = ReminderTools(store)

    # Valid in 30 minutes
    res = tools.set_reminder({"message": "Stretch legs", "when": "in 30 minutes"})
    assert res.success is True
    assert "reminder_id" in res.data

    # List
    list_res = tools.list_reminders({})
    assert list_res.success is True
    assert len(list_res.data["reminders"]) == 1

    # Snooze
    rid = res.data["reminder_id"]
    snooze_res = tools.snooze_reminder({"reminder_id": rid, "minutes": 20})
    assert snooze_res.success is True

    # Cancel
    cancel_res = tools.cancel_reminder({"reminder_id": rid})
    assert cancel_res.success is True


def test_assistant_reminder_integration(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    try:
        # Set reminder via registry
        action = ActionRequest(
            "reminder.set",
            {"message": "Submit report", "when": "in 15 minutes"},
            source_text="remind me to submit report in 15 minutes",
        )
        res = assistant.registry.execute(action, lambda *_: True)
        assert res.success is True
        rid = res.data["reminder_id"]

        # List reminders via registry
        list_action = ActionRequest("reminder.list", {})
        list_res = assistant.registry.execute(list_action, lambda *_: True)
        assert list_res.success is True
        assert any(r["id"] == rid for r in list_res.data["reminders"])

        # Snooze reminder via registry
        snooze_action = ActionRequest("reminder.snooze", {"reminder_id": rid, "minutes": 10})
        snooze_res = assistant.registry.execute(snooze_action, lambda *_: True)
        assert snooze_res.success is True

        # Cancel reminder via registry
        cancel_action = ActionRequest("reminder.cancel", {"reminder_id": rid})
        cancel_res = assistant.registry.execute(cancel_action, lambda *_: True)
        assert cancel_res.success is True
    finally:
        assistant.close()
