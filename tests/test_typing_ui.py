"""Offscreen target selection/approval; native windows and key input are fixtures."""
import threading

import pytest
from test_assistant import make_config


def test_window_selector_runs_off_ui_thread_and_binds_choice(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QInputDialog
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.core.tts_worker import global_tts
    from aeris.models import ActionResult
    from aeris.ui.desktop import AerisMainWindow
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    target = {"window_id": 42, "expected_title": "Fixture editor", "process_name": "fixture.exe"}
    entered, release = threading.Event(), threading.Event()
    threads, selected = [], []
    def candidates():
        threads.append(threading.get_ident())
        entered.set()
        assert release.wait(2)
        return [target]
    monkeypatch.setattr(assistant._desktop, "list_typing_targets", candidates)
    monkeypatch.setattr(assistant._desktop, "select_typing_target", lambda hwnd: selected.append(hwnd) or ActionResult(True, "selected"))
    monkeypatch.setattr(QInputDialog, "getItem", lambda _self, _title, _prompt, items, *_: (items[0], True))
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.typing_target_btn.click()
        pump(app, entered.is_set)
        assert threads[0] != threading.get_ident()
        assert not window.typing_target_btn.isEnabled()
        release.set()
        pump(app, lambda: bool(selected))
        assert selected == [42]
        assert "Fixture editor" in window.typing_target_label.text()
    finally:
        release.set()
        window.close()
        pump(app, lambda: not window.isVisible())


@pytest.mark.parametrize("allow,restore,expected", [(False, True, False), (True, False, False), (True, True, True)])
def test_typing_confirmation_restores_only_approved_current_target(tmp_path, monkeypatch, allow, restore, expected):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QMessageBox
    from test_desktop_lifecycle import pump

    from aeris.assistant import AerisAssistant
    from aeris.core.tts_worker import global_tts
    from aeris.models import ActionRequest, PermissionLevel
    from aeris.state import CancellationToken
    from aeris.ui.desktop import AerisMainWindow
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path))
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    window = AerisMainWindow(assistant)
    window.show()
    restored, decisions = [], []
    request = ActionRequest("desktop.type_text", {"text": "Hello नमस्ते", "window_id": 42,
        "focus_window_id": 43, "expected_title": "Fixture", "process_name": "fixture.exe"})
    window.worker.current_token = CancellationToken()
    window.worker._pending_request_id = request.request_id
    monkeypatch.setattr(QMessageBox, "exec", lambda _: QMessageBox.Yes if allow else QMessageBox.No)
    monkeypatch.setattr(assistant._desktop, "restore_typing_target", lambda args, token=None: restored.append(args) or restore)
    monkeypatch.setattr(window.worker, "provide_permission", lambda decision, request_id: decisions.append((decision, request_id)))
    try:
        window.handle_permission(request, PermissionLevel.CONFIRM, "fixture")
        assert decisions == [(expected, request.request_id)]
        assert bool(restored) == allow
    finally:
        window.worker.current_token = None
        window.close()
        pump(app, lambda: not window.isVisible())
