from aeris.models import ActionRequest, PermissionLevel
from aeris.permissions import ApprovalManager, PermissionEngine


def test_approval_is_bound_to_exact_action():
    manager = ApprovalManager()
    approved = ActionRequest("files.delete", {"path": "a.txt"})
    changed = ActionRequest("files.delete", {"path": "b.txt"})
    token = manager.issue(approved)
    assert manager.consume(token, changed) is False
    assert manager.consume(token, approved) is True


def test_approval_is_one_time_use():
    manager = ApprovalManager()
    request = ActionRequest("email.send", {"to": "a@example.com"})
    token = manager.issue(request)
    assert manager.consume(token, request) is True
    assert manager.consume(token, request) is False


def test_auto_action_does_not_prompt():
    engine = PermissionEngine()
    called = False

    def callback(*_):
        nonlocal called
        called = True
        return False

    decision = engine.authorize(ActionRequest("browser.search_web"), PermissionLevel.AUTO, callback)
    assert decision.allowed is True
    assert called is False


def test_session_permission_prompts_once():
    engine = PermissionEngine()
    calls = 0

    def callback(*_):
        nonlocal calls
        calls += 1
        return True

    request = ActionRequest("files.read", {"path": "notes.txt"})
    assert engine.authorize(request, PermissionLevel.SESSION, callback).allowed
    assert engine.authorize(request, PermissionLevel.SESSION, callback).allowed
    assert calls == 1


def test_confirmation_denial_fails_closed():
    engine = PermissionEngine()
    decision = engine.authorize(
        ActionRequest("email.send", {"to": "a@example.com"}),
        PermissionLevel.CONFIRM,
        lambda *_: False,
    )
    assert decision.allowed is False


def test_blocked_action_cannot_be_approved():
    engine = PermissionEngine()
    decision = engine.authorize(
        ActionRequest("system.shell", {"command": "anything"}),
        PermissionLevel.BLOCKED,
        lambda *_: True,
    )
    assert decision.allowed is False


def test_kill_switch_state():
    engine = PermissionEngine()
    assert not engine.stopped
    engine.stop()
    assert engine.stopped
    engine.resume()
    assert not engine.stopped
