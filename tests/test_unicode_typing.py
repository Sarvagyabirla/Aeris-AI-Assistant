import ctypes
import sys
from types import SimpleNamespace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest
from aeris.state import CancellationToken
from aeris.tools import desktop


@pytest.fixture
def typing_fixture(tmp_path, monkeypatch):
    state = {"foreground": 101, "focus": 201, "title": "Fixture editor", "created": 100.0,
             "modifiers": False, "after_send": None, "count": None}
    sent = []

    class Process:
        def __init__(self, pid):
            self.pid = pid

        def name(self):
            return "fixture-editor.exe"

        def create_time(self):
            return state["created"]

    class Keyboard:
        def focus(self, _thread):
            return 101, state["focus"]

        def modifiers_down(self):
            return state["modifiers"]

        def send_scalar(self, character):
            sent.append(character)
            count = len(character.encode("utf-16-le"))
            if state["after_send"]:
                state["after_send"]()
            return state["count"] if state["count"] is not None else count

    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(Process=Process, Error=OSError))
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(
        IsWindow=lambda hwnd: hwnd in {101, 201}, IsWindowVisible=lambda hwnd: True,
        GetClassName=lambda hwnd: "FixtureEditor", GetWindowText=lambda hwnd: state["title"],
        GetForegroundWindow=lambda: state["foreground"], IsChild=lambda root, child: root == 101 and child == 201))
    monkeypatch.setitem(sys.modules, "win32process", SimpleNamespace(GetWindowThreadProcessId=lambda hwnd: (7, 42)))
    monkeypatch.setitem(sys.modules, "pyautogui", SimpleNamespace(write=lambda text, **_: sent.append(text)))
    monkeypatch.setattr(desktop, "_UnicodeKeyboard", Keyboard, raising=False)
    monkeypatch.setattr(desktop.DesktopTools, "_require_windows", lambda _: None)
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    yield assistant, state, sent
    assistant.close()


def test_unicode_typing_binds_native_target_before_approval(typing_fixture):
    assistant, _, sent = typing_fixture
    previews = []
    text = "नमस्ते café 😀"
    turn = assistant.handle("type " + text, lambda request, *_: previews.append(request.arguments.copy()) or True)
    assert previews[0].get("window_id") == 101
    assert previews[0]["focus_window_id"] == 201
    assert previews[0]["process_id"] == 42
    assert previews[0]["expected_title"] == "Fixture editor"
    assert turn.success and sent == list(text)
    data = turn.results[0].data
    assert data["verified"] is False
    assert data["characters_dispatched"] == len(text)
    assert data["input_events_inserted"] == len(text.encode("utf-16-le"))


@pytest.mark.parametrize("changed", ["foreground", "focus", "title", "created"])
def test_typing_rejects_target_changed_during_approval(typing_fixture, changed):
    assistant, state, sent = typing_fixture

    def approve(*_):
        state[changed] = "Changed title" if changed == "title" else 999
        return True

    turn = assistant.handle("type fixture", approve)
    assert not turn.success and turn.results[0].error == "stale_typing_target"
    assert sent == []


def test_typing_stops_between_characters_on_focus_change(typing_fixture):
    assistant, state, sent = typing_fixture
    state["after_send"] = lambda: state.update(foreground=999)
    turn = assistant.handle("type abc", lambda *_: True)
    assert sent == ["a"]
    assert not turn.success and turn.results[0].error == "stale_typing_target"
    assert turn.results[0].data["characters_dispatched"] == 1
    assert turn.results[0].data["uncertain"] is True


def test_typing_cancellation_retains_partial_dispatch(typing_fixture):
    assistant, state, sent = typing_fixture
    token = CancellationToken()
    state["after_send"] = token.cancel
    result = assistant.registry.execute(ActionRequest("desktop.type_text", {"text": "abc"}),
                                        lambda *_: True, token=token)
    assert sent == ["a"]
    assert not result.success and result.error == "cancelled_after_effect"
    assert result.data["characters_dispatched"] == 1
    assert result.data["input_events_inserted"] == 2


def test_typing_partial_native_failure_is_never_retried(typing_fixture):
    assistant, state, sent = typing_fixture
    state["count"] = 1
    turn = assistant.handle("type abc", lambda *_: True)
    assert sent == ["a"]
    assert not turn.success and turn.results[0].error == "input_dispatch_failed"
    assert turn.results[0].data["input_events_inserted"] == 1
    assert turn.results[0].data["characters_dispatched"] == 0
    assert turn.results[0].data["uncertain"] is True


def test_typing_denial_and_held_modifiers_dispatch_nothing(typing_fixture):
    assistant, state, sent = typing_fixture
    assert not assistant.handle("type abc", lambda *_: False).success
    state["modifiers"] = True
    turn = assistant.handle("type abc", lambda *_: True)
    assert not turn.success and turn.results[0].error == "keyboard_modifiers_active"
    assert sent == []


def test_typing_requires_prepared_scope_for_direct_handler(typing_fixture):
    _, _, sent = typing_fixture
    result = desktop.DesktopTools().type_text({"text": "abc"})
    assert not result.success and result.error == "typing_scope_required"
    assert sent == []


def test_selected_target_is_reobserved_and_never_silently_rebound(typing_fixture):
    assistant, state, sent = typing_fixture
    tool = assistant._desktop
    assert tool.select_typing_target(101).success
    state["foreground"] = 999  # chooser is now foreground, selected editor remains explicit.
    prepared = tool.prepare_type_text({"text": "abc"})
    assert prepared["window_id"] == 101
    state["created"] = 200.0
    result = tool.prepare_type_text({"text": "abc"})
    assert not result.success and result.error == "stale_typing_target"
    assert sent == []


def test_explicit_restore_checks_identity_and_foreground_without_typing(typing_fixture, monkeypatch):
    assistant, state, sent = typing_fixture
    tool = assistant._desktop
    prepared = tool.prepare_type_text({"text": "abc"})
    state["foreground"] = 999
    restored = []
    gui = sys.modules["win32gui"]

    def activate(window_id):
        restored.append(window_id)
        state["foreground"] = window_id

    monkeypatch.setattr(gui, "SetForegroundWindow", activate, raising=False)
    assert tool.restore_typing_target(prepared)
    assert restored == [101] and sent == []
    state["created"] = 200.0
    assert not tool.restore_typing_target(prepared)
    assert restored == [101]


def test_native_unicode_adapter_uses_correct_abi_and_surrogate_batches():
    batches = []

    def send(count, events, size):
        batches.append((size, [(events[i].type, events[i].ki.wVk, events[i].ki.wScan,
                               events[i].ki.dwFlags) for i in range(count)]))
        return count

    def focus(thread_id, pointer):
        info = ctypes.cast(pointer, ctypes.POINTER(desktop._GuiThreadInfo)).contents
        assert info.cbSize == ctypes.sizeof(desktop._GuiThreadInfo) and thread_id == 7
        info.hwndActive = 101
        info.hwndFocus = 201
        return 1

    user32 = SimpleNamespace(SendInput=send, GetGUIThreadInfo=focus, GetAsyncKeyState=lambda _: 0)
    keyboard = desktop._UnicodeKeyboard(user32)
    assert keyboard.focus(7) == (101, 201)
    assert not keyboard.modifiers_down()
    assert keyboard.send_scalar("ह") == 2
    assert keyboard.send_scalar("😀") == 4
    expected_size = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    assert batches == [(expected_size, [(1, 0, 0x0939, 0x0004), (1, 0, 0x0939, 0x0006)]),
                       (expected_size, [(1, 0, 0xD83D, 0x0004), (1, 0, 0xDE00, 0x0004),
                                        (1, 0, 0xD83D, 0x0006), (1, 0, 0xDE00, 0x0006)])]


@pytest.mark.parametrize("text", ["abc\x00def", "abc\x1bdef", "abc\ud800def"])
def test_invalid_unicode_or_controls_are_rejected_before_approval(typing_fixture, text):
    assistant, _, sent = typing_fixture
    previews = []
    result = assistant.registry.execute(ActionRequest("desktop.type_text", {"text": text}),
                                        lambda *args: previews.append(args) or True)
    assert not result.success and result.error == "invalid_arguments"
    assert sent == [] and previews == []
