from datetime import datetime, timedelta, timezone

import pytest
from test_assistant import make_config


def test_reminders_tab_creates_notifies_snoozes_and_cancels_through_worker(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.core.tts_worker import global_tts
    from aeris.ui.desktop import AerisMainWindow
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    now = [datetime(2026, 10, 17, 2, tzinfo=timezone.utc)]
    assistant.reminder_store._clock = lambda: now[0]
    monkeypatch.setattr(global_tts, "speak", lambda *_a, **_k: None)
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    window = AerisMainWindow(assistant)
    window.show()
    view = window.reminders_view
    window.tabs.setCurrentWidget(view)
    try:
        view.message.setText("Fixture private reminder")
        view.when.setText("in 2 minutes")
        view.create_btn.click()
        pump(app, lambda: len(assistant.reminder_store.list_pending()) == 1 and window.worker.current_token is None)
        now[0] += timedelta(minutes=3)
        assistant.reminder_store._check_due_reminders()
        pump(app, lambda: any("A reminder is due" in window.dashboard.chat_history.item(i).text()
                              for i in range(window.dashboard.chat_history.count())))
        notices = [window.dashboard.chat_history.item(i).text() for i in range(window.dashboard.chat_history.count())
                   if "A reminder is due" in window.dashboard.chat_history.item(i).text()]
        assert len(notices) == 1 and "Fixture private" not in notices[0]
        pump(app, lambda: view.records.count() > 0)
        view.records.setCurrentRow(0)
        view.snooze()
        pump(app, lambda: len(assistant.reminder_store.list_pending()) == 1 and window.worker.current_token is None)
        view.cancel()
        pump(app, lambda: not assistant.reminder_store.list_pending() and window.worker.current_token is None)
    finally:
        window.close()
        pump(app, lambda: not window.isVisible())
    assert not assistant.reminder_store._thread.is_alive()
