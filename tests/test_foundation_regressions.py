import sqlite3

import pytest
from pydantic import ValidationError
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.memory import MemoryStore
from aeris.models import ActionRequest, ActionResult, PlannedResponse
from aeris.schemas import SetVolume


def test_legacy_duplicate_history_survives_repeated_startup(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, created_at TEXT, role TEXT, content TEXT)")
        db.executemany("INSERT INTO messages VALUES (?, ?, ?, ?)", [
            (1, "2020-01-01", "user", "status"),
            (2, "2020-01-02", "assistant", "status"),
        ])
    MemoryStore(path)
    store = MemoryStore(path)
    assert [(r["role"], r["created_at"]) for r in store.recent()] == [
        ("user", "2020-01-01"), ("assistant", "2020-01-02")]
    store.add("user", "status")
    assert len(store.recent()) == 3


def test_sensitive_never_persisted_raw(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    store.add("user", "SENSITIVE_UNIQUE_MARKER", "SENSITIVE")
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT content FROM messages").fetchall() == []


def test_cloud_boundary_excludes_local_history(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.memory.add("user", "LOCAL_ONLY_UNIQUE_MARKER")
    payloads = []
    class Planner:
        def plan(self, text, tools, context, token):
            payloads.append(context)
            return PlannedResponse(reply="fixture")
    assistant._gemini = Planner()
    assistant.handle("fixture request", lambda *_: True)
    assert len(payloads) == 1
    assert "LOCAL_ONLY_UNIQUE_MARKER" not in str(payloads)


def test_boolean_volume_rejected():
    with pytest.raises(ValidationError):
        SetVolume(level=True)


def test_required_step_failure_blocks_next_action(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    actions = [ActionRequest("system.status"), ActionRequest("system.status")]
    assistant.router.route = lambda _: PlannedResponse(actions=actions)
    calls = []
    def execute(action, *args, **kwargs):
        calls.append(action)
        return ActionResult(False, "fixture failure")
    assistant.registry.execute = execute
    assistant.handle("fixture")
    assert len(calls) == 1


@pytest.mark.parametrize("tool,data,marker", [
    ("browser.advanced_extract", {"content": "PAGE_MARKER"}, "PAGE_MARKER"),
    ("coding.search_workspace", {"matches": ["file.py: CODE_MARKER"]}, "CODE_MARKER"),
    ("calendar.list_events", {"events": [{"summary": "EVENT_MARKER", "start": "2026-10-12T12:00:00+05:30"}]}, "EVENT_MARKER"),
])
def test_result_details_visible(tool, data, marker):
    assert marker in AerisAssistant._visible_details(ActionRequest(tool), ActionResult(True, "OK", data))