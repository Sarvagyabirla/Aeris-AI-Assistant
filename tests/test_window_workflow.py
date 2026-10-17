import sys
from types import SimpleNamespace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant


@pytest.fixture
def window_fixture(tmp_path, monkeypatch):
    windows = {101: {"pid": 42, "created": 100.0, "title": "Fixture unsaved note"}}
    posted = []
    class Process:
        info = {"name": "notepad.exe"}
        def __init__(self, pid):
            self.pid = pid
        def name(self):
            return "notepad.exe"
        def create_time(self):
            return next(record["created"] for record in windows.values() if record["pid"] == self.pid)
        def terminate(self):
            pytest.fail("Graceful close must never terminate a process")
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(Process=Process, process_iter=lambda *_: [Process(42)],
        AccessDenied=PermissionError, NoSuchProcess=ProcessLookupError, Error=OSError))
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(
        EnumWindows=lambda callback, data: [callback(hwnd, data) for hwnd in windows],
        IsWindow=lambda hwnd: hwnd in windows, IsWindowVisible=lambda hwnd: hwnd in windows,
        GetWindowText=lambda hwnd: windows[hwnd]["title"], GetClassName=lambda _: "Notepad",
        GetForegroundWindow=lambda: 101, PostMessage=lambda *args: posted.append(args)))
    monkeypatch.setitem(sys.modules, "win32process", SimpleNamespace(GetWindowThreadProcessId=lambda hwnd: (1, windows[hwnd]["pid"])))
    monkeypatch.setattr("aeris.tools.desktop.DesktopTools._require_windows", lambda _: None)
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    yield assistant, windows, posted
    assistant.close()


def test_close_app_previews_exact_window_then_requests_graceful_close(window_fixture):
    assistant, _windows, posted = window_fixture
    previews = []
    turn = assistant.handle("close notepad", lambda request, *_: previews.append(dict(request.arguments)) or True)
    assert turn.success
    assert previews[0]["window_id"] == 101 and previews[0]["process_id"] == 42
    assert previews[0]["expected_title"] == "Fixture unsaved note"
    assert posted == [(101, 0x0010, 0, 0)]
    assert turn.results[0].data["verified"] is False


def test_close_app_replaced_window_during_confirmation_is_rejected(window_fixture):
    assistant, windows, posted = window_fixture
    def approve(*_):
        windows[101]["created"] = 200.0
        return True
    turn = assistant.handle("close notepad", approve)
    assert not turn.success and turn.results[0].error == "stale_window"
    assert posted == []


def test_close_app_denied_confirmation_never_posts(window_fixture):
    assistant, _windows, posted = window_fixture
    turn = assistant.handle("close notepad", lambda *_: False)
    assert not turn.success and posted == []
