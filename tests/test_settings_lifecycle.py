import hashlib
import json
import sqlite3
import time
from unittest.mock import MagicMock

import pytest
from test_assistant import make_config

from aeris.activation import extract_addressed_command
from aeris.assistant import AerisAssistant
from aeris.cli import _assistant_from_args, build_parser
from aeris.config import AerisConfig
from aeris.integrations.planning import parse_plan, select_tools
from aeris.integrations.voice import VoiceService
from aeris.models import ActionRequest, ActionResult, PermissionLevel
from aeris.registry import ToolSpec
from aeris.schemas import Download
from aeris.tools.browser_advanced import PlaywrightWorker, allowed_url
from aeris.tools.coding import CodingTools


@pytest.fixture
def credential_store(monkeypatch):
    values = {}
    monkeypatch.setattr("aeris.secrets.read_key", lambda path: values.get(str(path)))
    monkeypatch.setattr("aeris.secrets.write_key", lambda path, key: values.update({str(path): key}))
    return values


def test_saved_settings_secret_removal_and_cli_precedence(tmp_path, monkeypatch, credential_store):
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    config = make_config(tmp_path, dry_run=False).with_overrides(gemini_api_key="FAKE_SECRET", voice_device="auto")
    config.save()
    assert "FAKE_SECRET" not in (config.data_dir / "settings.json").read_text()
    loaded = AerisConfig.load()
    assert loaded.gemini_api_key == "FAKE_SECRET"
    assert loaded.voice_device == "auto"
    parser = build_parser()
    assert not _assistant_from_args(parser.parse_args(["--no-ai"])).registry.dry_run
    assert _assistant_from_args(parser.parse_args(["--no-ai", "--simulate"])).registry.dry_run
    assert not _assistant_from_args(parser.parse_args(["--no-ai", "--live"])).registry.dry_run
    config.with_overrides(gemini_api_key=None).save()
    assert AerisConfig.load().gemini_api_key is None
    assert credential_store[str(config.data_dir)] is None


def test_legacy_secret_migrates_without_plaintext_duplicate(tmp_path, monkeypatch, credential_store):
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"gemini_api_key": "FAKE_LEGACY", "custom": 17}))
    assert AerisConfig.load().gemini_api_key == "FAKE_LEGACY"
    assert json.loads(file.read_text()) == {"custom": 17}


def test_malformed_settings_disable_file_access(tmp_path, monkeypatch, credential_store):
    monkeypatch.setenv("AERIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    (tmp_path / "settings.json").write_text("{broken")
    with pytest.warns(RuntimeWarning):
        config = AerisConfig.load()
    assert config.allowed_paths == ()
    assert config.dry_run
    assistant = AerisAssistant(config.with_overrides(ai_enabled=False))
    assert assistant.handle("status").results[0].success


def test_settings_change_effective_executor(tmp_path, credential_store):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    called = []
    assistant.registry.register(ToolSpec("fixture.effect", "fixture", PermissionLevel.AUTO,
        lambda args: called.append(args) or ActionResult(True, "fixture applied")))
    assert assistant.registry.execute(ActionRequest("fixture.effect")).success
    assert called == [{}]


def test_canonical_url_and_omitted_filename_match_approval(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    previews, executions = [], []
    assistant.registry.register(ToolSpec("fixture.download", "fixture", PermissionLevel.CONFIRM,
        lambda args: executions.append(args) or ActionResult(True, "fixture"), model=Download))
    result = assistant.registry.execute(ActionRequest("fixture.download", {"url": "https://example.com"}),
        lambda request, *_: previews.append(request.arguments) or True)
    assert result.success
    assert previews == executions == [{"url": "https://example.com/"}]


@pytest.mark.parametrize("text,expected", [
    ("Aeris, open Notepad", "open Notepad"), ("Hey Aeris! Chrome kholo", "Chrome kholo"),
    ("aerisms open chrome", None), ("we mentioned aeris today", None), ("Aeris", ""),
])
def test_addressed_activation(text, expected):
    assert extract_addressed_command(text, ("aeris",)) == expected


def test_cancel_before_voice_start_does_not_open_device(monkeypatch):
    voice = VoiceService()
    voice.cancel_recording()
    assert voice.listen_once() == ""


@pytest.mark.parametrize("url,rules,expected", [
    ("https://example.com", ("example.com",), True),
    ("https://notexample.com", ("example.com",), False),
    ("https://child.example.com", ("example.com",), False),
    ("https://child.example.com", ("*.example.com",), True),
    ("https://example.com:444", ("example.com",), False),
    ("http://127.0.0.1:8123", ("http://127.0.0.1:8123",), True),
    ("http://127.0.0.1", ("*",), False),
    ("file:///C:/secret.txt", ("*",), False),
])
def test_browser_host_policy(url, rules, expected):
    assert allowed_url(url, rules) is expected


def test_browser_startup_crash_propagates_without_wait(monkeypatch):
    def crash(self):
        raise RuntimeError("fixture startup crash")
    monkeypatch.setattr(PlaywrightWorker, "_run_browser", crash)
    start = time.monotonic()
    worker = PlaywrightWorker(("example.com",))
    result = worker.execute("extract")
    assert not result.success
    assert result.error == "browser_unavailable"
    assert time.monotonic() - start < 1
    assert worker.close(1)


def test_plan_selection_calendar_and_unrecognized_fallback():
    tools = [{"name": "system.status"}, {"name": "calendar.list_events"}, {"name": "coding.search_workspace"}]
    assert tools[1] in select_tools("upcoming meeting", tools)
    assert select_tools("something unusual", tools) == tools


@pytest.mark.parametrize("payload", [
    {"actions": [{"tool": "unknown", "arguments": {}}]},
    {"actions": [None]}, {"actions": [{"tool": "system.status", "arguments": {}}] * 6},
])
def test_invalid_plans_rejected(payload):
    with pytest.raises(ValueError):
        parse_plan(payload, {"system.status"}, "fixture")


def test_hash_patch_preserves_newlines_and_rejects_stale_ambiguous_empty(tmp_path):
    file = tmp_path / "sample.py"
    tools = CodingTools((tmp_path,), tmp_path, None, "fixture")
    original = b"x = 1\r\nprint(x)\r\n"
    file.write_bytes(original)
    args = {"path": "sample.py", "old_content": "x = 1", "new_content": "x = 2",
        "expected_sha256": hashlib.sha256(original).hexdigest()}
    assert tools.apply_diff(args).success
    assert file.read_bytes() == b"x = 2\r\nprint(x)\r\n"
    assert not tools.apply_diff(args).success
    file.write_bytes(b"same\nsame\n")
    args.update(old_content="same", expected_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    assert not tools.apply_diff(args).success
    args["old_content"] = ""
    assert not tools.apply_diff(args).success


def test_search_symlink_outside_workspace_is_not_read(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("OUTSIDE_MARKER")
    try:
        (workspace / "linked.txt").symlink_to(outside)
    except OSError:
        pytest.skip("Creating Windows symlinks requires Developer Mode or elevated privileges")
    tools = CodingTools((tmp_path,), workspace, None, "fixture")
    assert tools.search_workspace({"query": "OUTSIDE_MARKER"}).data["matches"] == []


def test_sensitive_assistant_request_absent_in_raw_rows(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.handle("send email to fixture@example.com subject Test message SECRET_MARKER", lambda *_: False)
    with sqlite3.connect(assistant.memory.path) as db:
        assert db.execute("SELECT * FROM messages").fetchall() == []


def test_cloud_denial_does_not_call_provider(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant._gemini = MagicMock()
    turn = assistant.handle("private flexible request", lambda *_: False)
    assistant._gemini.plan.assert_not_called()
    assert "not approved" in turn.reply


def test_search_windows_junction_outside_workspace_is_not_read(tmp_path):
    import os
    import subprocess
    if os.name != "nt":
        pytest.skip("Windows junction acceptance requires Windows")
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "fixture.txt").write_text("OUTSIDE_JUNCTION_MARKER")
    junction = workspace / "linked"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        pytest.skip("Windows session does not permit creating a temporary junction")
    try:
        tools = CodingTools((tmp_path,), workspace, None, "fixture")
        assert tools.search_workspace({"query": "OUTSIDE_JUNCTION_MARKER"}).data["matches"] == []
    finally:
        os.rmdir(junction)