from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_KEY = re.compile(
    r"(api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|^body$|^content$|^prompt$|^text$)",
    re.I,
)
_SECRET_VALUE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+\-/=]+")
_SECRET_QUERY_KEY = re.compile(r"(token|signature|sig|key|secret|password|credential|auth)", re.I)

# Basic PII filters
_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.query:
        return value
    query = [
        (key, "[REDACTED]" if _SECRET_QUERY_KEY.search(key) else item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else redact(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        val = _redact_url(_SECRET_VALUE.sub(r"\1[REDACTED]", value))
        val = _EMAIL_REGEX.sub("[EMAIL REDACTED]", val)
        val = _PHONE_REGEX.sub("[PHONE REDACTED]", val)
        val = _SSN_REGEX.sub("[SSN REDACTED]", val)
        val = _CC_REGEX.sub("[CC REDACTED]", val)
        return val
    return value


class AuditLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, event: str, **details: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": redact(details),
        }
        with self._lock:
            # Rotate if file > 5MB
            if self.path.exists() and self.path.stat().st_size > 5 * 1024 * 1024:
                backup = self.path.with_suffix(".jsonl.bak")
                if backup.exists():
                    backup.unlink()
                self.path.rename(backup)
                
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
