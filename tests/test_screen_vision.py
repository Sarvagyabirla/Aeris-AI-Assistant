from aeris.integrations.screen_vision import ScreenVision


def test_screen_vision_requires_configured_ai():
    result = ScreenVision(None, "test-model").inspect({"question": "What is visible?"})
    assert not result.success
    assert result.error == "ai_not_configured"
