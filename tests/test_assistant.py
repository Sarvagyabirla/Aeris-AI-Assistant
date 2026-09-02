import socket
from pathlib import Path

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig


def make_config(tmp_path: Path, dry_run: bool = True) -> AerisConfig:
    return AerisConfig(
        data_dir=tmp_path / "data",
        allowed_paths=(tmp_path,),
        dry_run=dry_run,
        ai_enabled=False,
        gemini_api_key=None,
        app_catalog_file=tmp_path / "missing-apps.json",
    )


def test_assistant_runs_safe_command_in_dry_run(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    turn = assistant.handle("open chrome")
    assert turn.results[0].success
    assert turn.results[0].dry_run


def test_assistant_denies_sensitive_command_without_approval_ui(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    path = tmp_path / "notes.txt"
    path.write_text("private", encoding="utf-8")
    turn = assistant.handle(f"read file {path}")
    assert not turn.results[0].success
    assert turn.results[0].error == "permission_denied"


def test_assistant_kill_switch_blocks_later_action(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.handle("stop Aeris")
    turn = assistant.handle("open chrome")
    assert turn.results[0].error == "kill_switch"
    resumed = assistant.handle("resume Aeris")
    assert resumed.results[0].success


def test_unknown_command_without_ai_has_helpful_reply(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    turn = assistant.handle("do something not registered")
    assert "do not know that command" in turn.reply


def test_sensitive_command_text_is_not_stored(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.handle(
        "send email to secret@example.com subject Private message Hidden body",
        lambda *_: False,
    )
    messages = assistant.memory.recent()
    assert messages[0]["content"] == "[sensitive command omitted]"
    assert "Hidden body" not in messages[0]["content"]
    assert messages[1]["content"] == "[sensitive result omitted]"


def test_network_failure_becomes_offline_message(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))

    class OfflinePlanner:
        def plan(self, *_args, **_kwargs):
            raise socket.gaierror(11001, "getaddrinfo failed")

    assistant._gemini = OfflinePlanner()
    turn = assistant.handle("an online-only request")
    assert "Internet is unavailable" in turn.reply
    assert "getaddrinfo" not in turn.reply


def test_screen_and_coding_commands_use_registered_tools_in_dry_run(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    screen = assistant.handle("look at my screen and explain this error", lambda *_: True)
    coding = assistant.handle("write Python code for a calculator", lambda *_: True)
    assert screen.results[0].success and screen.results[0].dry_run
    assert coding.results[0].success and coding.results[0].dry_run
    assert "vision.inspect_screen" in screen.results[0].message
    assert "coding.create_project" in coding.results[0].message
