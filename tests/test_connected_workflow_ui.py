import os
from dataclasses import replace

import pytest
from test_assistant import make_config

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QMessageBox
from test_desktop_lifecycle import pump

from aeris.assistant import AerisAssistant
from aeris.core.tts_worker import global_tts
from aeris.models import ActionResult
from aeris.ui.desktop import AerisMainWindow


def test_review_save_and_run_study_routine_through_qt_worker(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    calls = []
    for tool in ('desktop.open_app', 'desktop.set_volume'):
        assistant.registry._tools[tool] = replace(assistant.registry._tools[tool],
            handler=lambda args, token=None: calls.append(args) or ActionResult(True, 'Fixture verified', {'verified': True}))
    monkeypatch.setattr(global_tts, 'speak', lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, 'exec', lambda _: QMessageBox.Save)
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.tasks_view.study_template()
        window.tasks_view.save_routine()
        assert window.tasks_view.routines.count() == 1
        window.tasks_view.routines.setCurrentRow(0)
        window.tasks_view.run_selected()
        pump(app, lambda: window.dashboard.chat_history.count() > 0)
        assert len(calls) == 2 and window.dashboard.task_steps.count() == 3
        assert window.tasks_view.history.count() == 1
        assert 'completed' in window.tasks_view.history.item(0).text()
        window.tasks_view.disable_selected()
        assert assistant.routine_store.records()[0][1] == 0
    finally:
        window.quit_application()
        pump(app, lambda: not window.isVisible() and not window.worker.isRunning())


def test_permission_view_revoke_is_immediate_and_settings_preserved(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    monkeypatch.setattr('aeris.secrets.read_key', lambda *_: None)
    monkeypatch.setattr('aeris.secrets.write_key', lambda *_: None)
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.permissions_view.roots.setCurrentRow(0)
        window.permissions_view.revoke_selected()
        with pytest.raises(PermissionError):
            assistant._files.guard.resolve(tmp_path / 'fixture.txt')
        pump(app, lambda: window.permissions_view.apply_worker is not None and not window.permissions_view.apply_worker.isRunning())
        app.processEvents()
        assert assistant.config.allowed_paths == ()
        assert assistant.config.dry_run and not assistant.config.ai_enabled
        assert not assistant.permissions.stopped  # revoke cancels task, distinct from Emergency Stop
    finally:
        window.quit_application()
        pump(app, lambda: not window.isVisible() and not window.worker.isRunning())


def test_character_follows_real_speech_permission_and_emergency_state(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    window = AerisMainWindow(assistant)
    window.show()
    try:
        global_tts.speaking.set()
        window.refresh_presence()
        assert window.presence.phase == 'speaking'
        global_tts.speaking.clear()
        window.emergency_stop()
        window.refresh_presence()
        assert window.presence.phase == 'interrupted'
        assert assistant.permissions.stopped
        assistant.permissions.resume()
        window.worker.process_command('status')
        monkeypatch.setattr(global_tts, 'speak', lambda *a, **k: None)
        pump(app, lambda: window.dashboard.chat_history.count() > 0)
        window.refresh_presence()
        assert window.presence.phase == 'offline'
    finally:
        global_tts.speaking.clear()
        window.quit_application()
        pump(app, lambda: not window.isVisible() and not window.worker.isRunning())
