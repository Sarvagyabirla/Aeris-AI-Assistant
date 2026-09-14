import json
import logging
import urllib.request
import urllib.error
from typing import Any

from ..models import ActionRequest, PlannedResponse


class OllamaPlanner:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.logger = logging.getLogger("aeris.ollama")
        self.endpoint = "http://localhost:11434/api/generate"

    def _select_relevant_tools(self, user_text: str, tool_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Fast keyword-based pre-filtering to reduce token count and latency
        text = user_text.lower()
        selected = []
        for tool in tool_definitions:
            name = tool["name"].lower()
            if name.startswith("system."):
                selected.append(tool)
                continue
                
            if name.startswith("desktop.") and any(kw in text for kw in ("open", "close", "volume", "brightness", "play", "pause", "type", "screenshot", "clipboard", "window")):
                selected.append(tool)
            elif name.startswith("browser.") and any(kw in text for kw in ("open", "search", "youtube", "google", "browser", "web")):
                selected.append(tool)
            elif name.startswith("files.") and any(kw in text for kw in ("file", "folder", "note", "read", "write", "copy", "move", "delete", "create", "list", "find")):
                selected.append(tool)
            elif name.startswith("packages.") and any(kw in text for kw in ("install", "uninstall", "update", "app", "software", "winget")):
                selected.append(tool)
            elif name.startswith("email.") and any(kw in text for kw in ("email", "mail", "gmail", "send", "message", "read")):
                selected.append(tool)
            elif name.startswith("downloads.") and any(kw in text for kw in ("download", "get")):
                selected.append(tool)
            elif name.startswith("vision.") and any(kw in text for kw in ("look", "screen", "see", "read", "explain")):
                selected.append(tool)
            elif name.startswith("coding.") and any(kw in text for kw in ("code", "program", "app", "project", "build")):
                selected.append(tool)
                
        if not selected:
            return tool_definitions
        return selected

    def plan(
        self,
        user_text: str,
        tool_definitions: list[dict[str, Any]],
        recent_context: list[dict[str, str]] | None = None,
        token: Any = None,
    ) -> PlannedResponse:
        if token:
            token.raise_if_cancelled()
        allowed_names = {item["name"] for item in tool_definitions}
        relevant_tools = self._select_relevant_tools(user_text, tool_definitions)

        prompt = f"""
You are the offline planning brain for Aeris, a permission-first Windows assistant.

Rules:
- Use only the registered tools listed below.
- Never invent tools or arguments.
- Use at most 5 actions.
- A reply-only answer must use an empty actions array.
- Reply EXACTLY with a JSON object. Do not include markdown code blocks or any other text.
- JSON format:
{{
  "reply": "string",
  "actions": [
    {{ "tool": "tool_name", "arguments": {{ "arg1": "value1" }} }}
  ]
}}

REGISTERED TOOLS:
{json.dumps(relevant_tools, ensure_ascii=False)}

RECENT CONVERSATION:
{json.dumps(recent_context or [], ensure_ascii=False)}

USER REQUEST:
{user_text}
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1
            }
        }

        try:
            if token:
                token.raise_if_cancelled()
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if token:
                    token.raise_if_cancelled()
                result = json.loads(response.read().decode("utf-8"))
                output = json.loads(result.get("response", "{}"))
                
                actions: list[ActionRequest] = []
                raw_actions = output.get("actions", [])
                
                if isinstance(raw_actions, list):
                    for item in raw_actions[:5]:
                        if not isinstance(item, dict):
                            continue
                        name = item.get("tool")
                        arguments = item.get("arguments", {})
                        if name not in allowed_names or not isinstance(arguments, dict):
                            continue
                        actions.append(ActionRequest(tool=name, arguments=arguments, source_text=user_text))
                        
                return PlannedResponse(reply=str(output.get("reply", "")).strip(), actions=actions)
        except Exception as e:
            raise RuntimeError(f"Ollama planning failed: {e}")
