from types import SimpleNamespace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.integrations.gemini import GeminiPlanner
from aeris.integrations.ollama import OllamaPlanner


class ClosingProvider:
    def __init__(self, failures=0, *, returns_false=False):
        self.failures = failures
        self.returns_false = returns_false
        self.close_calls = 0

    def close(self):
        self.close_calls += 1
        if self.close_calls <= self.failures:
            if self.returns_false:
                return False
            raise RuntimeError("fixture private provider body")
        return True


def test_retired_provider_cleanup_remains_owned_for_close_retry(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path))
    old = ClosingProvider(failures=1)
    assistant._gemini = old
    monkeypatch.setattr(type(assistant.config), "save", lambda _: None)
    assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    assert old.close_calls == 1
    assert assistant.close()
    assert old.close_calls == 2
    assert assistant.close()
    assert old.close_calls == 2
    assert "fixture private provider body" not in assistant.config.audit_log.read_text()


def test_ollama_is_retired_and_false_cleanup_is_retryable(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path))
    old = ClosingProvider(failures=1, returns_false=True)
    assistant._ollama = old
    monkeypatch.setattr(type(assistant.config), "save", lambda _: None)
    assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    assert old.close_calls == 1
    assert assistant.close()
    assert old.close_calls == 2


def test_failed_staging_cleanup_is_retained_and_blocks_more_replacements(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path))
    staged = ClosingProvider(failures=2)
    monkeypatch.setattr("aeris.assistant.GeminiPlanner", lambda *_: staged)
    monkeypatch.setattr("aeris.assistant.OllamaPlanner", lambda: ClosingProvider())
    bad_catalog = tmp_path / "broken-catalog.json"
    bad_catalog.write_text("{broken")
    with pytest.raises(ValueError):
        assistant.apply_settings(assistant.config.with_overrides(
            ai_enabled=True, gemini_api_key="FIXTURE_KEY", package_catalog_file=bad_catalog))
    assert staged.close_calls == 1
    previous_registry = assistant.registry
    monkeypatch.setattr(type(assistant.config), "save", lambda _: pytest.fail("Saved before cleanup"))
    with pytest.raises(RuntimeError, match="cleanup"):
        assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    assert assistant.registry is previous_registry and assistant.config.dry_run
    assert assistant.close()
    assert staged.close_calls == 3


def test_active_false_cleanup_does_not_report_success_and_can_retry(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    provider = ClosingProvider(failures=1, returns_false=True)
    assistant._gemini = provider
    assert not assistant.close()
    assert assistant._gemini is provider
    assert assistant.close()
    assert provider.close_calls == 2


def test_gemini_client_false_close_retains_retryable_handle():
    planner = GeminiPlanner.__new__(GeminiPlanner)
    client = ClosingProvider(failures=1, returns_false=True)
    planner.client = client
    assert planner.close() is False
    assert planner.client is client
    assert planner.close() is True
    assert planner.client is None


def test_closed_ollama_does_not_open_another_response(monkeypatch):
    planner = OllamaPlanner()
    monkeypatch.setattr("aeris.integrations.ollama.urllib.request.urlopen",
        lambda *_args, **_kwargs: pytest.fail("Closed provider opened network"))
    assert planner.close()
    with pytest.raises(RuntimeError, match="closed"):
        planner.plan("fixture", [])


def test_ollama_cancel_during_response_read_discards_late_output(monkeypatch):
    from aeris.state import CancellationToken, CancelledError

    token = CancellationToken()

    def read():
        token.cancel()
        return b'{"response":"{\\"reply\\":\\"late\\",\\"actions\\":[]}"}'

    response = SimpleNamespace(read=read)

    class ResponseContext:
        def __enter__(self):
            return response

        def __exit__(self, *_):
            return False

    monkeypatch.setattr("aeris.integrations.ollama.urllib.request.urlopen", lambda *_args, **_kwargs: ResponseContext())
    with pytest.raises(CancelledError):
        OllamaPlanner().plan("fixture", [], token=token)


def test_status_tracks_owner_after_settings_publication_and_recovery(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path))
    monkeypatch.setattr(type(assistant.config), "save", lambda _: None)
    assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
    assistant._enter_settings_recovery("Fixture credential recovery required")
    turn = assistant.handle("status")
    assert turn.results[0].data["dry_run"]
    assert turn.results[0].data["settings_recovery_required"]
    assistant.close()


def test_cloud_fallback_cleanup_error_audit_excludes_provider_body(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))

    class OfflineCloud:
        def plan(self, *_args):
            raise ConnectionError("fixture cloud body")

    class FailedFallback:
        def plan(self, *_args):
            raise RuntimeError("FIXTURE_PRIVATE_PROVIDER_BODY")

    assistant._gemini = OfflineCloud()
    assistant._ollama = FailedFallback()
    turn = assistant.handle("fixture unknown request", lambda *_: True)
    assert not turn.success
    assert "FIXTURE_PRIVATE_PROVIDER_BODY" not in assistant.config.audit_log.read_text()
    assistant.close()


def test_cleanup_requested_inside_approval_does_not_close_active_task(tmp_path):
    from aeris.models import PlannedResponse

    assistant = AerisAssistant(make_config(tmp_path))
    provider = ClosingProvider()
    provider.plan = lambda *_args: PlannedResponse(reply="Fixture plan completed")
    assistant._gemini = provider
    cleanup_results = []

    def approval(*_args):
        cleanup_results.append(assistant.close())
        return True

    turn = assistant.handle("fixture unknown request", approval)
    assert cleanup_results == [False]
    assert provider.close_calls == 0 and turn.success
    assert assistant.close() and provider.close_calls == 1


def test_settings_requested_inside_approval_does_not_replace_active_task(tmp_path, monkeypatch):
    from aeris.models import PlannedResponse

    assistant = AerisAssistant(make_config(tmp_path))
    provider = ClosingProvider()
    provider.plan = lambda *_args: PlannedResponse(reply="Fixture plan completed")
    assistant._gemini = provider
    monkeypatch.setattr(type(assistant.config), "save", lambda _: None)

    def approval(*_args):
        with pytest.raises(RuntimeError, match="busy"):
            assistant.apply_settings(assistant.config.with_overrides(dry_run=False))
        return True

    turn = assistant.handle("fixture unknown request", approval)
    assert turn.success and assistant.config.dry_run and provider.close_calls == 0
    assistant.close()
