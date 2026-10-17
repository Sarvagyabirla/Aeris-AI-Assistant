import json
import logging
import urllib.error
import urllib.request
from typing import Any

from ..models import PlannedResponse
from ..state import CancelledError
from .planning import parse_plan, select_tools


class OllamaPlanner:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.logger = logging.getLogger("aeris.ollama")
        self.endpoint = "http://localhost:11434/api/generate"
        self._closed = False

    def close(self) -> bool:
        # urllib responses are owned by each request's context manager. There
        # is no pooled transport to close; prevent reuse after retirement.
        self._closed = True
        return True

    def _select_relevant_tools(self, user_text: str, tool_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return select_tools(user_text, tool_definitions)
    def plan(
        self,
        user_text: str,
        tool_definitions: list[dict[str, Any]],
        recent_context: list[dict[str, str]] | None = None,
        token: Any = None,
    ) -> PlannedResponse:
        if self._closed:
            raise RuntimeError("Ollama planner is closed.")
        if token:
            token.raise_if_cancelled()
        allowed_names = {item["name"] for item in tool_definitions}
        relevant_tools = self._select_relevant_tools(user_text, tool_definitions)

        prompt = f"""
You are the offline planning brain for Aeris, a permission-first Windows assistant.

Rules:
- Use only the registered tools listed below.
- Never invent tools or arguments.
- Use at most 5 ordered steps with unique ids and declared earlier dependencies.
- A reply-only answer must use an empty steps array.
- Use a top-level argument {{"$ref":"create.path"}} only after declaring create as a dependency.
- Allowed producer fields: path from files.create_folder/files.write_text/downloads.download/coding.create_project;
  destination or sha256 from files.copy/files.move; url from browser.advanced_navigate.
- Never guess observation-dependent paths, URLs, message ids, selectors or coordinates.
- Reply EXACTLY with a JSON object. Do not include markdown code blocks or any other text.
- JSON format:
{{
  "reply": "string",
  "steps": [
    {{ "id": "first", "tool": "tool_name", "arguments": {{ "arg1": "value1" }}, "depends_on": [] }}
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
                body = response.read()
                if token:
                    token.raise_if_cancelled()
                result = json.loads(body.decode("utf-8"))
                output = json.loads(result.get("response", "{}"))
                
                return parse_plan(output, allowed_names, user_text)
        except CancelledError:
            raise
        except Exception as e:
            raise RuntimeError(f"Ollama planning failed: {e}")
