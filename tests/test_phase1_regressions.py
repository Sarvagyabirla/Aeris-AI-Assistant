import builtins
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.audit import AuditLogger
from aeris.config import AerisConfig
from aeris.integrations.voice import VoiceService, VoiceUnavailableError
from aeris.models import ActionRequest, PermissionLevel
from aeris.permissions import PermissionEngine
from aeris.registry import ToolSpec
from aeris.schemas import CreateProject
from aeris.state import CancellationToken
from aeris.tools.coding import CodingTools


@pytest.mark.parametrize("during_repair", [False, True])
def test_generation_cancelled_by_provider_never_publishes(tmp_path, monkeypatch, during_repair):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    workspace = tmp_path / "projects"
    tools = CodingTools((tmp_path,), workspace, "fake-key", "fixture")
    token = CancellationToken()
    calls = []
    def generate(*args, **kwargs):
        calls.append(True)
        if during_repair and len(calls) == 1:
            return {"files": [{"path": "main.py", "content": "def broken(:"}]}
        token.cancel()
        return {"project_name": "fixture", "files": [{"path": "main.py", "content": "print('fixture')\n"}]}
    monkeypatch.setattr(tools, "_ask_model", generate)
    monkeypatch.setattr(tools, "_open_project", lambda _: pytest.fail("Editor opened after cancellation"))
    assistant.registry.register(ToolSpec("fixture.generate", "cloud project generation", PermissionLevel.CONFIRM,
        tools.create_project, model=CreateProject))
    result = assistant.registry.execute(ActionRequest("fixture.generate", {"prompt": "fixture project"}), lambda *_: True, token)
    assert not result.success
    assert not list(workspace.rglob("main.py"))
    assert not list(workspace.glob(".aeris-building-*"))


def test_session_grant_is_bound_to_region_and_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("aeris.permissions.time.monotonic", lambda: now[0])
    engine = PermissionEngine()
    approvals = []
    def approve(request, *_):
        approvals.append(request.fingerprint())
        return True
    region_a = ActionRequest("vision.inspect_screen", {"region": [0, 0, 100, 100]})
    region_b = ActionRequest("vision.inspect_screen", {"region": [100, 0, 200, 100]})
    assert engine.authorize(region_a, PermissionLevel.SESSION, approve).allowed
    assert engine.authorize(region_a, PermissionLevel.SESSION, approve).allowed
    assert engine.authorize(region_b, PermissionLevel.SESSION, approve).allowed
    now[0] += 3600
    assert engine.authorize(region_b, PermissionLevel.SESSION, approve).allowed
    assert len(approvals) == 3


def test_global_stop_survives_settings_application(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path))
    monkeypatch.setattr("aeris.secrets.write_key", lambda *_: None)
    assistant.permissions.stop()
    assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    assert assistant.permissions.stopped
    assert assistant.handle("open notepad").results[0].error == "kill_switch"


def test_broken_portaudio_import_is_useful_voice_error(monkeypatch):
    original = builtins.__import__
    def importing(name, *args, **kwargs):
        if name == "numpy":
            return SimpleNamespace()  # Import isolation: portable core has no NumPy.
        if name == "sounddevice":
            raise OSError("PortAudio library not found")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", importing)
    with pytest.raises(VoiceUnavailableError, match="PortAudio"):
        VoiceService().listen_once()


def test_audit_default_never_records_arbitrary_messages_paths_or_values(tmp_path):
    log = AuditLogger(tmp_path / "audit.jsonl")
    log.write("tool_finished", request={"tool": "files.read", "request_id": "fixture-id", "arguments": {
        "path": "PRIVATE_PATH_MARKER", "custom": "SECRET_VALUE_MARKER"}},
        message="PRIVATE_RESULT_MARKER", error="PRIVATE_ERROR_MARKER", success=False)
    content = log.path.read_text()
    assert "MARKER" not in content
    record = json.loads(content)
    assert record["details"]["request"]["tool"] == "files.read"


@pytest.mark.parametrize("value", [{"dry_run": "false"}, {"voice_record_seconds": True},
                                  {"allowed_paths": []}, {"voice_device": "invalid"}])
def test_invalid_typed_settings_preserved_and_recover_safe(tmp_path, monkeypatch, value):
    path = tmp_path / "settings.json"
    original = json.dumps(value)
    path.write_text(original)
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    monkeypatch.setattr("aeris.secrets.read_key", lambda _: None)
    with pytest.warns(RuntimeWarning):
        config = AerisConfig.load()
    assert config.dry_run and not config.hands_free and not config.ai_enabled
    assert config.allowed_paths == ()
    assert config.recovery_message
    assert path.read_text() == original


def test_confirmation_invalidated_by_stop_during_prompt():
    engine = PermissionEngine()
    def approve(*_):
        engine.stop()
        engine.resume()
        return True
    assert not engine.authorize(ActionRequest("files.write", {"path": "fixture"}),
                                PermissionLevel.CONFIRM, approve).allowed


def test_cloud_coding_denied_before_model_call(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    called = []
    assistant.registry._tools.pop("coding.create_project")
    assistant.registry.register(ToolSpec("coding.create_project", "fixture", PermissionLevel.CONFIRM,
        lambda _: called.append(True), model=CreateProject))
    result = assistant.registry.execute(ActionRequest("coding.create_project", {"prompt": "fixture"}),
        lambda request, *_: request.tool != "privacy.share_coding")
    assert not result.success and not called


def test_cancellation_during_staging_cleans_files(tmp_path, monkeypatch):
    workspace = tmp_path / "projects"
    tools = CodingTools((tmp_path,), workspace, "fake", "fixture")
    token = CancellationToken()
    monkeypatch.setattr(tools, "_ask_model", lambda *_args, **_kwargs: {"project_name": "fixture", "files": [
        {"path": "main.py", "content": "print('fixture')"}]})
    original = Path.write_text
    def write(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if ".aeris-building-" in str(path):
            token.cancel()
        return result
    monkeypatch.setattr(Path, "write_text", write)
    result = tools.create_project({"prompt": "fixture"}, token)
    assert result.error == "cancelled"
    assert list(workspace.iterdir()) == []


def test_cancellation_after_publication_reports_existing_artifact(tmp_path, monkeypatch):
    tools = CodingTools((tmp_path,), tmp_path / "projects", "fake", "fixture")
    token = CancellationToken()
    monkeypatch.setattr(tools, "_ask_model", lambda *_args, **_kwargs: {"project_name": "fixture", "files": [
        {"path": "main.py", "content": "print('fixture')"}]})
    original = Path.rename
    def publish(path, destination):
        result = original(path, destination)
        token.cancel()
        return result
    monkeypatch.setattr(Path, "rename", publish)
    monkeypatch.setattr(tools, "_open_project", lambda _: pytest.fail("Editor must not open"))
    result = tools.create_project({"prompt": "fixture"}, token)
    assert result.error == "cancelled_after_publication"
    assert (Path(result.data["project_path"]) / "main.py").exists()


def test_expired_deadline_blocks_atomic_publication():
    token = CancellationToken(deadline=time.monotonic() - 1)
    effects = []
    from aeris.state import CancelledError
    with pytest.raises(CancelledError):
        token.commit(lambda: effects.append(True))
    assert not effects
