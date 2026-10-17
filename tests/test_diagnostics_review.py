import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.core.process_runner import ProcessOutcome
from aeris.state import CancellationToken


def test_health_shortcut_is_deterministic(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    try:
        turn = assistant.handle("Check system health and status")
        assert len(turn.results) == 2
        assert all(result.success for result in turn.results)
        assert "system.health" in turn.results[0].message
    finally:
        assistant.close()


def test_network_shortcut_denial_and_cancellation_do_not_probe(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    monkeypatch.setattr("aeris.tools.system.run_owned", lambda *_a, **_k: pytest.fail("Probe ran without consent"), raising=False)
    try:
        denied = assistant.handle("Test network connectivity", lambda *_: False)
        assert denied.results and denied.results[0].error == "permission_denied"
        token = CancellationToken()
        def cancel(*_):
            token.cancel()
            return True
        turn = assistant.handle("Test network connectivity", cancel, token)
        assert turn.status == "cancelled"
    finally:
        assistant.close()


def test_network_shortcut_uses_owned_bounded_probe_and_truthful_result(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    calls, previews = [], []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return ProcessOutcome(1, "PRIVATE_FIXTURE_NETWORK_OUTPUT")
    monkeypatch.setattr("aeris.tools.system.run_owned", run, raising=False)
    monkeypatch.setattr("aeris.tools.system.shutil.which", lambda _: "ping.exe")
    def approve(_request, _level, preview):
        previews.append(preview)
        return True
    try:
        turn = assistant.handle("Test network connectivity", approve)
        assert "www.microsoft.com" in previews[0]
        assert len(calls) == 1 and calls[0][1]["timeout"] <= 5
        assert not turn.success and "PRIVATE_FIXTURE" not in turn.reply
        assert "not prove" in turn.reply
    finally:
        assistant.close()
