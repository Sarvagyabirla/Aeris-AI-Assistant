from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionLevel(str, Enum):
    AUTO = "auto"
    SESSION = "session"
    CONFIRM = "confirm"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ActionRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    source_text: str = ""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"tool": self.tool, "arguments": self.arguments},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def preview(self) -> str:
        if not self.arguments:
            return self.tool
        args = ", ".join(f"{key}={value!r}" for key, value in self.arguments.items())
        return f"{self.tool}({args})"


@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    dry_run: bool = False


@dataclass
class PlannedResponse:
    reply: str = ""
    actions: list[ActionRequest] = field(default_factory=list)


@dataclass
class AssistantTurn:
    input_text: str
    reply: str
    results: list[ActionResult] = field(default_factory=list)
