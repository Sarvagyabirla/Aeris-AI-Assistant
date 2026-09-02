from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..models import ActionResult

_DANGEROUS_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".cpl",
    ".exe",
    ".hta",
    ".jar",
    ".js",
    ".jse",
    ".lnk",
    ".msi",
    ".msp",
    ".ps1",
    ".reg",
    ".scr",
    ".vbe",
    ".vbs",
}
_TEXT_EXTENSIONS = {
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".py",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


class PathGuard:
    def __init__(self, allowed_roots: tuple[Path, ...]):
        if not allowed_roots:
            raise ValueError("At least one allowed path is required.")
        self.allowed_roots = tuple(path.expanduser().resolve() for path in allowed_roots)

    def resolve(self, value: str | Path) -> Path:
        raw = Path(os.path.expandvars(str(value))).expanduser()
        candidate = raw.resolve() if raw.is_absolute() else (self.allowed_roots[0] / raw).resolve()
        if not any(candidate == root or candidate.is_relative_to(root) for root in self.allowed_roots):
            raise PermissionError(f"Path is outside AERIS_ALLOWED_PATHS: {candidate}")
        return candidate


class FilesystemTools:
    def __init__(self, allowed_roots: tuple[Path, ...]):
        self.guard = PathGuard(allowed_roots)

    def list_files(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments.get("path", ".")))
        if not path.exists() or not path.is_dir():
            return ActionResult(False, f"Folder does not exist: {path}", error="folder_not_found")
        limit = max(1, min(int(arguments.get("limit", 50)), 200))
        items = []
        for item in sorted(path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))[
            :limit
        ]:
            items.append({"name": item.name, "type": "folder" if item.is_dir() else "file"})
        return ActionResult(
            True, f"Found {len(items)} items in {path}", data={"path": str(path), "items": items}
        )

    def find_files(self, arguments: dict[str, object]) -> ActionResult:
        query = str(arguments["query"]).strip().lower()
        if not query:
            return ActionResult(False, "File search query cannot be empty.", error="empty_query")
        limit = max(1, min(int(arguments.get("limit", 20)), 100))
        matches: list[str] = []
        for root in self.guard.allowed_roots:
            if not root.exists():
                continue
            try:
                for path in root.rglob("*"):
                    if path.is_file() and query in path.name.lower():
                        matches.append(str(path))
                        if len(matches) >= limit:
                            break
            except (OSError, PermissionError):
                continue
            if len(matches) >= limit:
                break
        return ActionResult(True, f"Found {len(matches)} matching files.", data={"matches": matches})

    def read_text(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        if not path.exists() or not path.is_file():
            return ActionResult(False, f"File does not exist: {path}", error="file_not_found")
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            return ActionResult(
                False, "Only approved text-based file types can be read.", error="unsupported_file_type"
            )
        if path.stat().st_size > 200_000:
            return ActionResult(False, "File is larger than the 200 KB read limit.", error="file_too_large")
        content = path.read_text(encoding="utf-8", errors="replace")
        return ActionResult(True, f"Read {path.name}", data={"path": str(path), "content": content})

    def open_file(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        if not path.exists() or not path.is_file():
            return ActionResult(False, f"File does not exist: {path}", error="file_not_found")
        if path.suffix.lower() in _DANGEROUS_EXTENSIONS:
            return ActionResult(
                False,
                "Executable and script files are blocked in the normal file opener. Use the verified installer command when appropriate.",
                error="dangerous_file_type",
            )
        if os.name != "nt":
            return ActionResult(False, "Opening local files is available on Windows.", error="windows_only")
        os.startfile(str(path))  # type: ignore[attr-defined]
        return ActionResult(True, f"Opened {path.name}", data={"path": str(path)})

    def delete_file(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        if not path.exists() or not path.is_file():
            return ActionResult(False, f"File does not exist: {path}", error="file_not_found")
        try:
            from send2trash import send2trash
        except ImportError:
            return ActionResult(
                False, "Install send2trash to use recoverable deletion.", error="missing_dependency"
            )
        send2trash(str(path))
        return ActionResult(True, f"Moved {path.name} to the Recycle Bin.", data={"path": str(path)})

    def open_folder(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments.get("path", ".")))
        if not path.exists() or not path.is_dir():
            return ActionResult(False, f"Folder does not exist: {path}", error="folder_not_found")
        if os.name != "nt":
            return ActionResult(False, "Opening folders is available on Windows.", error="windows_only")
        os.startfile(str(path))  # type: ignore[attr-defined]
        return ActionResult(True, f"Opened {path}.", data={"path": str(path)})

    def create_folder(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        if path.exists():
            return ActionResult(False, f"A file or folder already exists at {path}.", error="already_exists")
        path.mkdir(parents=True, exist_ok=False)
        return ActionResult(True, f"Created folder {path.name}.", data={"path": str(path)})

    def write_text(self, arguments: dict[str, object]) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        text = str(arguments["text"])
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            return ActionResult(False, "New notes must use an approved text extension.", error="unsupported_file_type")
        if path.exists():
            return ActionResult(False, "Aeris will not overwrite an existing file.", error="already_exists")
        if len(text.encode("utf-8")) > 200_000:
            return ActionResult(False, "New text files are limited to 200 KB.", error="file_too_large")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return ActionResult(True, f"Created {path.name}.", data={"path": str(path)})

    def copy_file(self, arguments: dict[str, object]) -> ActionResult:
        source = self.guard.resolve(str(arguments["source"]))
        destination = self.guard.resolve(str(arguments["destination"]))
        if not source.is_file():
            return ActionResult(False, f"Source file does not exist: {source}", error="file_not_found")
        if destination.exists():
            return ActionResult(False, f"Destination already exists: {destination}", error="already_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return ActionResult(
            True,
            f"Copied {source.name} to {destination}.",
            data={"source": str(source), "destination": str(destination)},
        )

    def move_file(self, arguments: dict[str, object]) -> ActionResult:
        source = self.guard.resolve(str(arguments["source"]))
        destination = self.guard.resolve(str(arguments["destination"]))
        if not source.is_file():
            return ActionResult(False, f"Source file does not exist: {source}", error="file_not_found")
        if destination.exists():
            return ActionResult(False, f"Destination already exists: {destination}", error="already_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return ActionResult(
            True,
            f"Moved {source.name} to {destination}.",
            data={"source": str(source), "destination": str(destination)},
        )
