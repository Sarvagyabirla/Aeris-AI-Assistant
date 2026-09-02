from pathlib import Path

from aeris.audit import AuditLogger
from aeris.models import ActionRequest, ActionResult, PermissionLevel
from aeris.permissions import PermissionEngine
from aeris.registry import ToolRegistry, ToolSpec


def make_registry(tmp_path: Path, dry_run: bool = False):
    engine = PermissionEngine()
    registry = ToolRegistry(engine, AuditLogger(tmp_path / "audit.jsonl"), dry_run=dry_run)
    return engine, registry


def test_unknown_tool_is_rejected(tmp_path):
    _, registry = make_registry(tmp_path)
    result = registry.execute(ActionRequest("missing.tool"))
    assert not result.success
    assert result.error == "unknown_tool"


def test_missing_required_argument_is_rejected(tmp_path):
    _, registry = make_registry(tmp_path)
    registry.register(
        ToolSpec("demo", "demo", PermissionLevel.AUTO, lambda _: ActionResult(True, "ok"), ("name",))
    )
    result = registry.execute(ActionRequest("demo"))
    assert result.error == "invalid_arguments"


def test_dry_run_does_not_call_handler(tmp_path):
    _, registry = make_registry(tmp_path, dry_run=True)
    calls = 0

    def handler(_):
        nonlocal calls
        calls += 1
        return ActionResult(True, "executed")

    registry.register(ToolSpec("demo", "demo", PermissionLevel.AUTO, handler))
    result = registry.execute(ActionRequest("demo"))
    assert result.success and result.dry_run
    assert calls == 0


def test_kill_switch_blocks_normal_tools(tmp_path):
    engine, registry = make_registry(tmp_path)
    registry.register(ToolSpec("demo", "demo", PermissionLevel.AUTO, lambda _: ActionResult(True, "ok")))
    engine.stop()
    result = registry.execute(ActionRequest("demo"))
    assert not result.success
    assert result.error == "kill_switch"


def test_handler_exception_is_contained(tmp_path):
    _, registry = make_registry(tmp_path)

    def broken(_):
        raise RuntimeError("boom")

    registry.register(ToolSpec("demo", "demo", PermissionLevel.AUTO, broken))
    result = registry.execute(ActionRequest("demo"))
    assert not result.success
    assert result.error == "boom"


def test_audit_request_does_not_store_raw_source_text():
    request = ActionRequest("demo", {"prompt": "private idea"}, source_text="private command")
    payload = ToolRegistry._audit_request(request)
    assert "source_text" not in payload
    assert payload["arguments"]["prompt"] == "private idea"
