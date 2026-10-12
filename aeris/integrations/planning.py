"""Shared bounded parsing and tool selection for both model adapters."""
from ..models import ActionRequest, PlannedResponse

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
    if not isinstance(payload, dict) or set(payload) - {"reply", "actions"}:
        raise ValueError("Planner must return a reply/actions object")
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