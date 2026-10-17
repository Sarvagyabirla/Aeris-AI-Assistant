"""Audio controller fixtures; no microphone, model server or system speech."""
import threading

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant


def test_custom_wake_phrase_routes_through_real_controller(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(wake_word="nova"))
    try:
        turn = assistant.handle("Okay, Nova, open Notepad")
        assert turn.results and turn.results[0].dry_run
        assert "desktop.open_app" in turn.results[0].message
    finally:
        assistant.close()


@pytest.mark.parametrize("barrier", ["speaking", "global_stop"])
def test_passive_voice_does_not_capture_during_speech_or_global_stop(tmp_path, monkeypatch, barrier):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.core.tts_worker import global_tts
    from aeris.ui.desktop import AssistantWorker, HandsFreeWorker
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(hands_free=True))
    captured, elapsed = threading.Event(), threading.Event()
    class Voice:
        _model_state = "Ready (fixture)"
        def __init__(self, *_):
            pass
        def initialize_cached_model(self):
            pass
        def begin_session(self):
            pass
        def listen_once(self):
            captured.set()
            worker.stop()
            return "Aeris stop"
    monkeypatch.setattr("aeris.ui.desktop.VoiceService", Voice)
    monkeypatch.setattr(global_tts, "speaking", threading.Event())
    if barrier == "speaking":
        global_tts.speaking.set()
    else:
        assistant.permissions.stop()
    worker = HandsFreeWorker(assistant, AssistantWorker(assistant))
    worker.start()
    try:
        QTimer.singleShot(160, elapsed.set)
        pump(app, elapsed.is_set)
        assert not captured.is_set(), "Passive input must pause during TTS and latched global Stop"
    finally:
        worker.stop()
        assert worker.wait(2000)
        assistant.close()


def test_push_to_talk_survives_audio_worker_restart(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QPushButton
    from test_desktop_lifecycle import pump

    from aeris.core.tts_worker import global_tts
    from aeris.ui.desktop import AerisMainWindow
    app = QApplication.instance() or QApplication([])
    captured = threading.Event()
    class Voice:
        _model_state = "fixture"
        def __init__(self, *_):
            pass
        def begin_session(self):
            pass
        def listen_once(self):
            captured.set()
            window.hands_free.stop()
            return ""
    monkeypatch.setattr("aeris.ui.desktop.VoiceService", Voice)
    monkeypatch.setattr(global_tts, "shutdown", lambda: True)
    assistant = AerisAssistant(make_config(tmp_path))
    window = AerisMainWindow(assistant)
    window.show()
    try:
        window.hands_free.stop()
        assert window.hands_free.wait(2000)
        button = next(button for button in window.findChildren(QPushButton) if button.text() == "Push to talk")
        button.click()
        pump(app, captured.is_set)
    finally:
        window.close()
        pump(app, lambda: not window.isVisible())


@pytest.mark.parametrize("speech", [False, True])
def test_capture_has_bounded_pre_roll_and_silence_never_loads_model(monkeypatch, speech):
    import sys
    import wave
    from types import SimpleNamespace

    from aeris.integrations.voice import AudioState, VoiceService
    np = pytest.importorskip("numpy", reason="Synthetic frame fixture requires the optional audio extra")
    states, frames = [], []
    voice = VoiceService(record_seconds=6 if speech else 2, silence_timeout_ms=200)
    voice.state_listener = lambda state, _: states.append(state)
    silence = np.zeros((1600, 1), dtype=np.int16)
    voiced = np.ones((1600, 1), dtype=np.int16) * 1000
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            chunks = [silence] * 30 + [voiced, voiced, silence, silence] if speech else [silence] * 20
            for chunk in chunks:
                self.callback(chunk, 1600, None, None)
            return self
        def __exit__(self, *_):
            pass
    class Model:
        def transcribe(self, path, **_):
            with wave.open(path, "rb") as recording:
                frames.append(recording.getnframes())
            return [SimpleNamespace(text=" open notepad ")], None
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(InputStream=Stream))
    voice._model = Model()
    if speech:
        assert voice.listen_once() == "open notepad"
        assert frames == [1600 * 7]  # 300ms pre-roll + 200ms voice + 200ms trailing silence.
        assert states == [AudioState.LISTENING, AudioState.TRANSCRIBING]
    else:
        monkeypatch.setattr(voice, "_get_or_load_model", lambda: pytest.fail("Silence must not trigger ASR"))
        assert voice.listen_once() == ""
        assert frames == []


def test_late_transcript_is_discarded_if_playback_begins_during_inference(monkeypatch):
    import sys
    from types import SimpleNamespace

    from aeris.integrations.voice import VoiceService
    np = pytest.importorskip("numpy", reason="Synthetic frame fixture requires the optional audio extra")
    voice = VoiceService(silence_timeout_ms=100)
    permitted = [True]
    voice.input_allowed = lambda: permitted[0]
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            for chunk in [np.ones((1600, 1), dtype=np.int16) * 1000, np.zeros((1600, 1), dtype=np.int16)]:
                self.callback(chunk, 1600, None, None)
            return self
        def __exit__(self, *_):
            pass
    class Model:
        def transcribe(self, *_, **__):
            permitted[0] = False
            return [SimpleNamespace(text="Aeris open Notepad")], None
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(InputStream=Stream))
    voice._model = Model()
    assert voice.listen_once() == ""


def test_address_grammar_uses_exact_configured_phrases_and_longest_boundary():
    from aeris.activation import extract_addressed_command
    from aeris.router import LocalRouter
    for text in ("Okay, Nova, open Notepad", "Hey Nova! open Notepad", "Nova: open Notepad"):
        command = extract_addressed_command(text, ("nova",))
        assert command == "open Notepad"
        action = LocalRouter("nova").route(text).actions[0]
        assert action.tool == "desktop.open_app" and action.arguments == {"name": "notepad"}
    assert extract_addressed_command("Nova Prime, open Notepad", ("nova", "nova prime")) == "open Notepad"
    assert extract_addressed_command("Novation open Notepad", ("nova",)) is None
    assert extract_addressed_command("Arish open Notepad", ("nova",)) is None
    assert extract_addressed_command("we mentioned Nova today", ("nova",)) is None


@pytest.mark.parametrize("during", ["load", "transcribe"])
def test_stop_during_cuda_failure_does_not_start_cpu_fallback(monkeypatch, during):
    import sys
    from types import SimpleNamespace

    from aeris.integrations.voice import VoiceService
    np = pytest.importorskip("numpy", reason="Synthetic frame fixture requires the optional audio extra")
    voice = VoiceService(device="cuda", silence_timeout_ms=100)
    loads = []
    class Model:
        def __init__(self, name, device, **_):
            loads.append(device)
            if during == "load" and device == "cuda":
                voice.cancel_recording()
                raise RuntimeError("CUDA fixture load failure")
        def transcribe(self, *_, **__):
            voice.cancel_recording()
            raise RuntimeError("CUDA fixture transcription failure")
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            for chunk in [np.ones((1600, 1), dtype=np.int16) * 1000, np.zeros((1600, 1), dtype=np.int16)]:
                self.callback(chunk, 1600, None, None)
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(InputStream=Stream))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    assert voice.listen_once() == ""
    assert loads == ["cuda"], "Stop must prevent starting the expensive CPU fallback"


def test_only_one_capture_can_own_the_input_stream(monkeypatch):
    import sys
    from types import SimpleNamespace

    from aeris.integrations.voice import VoiceService, VoiceUnavailableError
    entered, release = threading.Event(), threading.Event()
    voice = VoiceService()
    opened, results = [], []
    class Stream:
        def __init__(self, **_):
            opened.append(True)
        def __enter__(self):
            entered.set()
            assert release.wait(2)
            voice.cancel_recording()
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(InputStream=Stream))
    owner = threading.Thread(target=lambda: results.append(voice.listen_once()))
    owner.start()
    try:
        assert entered.wait(2)
        with pytest.raises(VoiceUnavailableError, match="already owned"):
            voice.listen_once()
    finally:
        release.set()
        owner.join(2)
    assert opened == [True] and results == [""]


def test_addressed_push_to_talk_can_cancel_a_busy_task(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_desktop_lifecycle import pump

    from aeris.core.tts_worker import global_tts
    from aeris.state import CancellationToken
    from aeris.ui.desktop import AssistantWorker, HandsFreeWorker
    app = QApplication.instance() or QApplication([])
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(wake_word="nova"))
    class Voice:
        def __init__(self, *_):
            pass
        def begin_session(self):
            pass
        def listen_once(self):
            return "Hey Nova, cancel this task"
    monkeypatch.setattr("aeris.ui.desktop.VoiceService", Voice)
    monkeypatch.setattr(global_tts, "last_output_at", 0)
    monkeypatch.setattr(global_tts, "speaking", threading.Event())
    tasks = AssistantWorker(assistant)
    token = tasks.current_token = CancellationToken()
    worker = HandsFreeWorker(assistant, tasks)
    worker.push_to_talk.set()
    worker.start()
    try:
        pump(app, lambda: token.is_cancelled)
        assert tasks.command_queue.empty()
    finally:
        worker.stop()
        assert worker.wait(2000)
        assistant.close()
