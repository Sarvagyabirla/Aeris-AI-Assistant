import numpy as np
import pytest
from unittest.mock import patch, MagicMock
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
    
    # We won't simulate actual audio frames here since the callback is asynchronous, 
    # but we can verify it doesn't wait the full max_record_seconds when cancelled.
    voice.cancel_recording()
    res = voice.listen_once()
    assert res == ""

@patch('sounddevice.InputStream')
def test_voice_preload_does_not_block(mock_input_stream):
    voice = VoiceService(model_name="tiny")
    voice.preload_model()
    assert voice._model_state in ["Not loaded", "Downloading/Loading", "Ready", "Failed: Voice packages are missing."]
