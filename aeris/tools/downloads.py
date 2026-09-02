from __future__ import annotations

import ipaddress
import os
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..models import ActionResult

_INSTALLER_EXTENSIONS = {".appx", ".exe", ".msi", ".msix", ".msixbundle"}
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


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
    def _defender_scan(path: Path) -> str:
        if os.name != "nt":
            return "not_available"
        candidates = [Path(os.environ.get("ProgramFiles", "")) / "Windows Defender" / "MpCmdRun.exe"]
        platform_dir = Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows Defender" / "Platform"
        if platform_dir.is_dir():
            candidates.extend(sorted(platform_dir.glob("*/MpCmdRun.exe"), reverse=True))
        executable = next((item for item in candidates if item.is_file()), None)
        if executable is None:
            return "not_available"
        try:
            scan = subprocess.run(
                [str(executable), "-Scan", "-ScanType", "3", "-File", str(path)],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return "could_not_complete"
        return "completed" if scan.returncode == 0 else "attention_required"

    def download(self, arguments: dict[str, object]) -> ActionResult:
        try:
            url = self._validate_url(str(arguments["url"]), resolve_host=True)
            requested_name = str(arguments.get("filename", "")).strip()
            parsed_name = Path(urlparse(url).path).name or "download"
            destination = self._destination_for(requested_name or parsed_name)
        except socket.gaierror:
            return ActionResult(
                False,
                "The download host could not be reached. Check the internet connection and URL.",
                error="download_host_unavailable",
            )
        except (OSError, ValueError) as exc:
            return ActionResult(False, f"Download blocked safely: {exc}", error="invalid_download")

        partial = destination.with_suffix(destination.suffix + ".aeris.part")
        request = urllib.request.Request(url, headers={"User-Agent": "Aeris Desktop Assistant"})
        opener = urllib.request.build_opener(_SafeRedirectHandler(self._validate_url))

        try:
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
                        partial = destination.with_suffix(destination.suffix + ".aeris.part")

                received = 0
                with partial.open("xb") as handle:
                    while chunk := response.read(1024 * 1024):
                        received += len(chunk)
                        if received > self.max_bytes:
                            raise ValueError(
                                f"Download exceeded the {self.max_bytes // (1024 * 1024)} MB safety limit."
                            )
                        handle.write(chunk)
                partial.replace(destination)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            partial.unlink(missing_ok=True)
            return ActionResult(False, f"Download failed safely: {exc}", error="download_failed")

        scan_status = self._defender_scan(destination)
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
            data={
                "path": str(destination),
                "bytes": destination.stat().st_size,
                "url": final_url,
                "defender_scan": scan_status,
            },
            error="defender_attention" if scan_status == "attention_required" else None,
        )

    def open_downloads(self, _: dict[str, object]) -> ActionResult:
        if os.name != "nt":
            return ActionResult(False, "Opening Downloads is available on Windows.", error="windows_only")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.download_dir))  # type: ignore[attr-defined]
        return ActionResult(True, f"Opened {self.download_dir}.", data={"path": str(self.download_dir)})

    def clear_partial_downloads(self, _: dict[str, object]) -> ActionResult:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        removed = 0
        for path in self.download_dir.glob("*.aeris.part"):
            if path.is_file():
                path.unlink()
                removed += 1
        return ActionResult(True, f"Removed {removed} incomplete Aeris downloads.")
