from aeris.integrations.screen_vision import ScreenVision


def test_screen_vision_requires_configured_ai():
    result = ScreenVision(None, "test-model").inspect({"question": "What is visible?"})
    assert not result.success
    assert result.error == "ai_not_configured"


def test_screen_upload_requires_explicit_region():
    result = ScreenVision("fake-no-network-key", "fixture").inspect({"question": "fixture"})
    assert result.error == "capture_scope_required"


def test_monitor_fails_closed_without_safe_selected_scope():
    result = ScreenVision("fake-no-network-key", "fixture").monitor_screen({"duration_minutes": 1})
    assert result.error == "monitor_scope_required"
