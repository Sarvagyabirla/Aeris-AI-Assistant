import json

from aeris.audit import AuditLogger, redact


def test_nested_secrets_are_redacted():
    payload = redact({"api_key": "secret", "nested": {"access_token": "abc", "safe": "yes"}})
    assert payload["api_key"] == "[REDACTED]"
    assert payload["nested"]["access_token"] == "[REDACTED]"
    assert payload["nested"]["safe"] == "yes"


def test_bearer_token_is_redacted():
    assert "token123" not in redact("Authorization: Bearer token123")


def test_signed_url_query_secrets_are_redacted():
    value = redact("https://example.com/file?token=secret&name=public")
    assert "secret" not in value
    assert "name=public" in value


def test_audit_writes_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    AuditLogger(path).write("test", password="never-store-me")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["event"] == "test"
    assert record["details"]["password"] == "[REDACTED]"
