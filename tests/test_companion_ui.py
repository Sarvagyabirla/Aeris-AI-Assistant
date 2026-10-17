"""Real Qt widgets and worker boundary; no personal windows/audio/settings."""
import os
import threading

import pytest
from test_assistant import make_config

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication
from test_desktop_lifecycle import pump

from aeris.assistant import AerisAssistant
from aeris.core.tts_worker import global_tts
from aeris.models import ActionResult, AssistantTurn
from aeris.ui.companion import ViewPreferences
from aeris.ui.desktop import AerisMainWindow


def test_companion_shares_running_state_and_stop(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr(global_tts, 'speak', lambda *a, **k: None)
    def handle(text, approve, token):
        entered.set()
        release.wait(2)
        return AssistantTurn(text, 'Retained fixture effect', [ActionResult(True, 'Retained')])
    monkeypatch.setattr(assistant, 'handle', handle)
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.worker.process_command('long fixture')
        pump(app, entered.is_set)
        window.show_companion()
        pump(app, lambda: window.companion.isVisible())
        assert window.companion.avatar.model is window.dashboard.avatar.model
        assert window.companion.testAttribute(Qt.WA_ShowWithoutActivating)
        assert window.companion.windowFlags() & Qt.WindowDoesNotAcceptFocus
        token = window.worker.current_token
        window.companion.stop_btn.click()
        assert token.is_cancelled
        window.show_dashboard()
        assert window.isVisible() and not window.companion.isVisible()
        release.set()
        pump(app, lambda: window.worker.current_token is None and window.dashboard.chat_history.count() > 0)
        assert 'Retained' in window.dashboard.chat_history.item(0).text()
    finally:
        release.set()
        window.quit_application()
        pump(app, lambda: not window.worker.isRunning() and not window.isVisible())


def test_click_through_recovery_and_hidden_animation(tmp_path):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.show_companion()
        app.processEvents()
        window.companion.set_click_through(True)
        assert not window.companion.click_through  # offscreen has no native recovery path
        window.companion.recovery_available = lambda: True  # explicit registered-shortcut fixture
        window.companion.set_click_through(True)
        assert window.companion.click_through
        window.recover_views()
        assert not window.companion.click_through and window.isVisible()
        window.dashboard.avatar.set_reduced_motion(True)
        assert not window.dashboard.avatar.animation_timer.isActive()
        window.dashboard.avatar.set_reduced_motion(False)
        window.hide()
        app.processEvents()
        assert not window.dashboard.avatar.animation_timer.isActive()
        window.companion.fit_to_screens([QRect(-1920, 0, 1920, 1080)])
        assert QRect(-1920, 0, 1920, 1080).contains(window.companion.geometry())
    finally:
        window.quit_application()
        pump(app, lambda: not window.worker.isRunning() and not window.isVisible())


def test_saved_view_and_mic_mute_do_not_change_assistant_config(tmp_path):
    path = tmp_path / 'presentation.json'
    prefs = ViewPreferences(path)
    prefs.save(view='companion', microphone_muted=True, reduced_motion=True)
    loaded = ViewPreferences(path)
    assert loaded.values['view'] == 'companion' and loaded.values['microphone_muted']
    assert loaded.values['reduced_motion']
    assert not (tmp_path / 'settings.json').exists()
    original = '{"microphone_muted": "false", "view": "unknown"}'
    path.write_text(original)
    assert ViewPreferences(path).values['view'] == 'dashboard'
    assert ViewPreferences(path).values['microphone_muted']
    assert path.read_text() == original
