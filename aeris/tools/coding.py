from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

from ..models import ActionResult
from .filesystem import PathGuard

_ALLOWED_SUFFIXES = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_ALLOWED_SPECIAL_NAMES = {".env.example", ".gitignore", "dockerfile", "license", "makefile"}
_BLOCKED_CODING_INTENT = re.compile(
    r"\b(keylogger|ransomware|credential stealer|password stealer|token grabber|reverse shell|"
    r"disable (?:windows )?defender|bypass uac|browser cookie stealer|spyware|persistence malware)\b",
    re.I,
)


class CodingTools:
    """Generate new code projects without executing them or overwriting existing work."""

    def __init__(
        self,
        allowed_roots: tuple[Path, ...],
        workspace: Path,
        api_key: str | None,
        model: str,
    ):
        self.guard = PathGuard(allowed_roots)
        self.workspace = workspace.expanduser().resolve()
        self.api_key = api_key
        self.model = model

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return (slug or "aeris-project")[:60]

    @staticmethod
    def _extract_json(value: str) -> dict[str, Any]:
        cleaned = value.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.I | re.DOTALL)
        if fenced:
            cleaned = fenced.group(1)
        payload = json.loads(cleaned)
        if not isinstance(payload, dict):
            raise ValueError("Code planner must return one JSON object.")
        return payload

    def _ask_model(self, request: str, repair_context: str = "") -> dict[str, Any]:
        from google import genai
        from google.genai import types

        prompt = f"""
You are the coding engine inside Aeris, a permission-first Windows desktop assistant.
Create a clean, complete, beginner-readable project for this request:
{request}

Return ONLY JSON with this shape:
{{
  "project_name": "short-kebab-case-name",
  "summary": "one short sentence",
  "run_instructions": ["safe manual step"],
  "files": [{{"path": "relative/path.ext", "content": "complete file content"}}]
}}

Rules:
- Produce no more than 20 text files and keep the project focused.
- Every path must be relative. Never use .., absolute paths, drive letters, or user folders.
- Never include secrets, real credentials, destructive commands, malware, surveillance, or security bypasses.
- Do not create PowerShell, batch, registry, executable, or binary files.
- Do not claim the code was executed. Aeris validates syntax but does not run generated code.
- Include README.md, complete source, and dependency metadata only when actually needed.
- Prefer Python for AI/ML or unspecified requests. Use simple architecture and helpful comments.
{repair_context}
""".strip()
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
        )
        return self._extract_json(response.text or "")

    @staticmethod
    def _relative_path(value: object) -> PurePosixPath:
        raw = str(value).strip().replace("\\", "/")
        path = PurePosixPath(raw)
        if not raw or path.is_absolute() or ".." in path.parts or ":" in raw or "\0" in raw:
            raise ValueError(f"Unsafe generated path: {raw!r}")
        if any(part.startswith(".") and part not in {".env.example", ".gitignore"} for part in path.parts):
            raise ValueError(f"Hidden generated path is not allowed: {raw!r}")
        name = path.name.lower()
        if path.suffix.lower() not in _ALLOWED_SUFFIXES and name not in _ALLOWED_SPECIAL_NAMES:
            raise ValueError(f"Generated file type is not allowed: {raw!r}")
        return path

    def _validate_plan(self, payload: dict[str, Any]) -> tuple[list[tuple[PurePosixPath, str]], list[str]]:
        raw_files = payload.get("files")
        if not isinstance(raw_files, list) or not 1 <= len(raw_files) <= 20:
            raise ValueError("The generated project must contain between 1 and 20 files.")
        files: list[tuple[PurePosixPath, str]] = []
        errors: list[str] = []
        seen: set[str] = set()
        total_bytes = 0
        for item in raw_files:
            if not isinstance(item, dict):
                raise ValueError("Each generated file must be an object.")
            path = self._relative_path(item.get("path", ""))
            key = str(path).lower()
            if key in seen:
                raise ValueError(f"Duplicate generated path: {path}")
            seen.add(key)
            content = str(item.get("content", ""))
            size = len(content.encode("utf-8"))
            total_bytes += size
            if size > 250_000 or total_bytes > 1_000_000:
                raise ValueError("The generated project exceeded the safe text-size limit.")
            try:
                if path.suffix.lower() == ".py":
                    compile(content, str(path), "exec")
                elif path.suffix.lower() == ".json":
                    json.loads(content)
                elif path.suffix.lower() == ".toml":
                    tomllib.loads(content)
            except (SyntaxError, ValueError, tomllib.TOMLDecodeError) as exc:
                errors.append(f"{path}: {exc}")
            files.append((path, content))
        return files, errors

    def _destination(self, project_name: str) -> Path:
        workspace = self.guard.resolve(self.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        base = workspace / self._slug(project_name)
        candidate = self.guard.resolve(base)
        if not candidate.exists():
            return candidate
        for index in range(2, 10_000):
            candidate = self.guard.resolve(workspace / f"{base.name}-{index}")
            if not candidate.exists():
                return candidate
        raise FileExistsError("Could not choose a new project folder.")

    @staticmethod
    def _open_project(path: Path) -> str:
        if os.name != "nt":
            return "not_opened"
        code = shutil.which("code.cmd") or shutil.which("code.exe") or shutil.which("code")
        try:
            if code:
                subprocess.Popen(
                    [code, str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
                return "vscode"
            os.startfile(str(path))  # type: ignore[attr-defined]
            return "folder"
        except OSError:
            return "not_opened"

    def create_project(self, arguments: dict[str, object]) -> ActionResult:
        request = str(arguments["prompt"]).strip()
        if not request or len(request) > 8_000:
            return ActionResult(False, "The coding request is empty or too long.", error="invalid_prompt")
        if _BLOCKED_CODING_INTENT.search(request):
            return ActionResult(
                False,
                "Aeris will not create credential theft, surveillance, malware, persistence, or security-bypass code.",
                error="unsafe_coding_request",
            )
        if not self.api_key:
            return ActionResult(
                False,
                "Code generation needs GEMINI_API_KEY. Offline computer controls still work.",
                error="ai_not_configured",
            )
        requested_name = str(arguments.get("project_name", "")).strip()
        staging: Path | None = None

        try:
            payload = self._ask_model(request)
            files, validation_errors = self._validate_plan(payload)
            if validation_errors:
                repair = (
                    "The first draft had these validation errors. Return the entire corrected project JSON:\n- "
                    + "\n- ".join(validation_errors[:10])
                )
                payload = self._ask_model(request, repair)
                files, validation_errors = self._validate_plan(payload)
            if validation_errors:
                return ActionResult(
                    False,
                    "The generated code still had syntax errors, so Aeris did not write it.",
                    data={"validation_errors": validation_errors},
                    error="code_validation_failed",
                )
            project_name = requested_name or str(payload.get("project_name", "")) or request[:60]
            destination = self._destination(project_name)
            staging = Path(tempfile.mkdtemp(prefix=".aeris-building-", dir=destination.parent))
            for relative, content in files:
                target = staging.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            staging.replace(destination)
            staging = None
        except Exception as exc:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            return ActionResult(
                False,
                f"Aeris could not create the project safely: {exc}",
                error="code_generation_failed",
            )

        opened = self._open_project(destination)
        instructions = payload.get("run_instructions", [])
        if not isinstance(instructions, list):
            instructions = []
        return ActionResult(
            True,
            f"Created {destination.name} with {len(files)} validated files. Generated code was not executed.",
            data={
                "project_path": str(destination),
                "files": [str(path) for path, _ in files],
                "summary": str(payload.get("summary", "")),
                "run_instructions": [str(item) for item in instructions[:10]],
                "opened_with": opened,
            },
        )
