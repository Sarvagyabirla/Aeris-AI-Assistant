import json
from types import SimpleNamespace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.integrations.gemini import GeminiPlanner
from aeris.models import ActionRequest, ActionResult, PermissionLevel
from aeris.registry import ToolSpec
from aeris.schemas import SetVolume


def test_actual_gemini_serialization_excludes_private_history(tmp_path):
    pytest.importorskip("google.genai", reason="Cloud adapter serialization fixture requires the AI extra")
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.memory.add("user", "LOCAL_UNIQUE_MARKER", "LOCAL_ONLY")
    assistant.memory.add("user", "SENSITIVE_UNIQUE_MARKER", "SENSITIVE")
    assistant.memory.add("user", "APPROVED_SHAREABLE_MARKER", "SHAREABLE")
    outbound = []
    planner = GeminiPlanner.__new__(GeminiPlanner)
    planner.model = "fixture"
    def generate(**payload):
        outbound.append(json.dumps(payload, default=str))
        return SimpleNamespace(text='{"reply":"fixture response","actions":[]}')
    planner.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    assistant._gemini = planner
    assistant.handle("EXPLICIT_REQUEST_MARKER", lambda *_: True)
    assert len(outbound) == 1
    assert "LOCAL_UNIQUE_MARKER" not in outbound[0]
    assert "SENSITIVE_UNIQUE_MARKER" not in outbound[0]
    assert "APPROVED_SHAREABLE_MARKER" in outbound[0]
    assert "EXPLICIT_REQUEST_MARKER" in outbound[0]


def test_approval_argument_mutation_cannot_change_execution(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    effects = []
    assistant.registry.register(ToolSpec("fixture.volume", "fixture", PermissionLevel.CONFIRM,
        lambda args: effects.append(args) or ActionResult(True, "fixture"), model=SetVolume))
    def approval(request, *_):
        request.arguments["level"] = 99
        return True
    result = assistant.registry.execute(ActionRequest("fixture.volume", {"level": 35}), approval)
    assert result.error == "approval_changed"
    assert effects == []