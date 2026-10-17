from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..core.file_publication import HeldSource, cleanup_owned_stage, publish_exclusive
from ..core.process_runner import run_owned
from ..models import ActionResult
from ..state import CancelledError

_INSTALLER_EXTENSIONS = {".appx", ".exe", ".msi", ".msix", ".msixbundle"}
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'
_PARTIAL_LOCK = threading.RLock()
_ACTIVE_PARTIALS: set[Path] = set()
_PARTIAL_MINIMUM_AGE = 24 * 60 * 60


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, validator):
        super().__init__()
        self.validator = validator

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self.validator(newurl, resolve_host=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class DownloadTools:
    """Download public HTTP(S) files without overwriting or automatically executing them."""

    def __init__(
        self,
        download_dir: Path,
        allowed_domains: tuple[str, ...],
        max_bytes: int = 2 * 1024 * 1024 * 1024,
    ):
        self.download_dir = download_dir.expanduser().resolve()
        self.allowed_domains = tuple(domain.strip().lower() for domain in allowed_domains)
        self.max_bytes = max(1, int(max_bytes))

    def _validate_url(self, value: str, *, resolve_host: bool = False) -> str:
        candidate = value.strip()
        if not candidate.startswith(("http://", "https://")):
            raise ValueError("Downloads require a complete http:// or https:// URL.")
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only valid public HTTP and HTTPS URLs can be downloaded.")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing embedded usernames or passwords are blocked.")

        hostname = parsed.hostname.lower().rstrip(".")
        if "*" not in self.allowed_domains and not any(
            hostname == domain or hostname.endswith("." + domain) for domain in self.allowed_domains
        ):
            raise ValueError(f"Domain is not allowed: {hostname}")

        try:
            literal_ip = ipaddress.ip_address(hostname)
        except ValueError:
            literal_ip = None
        if literal_ip is not None and not literal_ip.is_global:
            raise ValueError("Private, local, and link-local download addresses are blocked.")

        if resolve_host:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
            if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
                raise ValueError("The download host resolved to a private or unsafe network address.")
        return candidate

    @staticmethod
    def _safe_filename(value: str) -> str:
        name = Path(unquote(value)).name.strip().strip(".")
        name = "".join("_" if char in _INVALID_FILENAME_CHARS or ord(char) < 32 else char for char in name)
        if not name or name in {".", ".."}:
            name = "download"
        return name[:180]

    def _destination_for(self, name: str) -> Path:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        base = self.download_dir / self._safe_filename(name)
        if not base.exists() and not base.with_suffix(base.suffix + ".aeris.part").exists():
            return base
        for index in range(1, 10_000):
            candidate = base.with_name(f"{base.stem} ({index}){base.suffix}")
            if not candidate.exists() and not candidate.with_suffix(
                candidate.suffix + ".aeris.part"
            ).exists():
                return candidate
        raise FileExistsError("Could not choose a unique download filename.")

    @staticmethod
    def _defender_scan(path: Path, token=None) -> str:
        if token and token.is_cancelled:
            return "cancelled"
        if os.name != "nt":
            return "not_available"
        candidates = [Path(os.environ.get("ProgramFiles", "")) / "Windows Defender" / "MpCmdRun.exe"]
        platform_dir = Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows Defender" / "Platform"
        if platform_dir.is_dir():
            candidates.extend(sorted(platform_dir.glob("*/MpCmdRun.exe"), reverse=True))
        executable = next((item for item in candidates if item.is_file()), None)
        if executable is None:
            return "not_available"
        scan = run_owned([str(executable), "-Scan", "-ScanType", "3", "-File", str(path)], timeout=300, token=token)
        if scan.reason == "cancelled":
            return "cancelled"
        if scan.reason:
            return "could_not_complete"
        return "completed" if scan.returncode == 0 else "attention_required"

    def download(self, arguments: dict[str, object], token=None) -> ActionResult:
        if token:
            token.raise_if_cancelled()
        try:
            url = self._validate_url(str(arguments["url"]), resolve_host=True)
            requested_name = str(arguments.get("filename") or "").strip()
            parsed_name = Path(urlparse(url).path).name or "download"
            destination = self._destination_for(requested_name or parsed_name)
        except socket.gaierror:
            return ActionResult(
                False,
                "The download host could not be reached. Check the internet connection and URL.",
                error="download_host_unavailable",
            )
        except (OSError, ValueError):
            return ActionResult(False, "Download blocked. Use a public HTTP(S) URL from an allowed domain and an accessible Downloads folder.", error="invalid_download")

        partial = None
        stage_held = None
        destination_held = None
        stage_owner = None
        receipt = {"path": str(destination), "published": False}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Aeris Desktop Assistant"})
            opener = urllib.request.build_opener(_SafeRedirectHandler(self._validate_url))
            deadline = time.monotonic() + 300
            if token:
                token.raise_if_cancelled()
            with opener.open(request, timeout=45) as response:
                final_url = self._validate_url(response.geturl())
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > self.max_bytes:
                    return ActionResult(
                        False,
                        f"Download exceeds the {self.max_bytes // (1024 * 1024)} MB safety limit.",
                        error="download_too_large",
                    )
                if not requested_name:
                    header_name = response.headers.get_filename()
                    if header_name:
                        destination = self._destination_for(header_name)
                        receipt["path"] = str(destination)

                received = 0
                digest = hashlib.sha256()
                descriptor, temporary = tempfile.mkstemp(dir=self.download_dir,
                    prefix=".aeris-download-", suffix=".aeris.part")
                partial = Path(temporary)
                stage_stat = os.fstat(descriptor)
                stage_owner = (stage_stat.st_dev, stage_stat.st_ino)
                with _PARTIAL_LOCK:
                    _ACTIVE_PARTIALS.add(partial)
                with os.fdopen(descriptor, "wb") as handle:
                    while chunk := response.read(1024 * 1024):
                        if token:
                            token.raise_if_cancelled()
                        if time.monotonic() >= deadline:
                            raise ValueError("Download exceeded its total time limit")
                        received += len(chunk)
                        if received > self.max_bytes:
                            raise ValueError(
                                f"Download exceeded the {self.max_bytes // (1024 * 1024)} MB safety limit."
                            )
                        handle.write(chunk)
                        digest.update(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                    staged_stat = os.fstat(handle.fileno())
                stage_held = HeldSource(partial, move=False)
                if (not os.path.samestat(staged_stat, stage_held.initial)
                        or (staged_stat.st_size, staged_stat.st_mtime_ns)
                        != (stage_held.initial.st_size, stage_held.initial.st_mtime_ns)):
                    raise ValueError("Staging identity changed")
                staged_digest = hashlib.sha256()
                while chunk := stage_held.handle.read(1024 * 1024):
                    if token:
                        token.raise_if_cancelled()
                    if time.monotonic() >= deadline:
                        raise ValueError("Download verification exceeded its time limit")
                    staged_digest.update(chunk)
                if digest.digest() != staged_digest.digest():
                    raise ValueError("Staged bytes changed")
                if token:
                    token.raise_if_cancelled()
                # Re-resolve the configured location immediately before publication.
                if (self.download_dir.resolve() != self.download_dir
                        or destination.parent.resolve() != self.download_dir):
                    raise ValueError("Download destination changed; request a fresh preview.")
                publish_exclusive(partial, destination, token)
                receipt.update(published=True, bytes=received, url=final_url, sha256=digest.hexdigest())
                if os.name == "nt":
                    destination_held = HeldSource(destination, move=False)
                    if (destination_held.initial.st_dev, destination_held.initial.st_ino) != stage_owner:
                        receipt["outcome_uncertain"] = True
                        return ActionResult(False, "Download destination changed after publication; review the retained path before retrying.", receipt, "published_destination_changed")
                    receipt["destination_verified"] = True
        except CancelledError:
            return ActionResult(False, "Download cancelled; retained publication state is shown.", receipt,
                                "cancelled_after_publication" if receipt["published"] else "cancelled")
        except FileExistsError:
            return ActionResult(False, "Download destination appeared while downloading; no existing file was overwritten.", receipt, "already_exists")
        except Exception:
            return ActionResult(False, "Download could not complete. Check connectivity, file size, access, and a destination filesystem supporting hard links.", receipt, "download_failed")
        finally:
            if destination_held is not None:
                try:
                    destination_held.close()
                except OSError:
                    receipt["outcome_uncertain"] = True
            if partial is not None:
                with _PARTIAL_LOCK:
                    try:
                        if stage_owner is not None and not cleanup_owned_stage(partial, stage_owner, stage_held):
                            receipt["staging_cleanup_incomplete"] = True
                            receipt["staging_path"] = str(partial)
                    finally:
                        _ACTIVE_PARTIALS.discard(partial)

        if receipt.get("staging_cleanup_incomplete") or receipt.get("outcome_uncertain"):
            return ActionResult(False, "Download was published; its staging file could not be removed. Review the retained paths.", receipt, "cleanup_incomplete")
        if token and token.is_cancelled:
            return ActionResult(False, "Download published before cancellation; file remains, scan did not run.",
                data=receipt, error="cancelled_after_publication")
        try:
            scan_status = self._defender_scan(destination, token=token)
        except CancelledError:
            scan_status = "cancelled"
        except Exception:
            return ActionResult(False, "Download was published; safety verification could not complete. File remains for review.",
                data=receipt, error="verification_incomplete")
        receipt["defender_scan"] = scan_status
        if scan_status == "cancelled" or (token and token.is_cancelled):
            return ActionResult(False, "Scan cancelled. Downloaded file remains; safety verification is incomplete.",
                data=receipt, error="cancelled_after_publication")
        if scan_status not in {"completed", "attention_required", "could_not_complete", "not_available"}:
            return ActionResult(False, "Download was published; safety verification returned no supported result.", receipt, "verification_incomplete")
        receipt["file_present"] = destination.is_file()
        if not receipt["file_present"]:
            return ActionResult(False, "Download was published but is no longer present after verification. Review Microsoft Defender history before retrying.", receipt, "download_unavailable_after_scan")
        installer_note = (
            " It was not executed; use 'install downloaded installer <path>' after reviewing it."
            if destination.suffix.lower() in _INSTALLER_EXTENSIONS
            else ""
        )
        scan_note = {
            "completed": " Microsoft Defender scan completed.",
            "attention_required": " Microsoft Defender reported that attention may be required.",
            "could_not_complete": " Microsoft Defender scan could not complete.",
            "not_available": " Microsoft Defender scanning was not available.",
        }[scan_status]
        return ActionResult(
            scan_status != "attention_required",
            f"Downloaded {destination.name} to {self.download_dir}.{scan_note}{installer_note}",
            data=receipt,
            error="defender_attention" if scan_status == "attention_required" else None,
        )

    def open_downloads(self, _: dict[str, object]) -> ActionResult:
        if os.name != "nt":
            return ActionResult(False, "Opening Downloads is available on Windows.", error="windows_only")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.download_dir))  # type: ignore[attr-defined]
        return ActionResult(True, f"Opened {self.download_dir}.", data={"path": str(self.download_dir)})

    def clear_partial_downloads(self, _: dict[str, object], token=None) -> ActionResult:
        """Remove only aged, inactive stages in this instance's configured folder.

        Active ownership is shared across DownloadTools instances in this process.
        The 24-hour threshold also avoids normal bounded jobs in other processes.
        """
        removed: list[str] = []
        skipped = 0
        data = {"removed_paths": removed, "skipped": 0, "minimum_age_hours": 24}
        if token:
            token.raise_if_cancelled()
        if not self.download_dir.exists():
            return ActionResult(True, "No incomplete Aeris downloads need cleanup.", data)
        deadline = time.monotonic() + 2
        try:
            if self.download_dir.resolve() != self.download_dir:
                return ActionResult(False, "Downloads folder changed; request a fresh preview.", data, "stale_path")
            for index, path in enumerate(self.download_dir.glob(".aeris-download-*.aeris.part")):
                if token:
                    token.raise_if_cancelled()
                if index >= 1000 or time.monotonic() >= deadline:
                    data["truncated"] = True
                    break
                with _PARTIAL_LOCK:
                    if path in _ACTIVE_PARTIALS or path.is_symlink():
                        skipped += 1
                        continue
                    observed = path.stat(follow_symlinks=False)
                    if not stat.S_ISREG(observed.st_mode) or time.time() - observed.st_mtime < _PARTIAL_MINIMUM_AGE:
                        skipped += 1
                        continue

                    held = HeldSource(path, move=True) if os.name == "nt" else None
                    try:
                        def remove(candidate=path, expected=observed):
                            if self.download_dir.resolve() != self.download_dir or candidate.parent.resolve() != self.download_dir:
                                raise PermissionError("Destination changed")
                            current = held.initial if held else candidate.stat(follow_symlinks=False)
                            if (not stat.S_ISREG(current.st_mode) or not os.path.samestat(expected, current)
                                    or (expected.st_size, expected.st_mtime_ns) != (current.st_size, current.st_mtime_ns)):
                                return False
                            if held:
                                held.delete_owned()
                            else:
                                candidate.unlink()
                            return True

                        deleted = token.commit(remove) if token else remove()
                        if deleted:
                            removed.append(str(path))
                        else:
                            skipped += 1
                    finally:
                        if held:
                            held.close()
            if token:
                token.raise_if_cancelled()
        except CancelledError:
            data["skipped"] = skipped
            return ActionResult(False, "Partial cleanup cancelled; completed removals are shown.", data,
                                "cancelled_after_cleanup" if removed else "cancelled")
        except OSError:
            data["skipped"] = skipped
            data["outcome_uncertain"] = bool(removed)
            return ActionResult(False, "Partial cleanup could not complete; completed removals are shown.", data, "cleanup_incomplete")
        data["skipped"] = skipped
        return ActionResult(True, f"Removed {len(removed)} inactive Aeris partial downloads older than 24 hours.", data)
