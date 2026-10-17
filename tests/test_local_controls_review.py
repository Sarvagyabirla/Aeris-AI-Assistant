import ctypes
import sys
import threading
from types import SimpleNamespace

import pytest

from aeris.router import LocalRouter
from aeris.state import CancellationToken
from aeris.tools.desktop import DesktopTools


@pytest.fixture
def audio(tmp_path, monkeypatch):
    calls = []
    class Endpoint:
        volume = 0.5
        muted = False
        def SetMasterVolumeLevelScalar(self, value, _):
            self.volume = value
        def GetMasterVolumeLevelScalar(self):
            return self.volume
        def SetMute(self, value, _):
            self.muted = bool(value)
        def GetMute(self):
            return self.muted
    endpoint = Endpoint()
    class Interface(ctypes.Structure):
        _iid_ = "fixture"
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        COINIT_APARTMENTTHREADED=2,
        CoInitialize=lambda: calls.append(("init", threading.get_ident())),
        CoInitializeEx=lambda _: calls.append(("init", threading.get_ident())),
        CoUninitialize=lambda: calls.append(("uninit", threading.get_ident()))))
    monkeypatch.setitem(sys.modules, "comtypes", SimpleNamespace(CLSCTX_ALL=1))
    monkeypatch.setitem(sys.modules, "pycaw.pycaw", SimpleNamespace(
        IAudioEndpointVolume=Interface,
        AudioUtilities=SimpleNamespace(GetSpeakers=lambda: SimpleNamespace(
            Activate=lambda *_: endpoint, FriendlyName="Fixture speakers"))))
    monkeypatch.setattr(ctypes, "cast", lambda value, _: value)
    tools = DesktopTools(None, tmp_path)
    monkeypatch.setattr(tools, "_require_windows", lambda: None)
    return tools, endpoint, calls


def test_repeated_mute_and_unmute_are_absolute_and_com_balanced(audio):
    tools, endpoint, calls = audio
    for action, muted in (("mute", True), ("mute", True), ("unmute", False), ("unmute", False)):
        result = tools.media_control({"action": action})
        assert result.success and result.data["muted"] is muted
        assert endpoint.muted is muted
    assert len(calls) == 8
    assert calls[::2] == [("init", threading.get_ident())] * 4
    assert calls[1::2] == [("uninit", threading.get_ident())] * 4


def test_volume_reads_back_observed_value_and_balances_com_on_error(audio, monkeypatch):
    tools, endpoint, calls = audio
    monkeypatch.setattr(endpoint, "SetMasterVolumeLevelScalar", lambda *_: None)
    result = tools.set_volume({"level": 35})
    assert not result.success and result.error == "verification_failed"
    assert result.data["level"] == 50
    assert calls[0][0] == "init" and calls[1][0] == "uninit"


def test_cancelled_audio_does_not_change_state(audio):
    tools, endpoint, _calls = audio
    token = CancellationToken()
    token.cancel()
    result = tools.set_volume({"level": 100}, token=token)
    assert not result.success and endpoint.volume == 0.5


@pytest.mark.parametrize("command,action", [("pause", "pause"), ("play", "play"),
                                            ("mute", "mute"), ("unmute", "unmute"),
                                            ("toggle playback", "play_pause"), ("toggle mute", "toggle_mute")])
def test_absolute_and_toggle_routes_are_distinct(command, action):
    assert LocalRouter().route(command).actions[0].arguments == {"action": action}


def test_absolute_pause_never_sends_toggle_key(audio, monkeypatch):
    tools, _, _ = audio
    # No native API is invoked when an absolute media-session adapter is absent.
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=SimpleNamespace(
        keybd_event=lambda *_: pytest.fail("Absolute pause became a toggle"))), raising=False)
    result = tools.media_control({"action": "pause"})
    assert not result.success and result.error == "unsupported_absolute_media"
