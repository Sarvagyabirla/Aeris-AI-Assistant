from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import time
from pathlib import Path

from ..access import ScopePolicy
from ..core.file_publication import HeldSource as _HeldSource
from ..core.file_publication import cleanup_owned_stage, publish_exclusive
from ..models import ActionResult
from ..state import CancelledError

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

_TRANSFER_LIMIT = 2 * 1024 * 1024 * 1024


def _identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


class PathGuard:
    def __init__(self, allowed_roots: tuple[Path, ...]):
        self.policy = ScopePolicy(allowed_roots)

    @property
    def allowed_roots(self):
        return self.policy.roots

    def resolve(self, value: str | Path) -> Path:
        if not self.allowed_roots:
            raise PermissionError("File access is disabled. Select trusted paths in settings.")
        raw = Path(os.path.expandvars(str(value))).expanduser()
        candidate = raw.resolve() if raw.is_absolute() else (self.allowed_roots[0] / raw).resolve()
        self.policy.check(candidate)
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

    def find_files(self, arguments: dict[str, object], token=None) -> ActionResult:
        query = str(arguments["query"]).strip().lower()
        if not query:
            return ActionResult(False, "File search query cannot be empty.", error="empty_query")
        limit = max(1, min(int(arguments.get("limit", 20)), 100))
        matches: list[str] = []
        deadline = time.monotonic() + 2.0
        visited = 0
        truncated = False
        for root in self.guard.allowed_roots:
            if token:
                token.raise_if_cancelled()
            if not root.exists():
                continue
            try:
                for directory, folders, names in os.walk(root, followlinks=False):
                    if token:
                        token.raise_if_cancelled()
                    if time.monotonic() >= deadline or visited >= 10_000:
                        truncated = True
                        break
                    # Never traverse generated trees, symlinks or out-of-scope junctions.
                    safe_folders = []
                    for name in folders:
                        if token:
                            token.raise_if_cancelled()
                        path = Path(directory) / name
                        visited += 1
                        if visited >= 10_000 or time.monotonic() >= deadline:
                            truncated = True
                            break
                        if name in {".git", ".venv", "venv", "node_modules", "__pycache__"} or path.is_symlink():
                            continue
                        try:
                            self.guard.resolve(path)
                        except (OSError, PermissionError):
                            continue
                        safe_folders.append(name)
                    folders[:] = safe_folders
                    for name in names:
                        if token:
                            token.raise_if_cancelled()
                        visited += 1
                        if visited >= 10_000 or time.monotonic() >= deadline:
                            truncated = True
                            break
                        if query not in name.lower():
                            continue
                        try:
                            path = self.guard.resolve(Path(directory) / name)
                        except (OSError, PermissionError):
                            continue
                        if path.is_file():
                            matches.append(str(path))
                            if len(matches) >= limit:
                                truncated = True
                                break
                    if truncated:
                        break
            except (OSError, PermissionError):
                continue
            if truncated:
                break
        return ActionResult(True, f"Found {len(matches)} matching files." + (" Search limit reached." if truncated else ""),
                            data={"matches": matches, "truncated": truncated, "visited": visited})

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

    def create_folder(self, arguments: dict[str, object], token=None) -> ActionResult:
        path = self.guard.resolve(str(arguments["path"]))
        if path.exists():
            return ActionResult(False, f"A file or folder already exists at {path}.", error="already_exists")
        def publish():
            self.guard.resolve(str(path))
            path.mkdir(parents=True, exist_ok=False)
        token.commit(publish) if token else publish()
        return ActionResult(True, f"Created folder {path.name}.", data={"path": str(path), 'published': True, 'verified': path.is_dir()})

    def write_text(self, arguments: dict[str, object], token=None) -> ActionResult:
        if token and token.is_cancelled:
            return ActionResult(False, "Note creation cancelled.", error="cancelled")
        path = self.guard.resolve(str(arguments["path"]))
        text = str(arguments["text"])
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            return ActionResult(False, "New notes must use an approved text extension.", error="unsupported_file_type")
        if path.exists():
            return ActionResult(False, "Aeris will not overwrite an existing file.", error="already_exists")
        if len(text.encode("utf-8")) > 200_000:
            return ActionResult(False, "New text files are limited to 200 KB.", error="file_too_large")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".aeris-note-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(text.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            fresh = self.guard.resolve(str(arguments["path"]))
            if fresh != path:
                return ActionResult(False, "Note destination changed; request a fresh preview.", error="stale_path")
            # Hard-link publication fails atomically if the destination exists. Staging
            # shares the destination filesystem. Unsupported filesystems fail closed.
            if token:
                token.commit(lambda: os.link(temporary, path))
            else:
                os.link(temporary, path)
        except FileExistsError:
            return ActionResult(False, "Aeris will not overwrite an existing file.", error="already_exists")
        except CancelledError:
            return ActionResult(False, "Note creation cancelled before publication.", error="cancelled")
        finally:
            Path(temporary).unlink(missing_ok=True)
        data = {"path": str(path), "published": True}
        if token and token.is_cancelled:
            return ActionResult(False, "Note published before cancellation; file retained.", data, "cancelled_after_publication")
        return ActionResult(True, f"Created {path.name}.", data=data)

    def copy_file(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._transfer(arguments, move=False, token=token)

    def move_file(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._transfer(arguments, move=True, token=token)

    def _transfer(self, arguments: dict[str, object], *, move: bool, token=None) -> ActionResult:
        if token:
            token.raise_if_cancelled()
        source = self.guard.resolve(str(arguments["source"]))
        destination = self.guard.resolve(str(arguments["destination"]))
        if not source.is_file():
            return ActionResult(False, f"Source file does not exist: {source}", error="file_not_found")
        source_identity = _identity(source.stat())
        if destination.exists():
            return ActionResult(False, f"Destination already exists: {destination}", error="already_exists")
        data = {"source": str(source), "destination": str(destination),
                "published": False, "source_removed": False, "created_directories": []}
        held = None
        stage_held = None
        destination_held = None
        staged = None
        stage_identity = None
        stage_owner = None
        published = False
        try:
            held = _HeldSource(source, move=move)
            expected_identity = arguments.get('expected_identity')
            if expected_identity is not None and list(_identity(held.initial)) != expected_identity:
                return ActionResult(False, 'File identity changed since the batch review; no move performed.', data, 'stale_source')
            if held.initial.st_size > _TRANSFER_LIMIT:
                return ActionResult(False, "File transfers are limited to 2 GiB.", data, "file_too_large")
            if (_identity(source.stat()) != _identity(held.initial)
                    or source_identity != _identity(held.initial)):
                return ActionResult(False, "Source changed; request a fresh preview.", data, "stale_source")
            parents = []
            parent = destination.parent
            while not parent.exists():
                parents.append(parent)
                parent = parent.parent
            for parent in reversed(parents):
                if token:
                    token.commit(lambda path=parent: path.mkdir(exist_ok=False))
                else:
                    parent.mkdir(exist_ok=False)
                data["created_directories"].append(str(parent))
            fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".aeris-transfer-")
            staged = Path(temporary)
            stage_stat = os.fstat(fd)
            stage_owner = (stage_stat.st_dev, stage_stat.st_ino)
            deadline = time.monotonic() + 300
            received = 0
            digest = hashlib.sha256()
            with os.fdopen(fd, "wb") as output:
                while True:
                    if token:
                        token.raise_if_cancelled()
                    if time.monotonic() >= deadline:
                        return ActionResult(False, "File staging exceeded five minutes.", data, "transfer_timeout")
                    chunk = held.handle.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > _TRANSFER_LIMIT:
                        return ActionResult(False, "Source grew beyond the 2 GiB transfer limit.", data, "source_changed")
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
                os.fsync(output.fileno())
                if arguments.get('expected_sha256') and digest.hexdigest() != arguments['expected_sha256']:
                    return ActionResult(False, 'File bytes changed since the batch review; no move performed.', data, 'stale_source')
                if (_identity(os.fstat(held.handle.fileno())) != _identity(held.initial)
                        or _identity(source.stat()) != _identity(held.initial)):
                    return ActionResult(False, "Source changed while staging; no file published.", data, "source_changed")
                # Windows read-only attributes would also make the stage unlink fail.
                # Access-control lists/alternate streams are not copied by this byte transfer.
                if os.name != "nt":
                    os.chmod(staged, stat.S_IMODE(held.initial.st_mode))
                os.utime(staged, ns=(held.initial.st_atime_ns, held.initial.st_mtime_ns))
                stage_identity = _identity(os.fstat(output.fileno()))
            # Close the writer before acquiring a deny-write/delete handle. Verify
            # both identity and bytes across that gap before publishing anything.
            stage_held = _HeldSource(staged, move=False)
            if _identity(stage_held.initial) != stage_identity:
                stage_held.close()
                stage_held = None
                return ActionResult(False, "Staging identity changed; source retained.", data, "stale_stage")
            staged_digest = hashlib.sha256()
            while chunk := stage_held.handle.read(1024 * 1024):
                if token:
                    token.raise_if_cancelled()
                if time.monotonic() >= deadline:
                    return ActionResult(False, "File verification exceeded five minutes.", data, "transfer_timeout")
                staged_digest.update(chunk)
            if staged_digest.digest() != digest.digest():
                return ActionResult(False, "Staged bytes changed; source retained.", data, "stale_stage")
            if (self.guard.resolve(str(arguments["source"])) != source
                    or self.guard.resolve(str(arguments["destination"])) != destination):
                return ActionResult(False, "Transfer paths changed; request a fresh preview.", data, "stale_path")
            publish_exclusive(staged, destination, token)
            published = data["published"] = True
            data["bytes"] = received
            data["sha256"] = digest.hexdigest()
            if os.name == "nt":
                destination_held = _HeldSource(destination, move=False)
                if (destination_held.initial.st_dev, destination_held.initial.st_ino) != stage_owner:
                    data["outcome_uncertain"] = True
                    return ActionResult(False, "Destination changed after publication; source retained. Review both paths before retrying.", data, "published_destination_changed")
                data["destination_verified"] = True
            if token:
                token.raise_if_cancelled()
            if move:
                try:
                    if token:
                        token.commit(held.delete_owned)
                    else:
                        held.delete_owned()
                    held.close()
                    held = None
                    data["source_removed"] = True
                except OSError:
                    data["outcome_uncertain"] = True
                    return ActionResult(False, "Destination published; source removal could not be verified. Review both paths before retrying.", data, "source_removal_unverified")
        except FileExistsError:
            return ActionResult(False, "Destination already exists; no file was overwritten.", data, "already_exists")
        except CancelledError:
            if published:
                return ActionResult(False, "Destination published before cancellation; retained file and source state are shown.", data, "cancelled_after_publication")
            return ActionResult(False, "Transfer cancelled before publication.", data, "cancelled")
        except NotImplementedError:
            return ActionResult(False, "Safe move is available on Windows. Copy the file instead; source was retained.", data, "unsupported_safe_move")
        except (OSError, ValueError):
            return ActionResult(False, "Transfer could not complete safely. Check file access and a destination filesystem supporting hard links.", data, "transfer_unavailable")
        finally:
            if destination_held is not None:
                try:
                    destination_held.close()
                except OSError:
                    data["outcome_uncertain"] = True
            if staged is not None and stage_owner is not None:
                if not cleanup_owned_stage(staged, stage_owner, stage_held):
                    data["staging_cleanup_incomplete"] = True
                    data["staging_path"] = str(staged)
            if held is not None:
                try:
                    held.close()
                except OSError:
                    data["outcome_uncertain"] = True
        if data.get("staging_cleanup_incomplete") or data.get("outcome_uncertain"):
            return ActionResult(False, "File effects are retained; handle or staging cleanup needs review.", data, "cleanup_incomplete")
        if token and token.is_cancelled:
            return ActionResult(False, "Transfer completed before cancellation; retained effects are shown.", data, "cancelled_after_publication")
        verb = "Moved" if move else "Copied"
        return ActionResult(True, f"{verb} {source.name} to {destination}.", data=data)
