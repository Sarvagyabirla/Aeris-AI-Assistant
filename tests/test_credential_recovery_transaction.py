import json

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig
from aeris.models import ActionRequest, ActionResult, PermissionLevel
from aeris.registry import ToolSpec


def credential_fixture(monkeypatch, config):
    values = {"key": "FIXTURE_OLD_SECRET"}
    monkeypatch.setattr("aeris.secrets.read_key", lambda _: values["key"])
    monkeypatch.setattr("aeris.secrets.write_key", lambda _, key: values.update(key=key))
    monkeypatch.setattr("aeris.config._load_dotenv", lambda: None)
    monkeypatch.setenv("AERIS_DATA_DIR", str(config.data_dir))
    config.with_overrides(gemini_api_key=values["key"]).save()
    return values


def fail_settings_and_rollback(monkeypatch, values):
    from aeris.config import _atomic_settings

    def write_key(_path, key):
        if key == "FIXTURE_OLD_SECRET":
            raise RuntimeError("fixture backend body")
        values["key"] = key

    def atomic(path, data):
        if path.name == "settings.json":
            raise OSError("fixture disk body")
        return _atomic_settings(path, data)

    monkeypatch.setattr("aeris.secrets.write_key", write_key)
    monkeypatch.setattr("aeris.config._atomic_settings", atomic)


def test_failed_credential_rollback_has_durable_safe_restart(tmp_path, monkeypatch):
    config = make_config(tmp_path, dry_run=False)
    values = credential_fixture(monkeypatch, config)
    fail_settings_and_rollback(monkeypatch, values)
    with pytest.raises(RuntimeError):
        config.with_overrides(gemini_api_key="FIXTURE_NEW_SECRET").save()
    assert values["key"] == "FIXTURE_NEW_SECRET"
    marker = config.data_dir / "credential-recovery.json"
    assert marker.is_file(), "Rollback failure needs durable recovery state"
    assert "SECRET" not in marker.read_text() and "backend body" not in marker.read_text()
    monkeypatch.setenv("GEMINI_API_KEY", "FIXTURE_ENV_SECRET")
    monkeypatch.setattr("aeris.secrets.read_key", lambda _: pytest.fail("Ambiguous credential used on restart"))
    loaded = AerisConfig.load()
    assert loaded.dry_run and not loaded.ai_enabled and not loaded.hands_free
    assert loaded.gemini_api_key is None and "credential" in loaded.recovery_message.lower()


def test_failed_rollback_transitions_running_controller_to_simulation(tmp_path, monkeypatch):
    config = make_config(tmp_path, dry_run=False)
    values = credential_fixture(monkeypatch, config)
    assistant = AerisAssistant(config)
    fail_settings_and_rollback(monkeypatch, values)
    effects = []
    assistant.registry.register(ToolSpec("fixture.effect", "fixture", PermissionLevel.AUTO,
        lambda _: effects.append(True) or ActionResult(True, "effect")))
    with pytest.raises(RuntimeError):
        assistant.apply_settings(config.with_overrides(gemini_api_key="FIXTURE_NEW_SECRET"))
    assert assistant.registry.dry_run and assistant.config.dry_run
    assert not assistant.config.ai_enabled and not assistant.config.hands_free
    assert assistant.config.gemini_api_key is None and assistant.config.recovery_message
    assert assistant.registry.execute(ActionRequest("fixture.effect")).dry_run
    assert effects == []
    assistant.close()


def test_successful_explicit_retry_clears_recovery_without_secret_files(tmp_path, monkeypatch):
    config = make_config(tmp_path, dry_run=False)
    values = credential_fixture(monkeypatch, config)
    config.data_dir.joinpath("credential-recovery.json").write_text('{"version":1}')
    recovered = AerisConfig.load()
    assert recovered.gemini_api_key is None and recovered.dry_run
    assistant = AerisAssistant(recovered)
    assistant.apply_settings(recovered.with_overrides(gemini_api_key="FIXTURE_REPAIRED_SECRET", dry_run=False))
    assert values["key"] == "FIXTURE_REPAIRED_SECRET"
    assert not config.data_dir.joinpath("credential-recovery.json").exists()
    assert not assistant.config.recovery_message
    settings = json.loads(config.data_dir.joinpath("settings.json").read_text())
    assert "gemini_api_key" not in settings and "FIXTURE_REPAIRED_SECRET" not in json.dumps(settings)
    assert AerisConfig.load().gemini_api_key == "FIXTURE_REPAIRED_SECRET"
    assistant.close()


def test_failed_key_write_after_mutation_rolls_back_before_clearing_journal(tmp_path, monkeypatch):
    config = make_config(tmp_path, dry_run=False)
    values = credential_fixture(monkeypatch, config)
    original = config.data_dir.joinpath("settings.json").read_bytes()

    def write_key(_path, key):
        values["key"] = key
        if key == "FIXTURE_NEW_SECRET":
            raise OSError("fixture partially completed backend write")

    monkeypatch.setattr("aeris.secrets.write_key", write_key)
    with pytest.raises(OSError):
        config.with_overrides(gemini_api_key="FIXTURE_NEW_SECRET").save()
    assert values["key"] == "FIXTURE_OLD_SECRET"
    assert config.data_dir.joinpath("settings.json").read_bytes() == original
    assert not config.data_dir.joinpath("credential-recovery.json").exists()


def test_failed_explicit_retry_does_not_clear_preexisting_recovery(tmp_path, monkeypatch):
    config = make_config(tmp_path, dry_run=False)
    values = credential_fixture(monkeypatch, config)
    marker = config.data_dir / "credential-recovery.json"
    marker.write_text('{"version":1}')

    def write_key(_path, key):
        values["key"] = key
        if key == "FIXTURE_RETRY_SECRET":
            raise OSError("fixture partial retry")

    monkeypatch.setattr("aeris.secrets.write_key", write_key)
    with pytest.raises(RuntimeError, match="recovery"):
        config.with_overrides(gemini_api_key="FIXTURE_RETRY_SECRET").save()
    assert marker.exists()
    assert AerisConfig.load().gemini_api_key is None


def test_post_publication_journal_cleanup_failure_remains_recoverable(tmp_path, monkeypatch):
    from pathlib import Path

    config = make_config(tmp_path, dry_run=False)
    credential_fixture(monkeypatch, config)
    unlink = Path.unlink

    def failed_unlink(path, *args, **kwargs):
        if path.name == "credential-recovery.json":
            raise OSError("fixture sharing violation")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failed_unlink)
    with pytest.raises(RuntimeError, match="recovery"):
        config.with_overrides(gemini_api_key="FIXTURE_NEW_SECRET").save()
    assert config.data_dir.joinpath("credential-recovery.json").exists()
    assert AerisConfig.load().gemini_api_key is None
