from unittest.mock import MagicMock, patch

from aeris.integrations.voice import VoiceService


def test_voice_defaults():
    voice = VoiceService()
    assert voice.device == "cpu"
    assert voice.language is None # 'auto' translates to None
    assert voice.max_record_seconds == 6

def test_voice_cancellation():
    voice = VoiceService()
    voice.cancel_recording()
    assert voice._cancel_flag is True

def test_voice_silence_detection():
    import pytest
    sd = pytest.importorskip("sounddevice", reason="Audio adapter fixture requires sounddevice")
    with patch.object(sd, "InputStream") as mock_input_stream:
        _capture_cancel_fixture(mock_input_stream)


def _capture_cancel_fixture(mock_input_stream):
    # Simulate a stream that instantly returns silence
    voice = VoiceService(noise_threshold=500, silence_timeout_ms=500)
    
    # Mocking InputStream as a context manager
    mock_stream_instance = MagicMock()
    mock_input_stream.return_value.__enter__.return_value = mock_stream_instance
    
    import threading
    import time
    def cancel():
        time.sleep(0.1)
        voice.cancel_recording()
        
    t = threading.Thread(target=cancel)
    t.start()
    res = voice.listen_once()
    t.join()
    assert res == ""

def test_voice_preload_does_not_block():
    voice = VoiceService(model_name="tiny")
    import threading
    loaded = threading.Event()
    def fake_load():
        loaded.set()
        return MagicMock()
    with patch.object(voice, "_get_or_load_model", side_effect=fake_load):
        voice.preload_model()
        assert loaded.wait(2)


def test_cuda_generator_failure_retries_once_on_cpu(monkeypatch):
    import sys
    from types import SimpleNamespace

    import pytest
    np = pytest.importorskip("numpy", reason="Audio frame fixture requires numpy")
    sd = pytest.importorskip("sounddevice", reason="Audio frame fixture requires sounddevice")
    loads = []
    class Model:
        def __init__(self, name, device, compute_type):
            loads.append((device, compute_type))
            self.device = device
        def transcribe(self, *args, **kwargs):
            def segments():
                if self.device == "cuda":
                    raise RuntimeError("CUDA fixture generator failure")
                yield SimpleNamespace(text="open notepad")
            return segments(), None
    class Stream:
        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
        def __enter__(self):
            self.callback(np.ones((1600, 1), dtype=np.int16) * 1000, 1600, None, None)
            self.callback(np.zeros((1600, 1), dtype=np.int16), 1600, None, None)
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(sd, "InputStream", Stream)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    voice = VoiceService(device="cuda", silence_timeout_ms=100)
    assert voice.listen_once() == "open notepad"
    assert loads == [("cuda", "float16"), ("cpu", "int8")]
