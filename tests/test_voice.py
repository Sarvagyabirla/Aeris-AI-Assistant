from aeris.integrations.voice import VoiceService


def test_voice_defaults_to_cpu():
    voice = VoiceService()
    assert voice.device == "cpu"
    assert voice.language == "en"


def test_invalid_voice_device_falls_back_to_cpu():
    voice = VoiceService(device="magic-gpu")
    assert voice.device == "cpu"


def test_auto_language_disables_forcing():
    voice = VoiceService(language="auto")
    assert voice.language is None
