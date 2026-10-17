"""Real Qt event-loop checks, isolated from user configuration and native effects."""
import threading

import pytest
from test_assistant import make_config


def test_cancelled_worker_retains_effects_without_speech(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.core.tts_worker import global_tts
    from aeris.models import ActionResult, AssistantTurn
    from aeris.ui.desktop import AssistantWorker
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    entered, release = threading.Event(), threading.Event()
    spoken, responses = [], []
    def handle(text, approve, token):
        entered.set()
        assert release.wait(2)
        return AssistantTurn(text, "Retained artifact: fixture.txt", [
            ActionResult(False, "Retained", {"path": "fixture.txt", "published": True}, "cancelled_after_publication")])
    monkeypatch.setattr(assistant, "handle", handle)
    monkeypatch.setattr(global_tts, "speak", lambda *a, **k: spoken.append(a))
    worker = AssistantWorker(assistant)
    worker.response_ready.connect(lambda _text, reply: responses.append(reply))
    worker.start()
    try:
        worker.process_command("fixture")
        pump(app, entered.is_set)
        worker.cancel_current()
        release.set()
        pump(app, lambda: bool(responses))
        assert "fixture.txt" in responses[0]
        assert spoken == []
    finally:
        release.set()
        worker.stop_worker()
        assert worker.wait(2000)
        assistant.close()


def test_failed_cleanup_has_explicit_retry_without_polling(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.core.tts_worker import global_tts
    from aeris.ui.desktop import AerisMainWindow
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    calls = []
    original = assistant.close
    def cleanup():
        calls.append(True)
        return len(calls) > 1
    monkeypatch.setattr(assistant, "close", cleanup)
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.close()
        pump(app, lambda: window._cleanup_worker is not None and not window._cleanup_worker.isRunning())
        app.processEvents()
        assert hasattr(window, "cleanup_retry_btn"), "Failed cleanup needs a visible Retry control"
        pump(app, lambda: window.cleanup_retry_btn.isVisible())
        assert window.isVisible() and len(calls) == 1
        assert "failed" in window.dashboard.status_label.text().lower()
        window.cleanup_retry_btn.click()
        pump(app, lambda: not window.isVisible())
        assert len(calls) == 2
    finally:
        if window.isVisible():
            monkeypatch.setattr(assistant, "close", lambda: True)
            if hasattr(window, "retry_cleanup"):
                window.retry_cleanup()
            else:
                window._cleanup_worker.cleaned = True
                window.close()
            pump(app, lambda: not window.isVisible())
        original()


def test_opted_in_cached_model_initializes_on_audio_thread_and_stop_prevents_capture(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.ui.desktop import AssistantWorker, HandsFreeWorker
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(hands_free=True))
    entered, release = threading.Event(), threading.Event()
    threads = []
    class Voice:
        _model_state = "Ready (fixture cache)"
        def __init__(self, *_):
            pass
        def initialize_cached_model(self):
            threads.append(threading.get_ident())
            entered.set()
            assert release.wait(2)
        def listen_once(self):
            pytest.fail("Capture started after Stop during initialization")
    monkeypatch.setattr("aeris.ui.desktop.VoiceService", Voice)
    worker = HandsFreeWorker(assistant, AssistantWorker(assistant))
    worker.start()
    try:
        pump(app, entered.is_set)
        assert threads[0] != threading.get_ident()
        worker.stop()
        release.set()
        assert worker.wait(2000)
    finally:
        release.set()
        worker.stop()
        worker.wait(2000)
        assistant.close()
