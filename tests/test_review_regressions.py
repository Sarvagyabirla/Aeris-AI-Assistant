"""17 October review regressions through production router/registry/controller boundaries."""
import hashlib
import json

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest, ActionResult, PermissionLevel, PlannedResponse
from aeris.registry import ToolSpec
from aeris.router import LocalRouter
from aeris.schemas import ApplyDiff, InspectScreen
from aeris.state import CancellationToken
from aeris.tools.coding import CodingTools


@pytest.mark.parametrize("command", [
    "don't set volume to 100", "do not set brightness to 80", "never set volume to 100",
    '"set volume to 100"', "'set volume to 100'", "if I say set volume to 100",
    "imagine set brightness to 90", "he said set volume to 100",
    "what happens when I set volume to 100?", "set volume to 100 if I ask later",
    "set brightness to -10", "set volume to 35.5", "set volume to 101",
    "set volume to 1e2", "set volume to fifty point five", "set volume to 50/100",
])
def test_unsafe_control_is_locally_clarified_without_actions(command):
    plan = LocalRouter().route(command)
    assert plan is not None, "Unsafe commands must not fall through to a planner"
    assert not plan.actions
    assert plan.reply


def test_negated_intent_never_reaches_provider_or_desktop(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    class ForbiddenPlanner:
        def plan(self, *_):
            pytest.fail("Negated local request reached a planner")
    assistant._gemini = assistant._ollama = ForbiddenPlanner()
    monkeypatch.setattr(assistant.registry, "execute", lambda *_a, **_k: pytest.fail("Effect attempted"))
    try:
        assert assistant.handle("don't set volume to 100", lambda *_: True).reply
    finally:
        assistant.close()


def patch_fixture(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    workspace = tmp_path / "projects"
    workspace.mkdir()
    path = workspace / "main.py"
    path.write_bytes(b"print('old')\r\n")
    tools = CodingTools((tmp_path,), workspace, None, "fixture")
    assistant.registry.register(ToolSpec("fixture.patch", "patch", PermissionLevel.CONFIRM,
                                        tools.apply_diff, model=ApplyDiff))
    action = ActionRequest("fixture.patch", {"path": "main.py", "old_content": "old", "new_content": "new",
                           "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return assistant, tools, path, action


def test_patch_cancelled_during_final_resolve_never_publishes(tmp_path, monkeypatch):
    assistant, tools, path, action = patch_fixture(tmp_path)
    token = CancellationToken()
    resolve = tools._resolve_in_workspace
    calls = []
    def cancelling_resolve(value):
        calls.append(value)
        if len(calls) == 2:
            token.cancel()
        return resolve(value)
    monkeypatch.setattr(tools, "_resolve_in_workspace", cancelling_resolve)
    try:
        result = assistant.registry.execute(action, lambda *_: True, token)
        assert not result.success
        assert result.error == "cancelled"
        assert path.read_bytes() == b"print('old')\r\n"
        assert not list(path.parent.glob(".aeris-patch-*"))
    finally:
        assistant.close()


def test_controller_preserves_committed_effect_when_next_step_is_cancelled(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    token = CancellationToken()
    def effect(_, token=None):
        token.cancel()
        return ActionResult(False, "Artifact retained after Stop.",
                            {"path": "fixture.txt", "published": True}, "cancelled_after_publication")
    assistant.registry.register(ToolSpec("fixture.effect", "effect", PermissionLevel.AUTO, effect))
    monkeypatch.setattr(assistant.router, "route", lambda _: PlannedResponse(actions=[
        ActionRequest("fixture.effect"), ActionRequest("system.status")]))
    try:
        turn = assistant.handle("fixture task", token=token)
        assert turn.results[0].data["published"]
        assert "fixture.txt" in turn.reply
    finally:
        assistant.close()


def test_actual_json_region_reaches_registry_with_strict_integers(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    seen = []
    def inspect(args):
        seen.append(args)
        return ActionResult(True, "fixture")
    assistant.registry.register(ToolSpec("fixture.inspect", "inspect", PermissionLevel.SESSION,
                                        inspect, model=InspectScreen))
    try:
        payload = json.loads('{"question":"fixture","region":[0,0,100,100]}')
        result = assistant.registry.execute(ActionRequest("fixture.inspect", payload), lambda *_: True)
        assert result.success
        assert seen == [payload]
        for bad in ([0, 0, True, 100], [0, 0, 100.0, 100], [0, 0, 0, 100], [1, 2, 3]):
            result = assistant.registry.execute(ActionRequest("fixture.inspect", {"question": "fixture", "region": bad}),
                                                lambda *_: pytest.fail("Invalid scope prompted"))
            assert result.error == "invalid_arguments"
    finally:
        assistant.close()


def test_cancellation_between_steps_retains_success_receipt(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    token = CancellationToken()
    def effect(_, token=None):
        token.cancel()
        return ActionResult(True, "Created fixture artifact.", {"path": "fixture.txt", "published": True})
    assistant.registry.register(ToolSpec("fixture.effect", "effect", PermissionLevel.AUTO, effect))
    monkeypatch.setattr(assistant.router, "route", lambda _: PlannedResponse(actions=[
        ActionRequest("fixture.effect"), ActionRequest("system.status")]))
    try:
        turn = assistant.handle("fixture task", token=token)
        assert len(turn.results) == 1 and turn.results[0].success
        assert "fixture.txt" in turn.reply and turn.status == "cancelled"
        assert not turn.success
    finally:
        assistant.close()


def test_keyring_failure_leaves_local_text_available(tmp_path, monkeypatch):
    from aeris.config import AerisConfig
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "FIXTURE_DO_NOT_USE")
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    def unavailable(_):
        raise RuntimeError("FIXTURE_PRIVATE_BACKEND_BODY")
    monkeypatch.setattr("aeris.secrets.read_key", unavailable)
    config = AerisConfig.load()
    assert config.recovery_message and "FIXTURE_PRIVATE" not in config.recovery_message
    assert not config.ai_enabled and not config.hands_free and config.dry_run
    assert config.gemini_api_key is None
    assistant = AerisAssistant(config)
    try:
        assert assistant.handle("help").success
    finally:
        assistant.close()


@pytest.mark.parametrize("name,value", [
    ("AERIS_DRY_RUN", "maybe"), ("AERIS_HANDS_FREE", "surprise"),
    ("AERIS_VOICE_SECONDS", "many"), ("AERIS_MAX_DOWNLOAD_MB", "-1"),
    ("AERIS_VOICE_DEVICE", "invalid"),
])
def test_malformed_environment_recovers_without_live_mode(tmp_path, monkeypatch, name, value):
    from aeris.config import AerisConfig
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    monkeypatch.setattr("aeris.secrets.read_key", lambda _: None)
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(name, value)
    config = AerisConfig.load()
    assert config.recovery_message
    assert config.dry_run and not config.ai_enabled and not config.hands_free
    assert not config.allowed_paths


def test_cli_distinguishes_planner_failure_from_reply_only(tmp_path, monkeypatch, capsys):
    from aeris import cli
    assistant = AerisAssistant(make_config(tmp_path))
    monkeypatch.setattr(cli, "_assistant_from_args", lambda _: assistant)
    class BrokenPlanner:
        def plan(self, *_):
            raise RuntimeError("fixture")
    assistant._ollama = BrokenPlanner()
    try:
        assert cli.main(["--once", "fixture unknown command"]) == 1
        assert cli.main(["--once", "help"]) == 0
    finally:
        assistant.close()


def test_private_reply_only_request_is_not_persisted(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    try:
        turn = assistant.handle("/private help")
        assert turn.reply and turn.success
        assert assistant.memory.inspect() == []
    finally:
        assistant.close()


def test_settings_save_failure_restores_previous_credential(tmp_path, monkeypatch):
    config = make_config(tmp_path).with_overrides(gemini_api_key="FIXTURE_NEW_KEY")
    values = ["FIXTURE_OLD_KEY"]
    monkeypatch.setattr("aeris.secrets.read_key", lambda _: values[0])
    monkeypatch.setattr("aeris.secrets.write_key", lambda _, key: values.__setitem__(0, key))
    def disk_failure(*_):
        raise OSError("fixture disk failure")
    monkeypatch.setattr("aeris.config._atomic_settings", disk_failure)
    with pytest.raises(OSError):
        config.save()
    assert values == ["FIXTURE_OLD_KEY"]


def test_patch_cancelled_after_replace_reports_retained_bytes(tmp_path, monkeypatch):
    import os
    assistant, _tools, path, action = patch_fixture(tmp_path)
    token = CancellationToken()
    replace = os.replace
    def publishing(source, destination):
        replace(source, destination)
        token.cancel()
    monkeypatch.setattr("aeris.tools.coding.os.replace", publishing)
    try:
        result = assistant.registry.execute(action, lambda *_: True, token)
        assert result.error == "cancelled_after_publication" and result.data["published"]
        assert path.read_bytes() == b"print('new')\r\n"
    finally:
        assistant.close()


def test_payload_limit_rejects_before_permission_or_handler(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    assistant.registry.register(ToolSpec("fixture.inspect", "inspect", PermissionLevel.SESSION,
                                        lambda _: pytest.fail("Oversized payload executed"), model=InspectScreen))
    try:
        result = assistant.registry.execute(ActionRequest("fixture.inspect", {"question": "x" * 300_000}),
                                             lambda *_: pytest.fail("Oversized payload prompted"))
        assert result.error == "invalid_arguments"
    finally:
        assistant.close()
