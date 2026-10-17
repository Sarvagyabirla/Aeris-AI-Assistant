"""Shared bounded parsing and tool selection for both model adapters."""
import json

from ..models import ActionRequest, PlannedResponse
from ..tasks import TaskPlan

KEYWORDS = {
    "desktop": ("open", "close", "volume", "brightness", "play", "pause", "type", "screenshot", "clipboard", "window"),
    "browser": ("page", "browse", "search", "youtube", "google", "browser", "web", "navigate", "extract", "click", "fill"),
    "files": ("file", "folder", "note", "read", "write", "copy", "move", "delete", "create", "list", "find"),
    "packages": ("install", "uninstall", "update", "app", "software", "winget"),
    "email": ("email", "mail", "gmail", "send", "message", "brief"),
    "downloads": ("download", "get"),
    "vision": ("look", "screen", "see", "explain", "window"),
    "calendar": ("calendar", "event", "meeting", "schedule", "appointment", "brief"),
    "coding": ("code", "program", "project", "build", "workspace", "patch", "bug"),
}


def select_tools(text, definitions):
    categories = {key for key, words in KEYWORDS.items() if any(word in text.lower() for word in words)}
    if not categories:
        return definitions
    return [item for item in definitions if item["name"].split(".")[0] in categories | {"system"}]


def parse_plan(payload, allowed_names, source_text):
    if len(json.dumps(payload, allow_nan=False).encode("utf-8")) > 262_144:
        raise ValueError("Planner payload exceeds 256 KiB")
    if not isinstance(payload, dict) or set(payload) - {"reply", "actions", "steps"}:
        raise ValueError("Planner must return a reply/actions object")
    if 'steps' in payload:
        if 'actions' in payload or not isinstance(payload.get('reply', ''), str):
            raise ValueError('Use either steps or actions, with a text reply')
        if payload['steps'] == []:
            return PlannedResponse(reply=payload.get('reply', '').strip())
        plan = TaskPlan.model_validate({'steps': payload['steps']})
        if any(step.tool not in allowed_names for step in plan.steps):
            raise ValueError('Unknown task tool')
        return PlannedResponse(reply=payload.get('reply', '').strip(), steps=plan.steps)
    actions = payload.get("actions", [])
    if not isinstance(actions, list) or len(actions) > 5:
        raise ValueError("Planner must return at most five actions")
    requests = []
    for item in actions:
        if not isinstance(item, dict) or set(item) != {"tool", "arguments"}:
            raise ValueError("Malformed planner action")
        if item["tool"] not in allowed_names or not isinstance(item["arguments"], dict):
            raise ValueError("Unknown tool or invalid arguments")
        requests.append(ActionRequest(item["tool"], item["arguments"], source_text))
    reply = payload.get("reply", "")
    if not isinstance(reply, str):
        raise ValueError("Planner reply must be text")
    return PlannedResponse(reply=reply.strip(), actions=requests)
