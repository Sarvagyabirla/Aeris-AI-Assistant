from aeris.models import ActionRequest


def test_action_fingerprint_is_stable_for_argument_order():
    first = ActionRequest("tool", {"a": 1, "b": 2})
    second = ActionRequest("tool", {"b": 2, "a": 1})
    assert first.fingerprint() == second.fingerprint()


def test_action_fingerprint_changes_with_arguments():
    first = ActionRequest("tool", {"value": 1})
    second = ActionRequest("tool", {"value": 2})
    assert first.fingerprint() != second.fingerprint()


def test_preview_contains_tool_and_arguments():
    request = ActionRequest("email.send", {"to": "test@example.com"})
    assert "email.send" in request.preview()
    assert "test@example.com" in request.preview()
