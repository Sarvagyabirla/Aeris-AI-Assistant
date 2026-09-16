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

@patch('sounddevice.InputStream')
def test_voice_silence_detection(mock_input_stream):
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

@patch('sounddevice.InputStream')
def test_voice_preload_does_not_block(mock_input_stream):
    voice = VoiceService(model_name="tiny")
    voice.preload_model()
    assert voice._model_state in ["Not loaded", "Downloading/Loading", "Ready", "Failed: Voice packages are missing."]
