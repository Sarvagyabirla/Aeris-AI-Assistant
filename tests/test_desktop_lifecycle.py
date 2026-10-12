import os
import threading
import time

import pytest
from test_assistant import make_config

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="Qt event-loop tests require the optional Windows/UI extra")
from PySide6.QtWidgets import QApplication

from aeris.assistant import AerisAssistant
from aeris.core.tts_worker import global_tts
from aeris.models import ActionRequest, PermissionLevel
from aeris.ui.desktop import AerisMainWindow, AssistantWorker


def pump(app, condition, timeout=3):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert condition()


def test_real_window_text_dispatch_and_clean_close(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    spoken = []
    monkeypatch.setattr(global_tts, "speak", lambda text, token=None: spoken.append(text))
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(hands_free=False))
    window = AerisMainWindow(assistant)
    window.show()
    window.dashboard.input_field.setText("open notepad")
    window.dashboard.send_command()
    pump(app, lambda: window.dashboard.chat_history.count() >= 2)
    assert "SIMULATION" in window.mode_label.text()
    assert "Dry run" in window.dashboard.chat_history.item(1).text()
    assert spoken and "Simulation only" in spoken[0]
    window.close()
    pump(app, lambda: not window.isVisible())
    assert not window.worker.isRunning()
    assert not window.hands_free.isRunning()


def test_stale_approval_rejected_and_stop_unblocks_wait(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    reached = threading.Event()
    effects = []
    def handle(text, approve, token):
        request = ActionRequest("fixture.effect")
        reached.set()
        if approve(request, PermissionLevel.CONFIRM, "fixture"):
            token.raise_if_cancelled()
            effects.append(True)
        token.raise_if_cancelled()
    monkeypatch.setattr(assistant, "handle", handle)
    worker = AssistantWorker(assistant)
    worker.start()
    worker.process_command("fixture")
    pump(app, reached.is_set)
    worker.provide_permission(True, "wrong-request-id")
    assert not worker._permission_event.is_set()
    worker.cancel_current()
    pump(app, lambda: worker.current_token is None)
    assert effects == []
    worker.stop_worker()
    assert worker.wait(2000)


def test_queue_full_visible_to_caller(tmp_path):
    worker = AssistantWorker(AerisAssistant(make_config(tmp_path)))
    assert worker.process_command("first")
    assert not worker.process_command("second")
    worker.cancel_current()
    assert worker.command_queue.empty()


def test_memory_view_inspects_and_forgets_only_selected_local_record(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from aeris.ui.memory_view import MemoryView
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.memory.add("user", "fixture local memory", classification="LOCAL_ONLY")
    view = MemoryView(assistant.memory)
    view.refresh()
    assert view.list.count() == 1
    view.list.setCurrentRow(0)
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Yes)
    view.forget()
    app.processEvents()
    assert view.list.count() == 0
    assert assistant.memory.inspect() == []


def test_settings_apply_does_not_block_qt_event_loop(tmp_path, monkeypatch):
    from aeris.ui.desktop import SettingsTab
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    entered = threading.Event()
    release = threading.Event()
    def apply(config):
        entered.set()
        assert release.wait(3)
    monkeypatch.setattr(assistant, "apply_settings", apply)
    tab = SettingsTab(assistant)
    tab.save_settings()
    pump(app, entered.is_set)
    assert not tab.save_btn.isEnabled()
    assert tab.apply_worker.isRunning()
    release.set()
    pump(app, lambda: tab.save_btn.isEnabled() and not tab.apply_worker.isRunning())


def test_close_cleanup_is_owned_once_off_gui_thread(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    entered = threading.Event()
    release = threading.Event()
    calls = []
    def cleanup():
        calls.append(threading.get_ident())
        entered.set()
        assert release.wait(3)
        return True
    monkeypatch.setattr(assistant, "close", cleanup)
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    window = AerisMainWindow(assistant)
    window.show()
    window.close()
    pump(app, entered.is_set)
    window.close()
    app.processEvents()
    assert calls == [calls[0]] and calls[0] != threading.get_ident()
    assert window.isVisible()
    release.set()
    pump(app, lambda: not window.isVisible())