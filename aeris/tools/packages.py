from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..models import ActionResult
from .downloads import DownloadTools
from .filesystem import PathGuard

_INSTALLER_EXTENSIONS = {".appx", ".exe", ".msi", ".msix", ".msixbundle"}
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class PackageTools:
    """Manage trusted Windows packages through winget and launch signed local installers."""

    def __init__(
        self,
        allowed_roots: tuple[Path, ...],
        package_catalog_file: Path | None = None,
        require_signed_installers: bool = True,
    ):
        self.guard = PathGuard(allowed_roots)
        self.require_signed_installers = require_signed_installers
        self.aliases: dict[str, str] = {}
        if package_catalog_file and package_catalog_file.exists():
            payload = json.loads(package_catalog_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self.aliases = {
                    str(name).strip().lower(): str(package_id).strip()
                    for name, package_id in payload.items()
                    if str(name).strip() and str(package_id).strip()
                }

    @staticmethod
    def _require_windows() -> ActionResult | None:
        if os.name != "nt":
            return ActionResult(False, "App installation is available on Windows only.", error="windows_only")
        return None

    @staticmethod
    def _clean_query(value: object) -> str:
        query = str(value).strip()
        if not query or len(query) > 120 or any(char in query for char in "\r\n\0"):
            raise ValueError("The app name or package ID is invalid.")
        return query

    def _package_selector(self, value: object) -> tuple[str, str]:
        query = self._clean_query(value)
        package_id = self.aliases.get(query.lower())
        if package_id:
            return "--id", package_id
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.-]+\.[A-Za-z0-9+_.-]+", query):
            return "--id", query
        return "--name", query

    @staticmethod
    def _clean_output(value: str) -> str:
        cleaned = _ANSI_ESCAPE.sub("", value).replace("\b", "")
        lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]
        return "\n".join(lines[-80:])[-8_000:]

    def _run_winget(self, arguments: list[str], *, timeout: int = 600) -> ActionResult:
        if failure := self._require_windows():
            return failure
        executable = shutil.which("winget")
        if not executable:
            return ActionResult(
                False,
                "Windows Package Manager (winget) is missing. Install or update App Installer from Microsoft Store.",
                error="winget_missing",
            )
        try:
            completed = subprocess.run(
                [executable, *arguments],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return ActionResult(False, "Windows Package Manager timed out safely.", error="winget_timeout")
        output = self._clean_output((completed.stdout or "") + "\n" + (completed.stderr or ""))
        if completed.returncode != 0:
            return ActionResult(
                False,
                "Windows Package Manager could not complete the request.",
                data={"output": output},
                error=f"winget_exit_{completed.returncode}",
            )
        return ActionResult(True, "Windows Package Manager completed the request.", data={"output": output})

    def search(self, arguments: dict[str, object]) -> ActionResult:
        try:
            query = self._clean_query(arguments["query"])
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_package_query")
        result = self._run_winget(
            ["search", "--query", query, "--source", "winget", "--accept-source-agreements"],
            timeout=120,
        )
        if result.success:
            result.message = f"Package search results for {query}."
        return result

    def install(self, arguments: dict[str, object]) -> ActionResult:
        try:
            selector, package = self._package_selector(arguments["package"])
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_package_query")
        result = self._run_winget(
            [
                "install",
                selector,
                package,
                "--exact",
                "--source",
                "winget",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ]
        )
        if result.success:
            result.message = f"Installed {package} through Windows Package Manager."
            result.data["package"] = package
        return result

    def uninstall(self, arguments: dict[str, object]) -> ActionResult:
        try:
            selector, package = self._package_selector(arguments["package"])
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_package_query")
        result = self._run_winget(["uninstall", selector, package, "--exact"])
        if result.success:
            result.message = f"Uninstalled {package}."
            result.data["package"] = package
        return result

    def update(self, arguments: dict[str, object]) -> ActionResult:
        try:
            selector, package = self._package_selector(arguments["package"])
        except ValueError as exc:
            return ActionResult(False, str(exc), error="invalid_package_query")
        result = self._run_winget(
            [
                "upgrade",
                selector,
                package,
                "--exact",
                "--source",
                "winget",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ]
        )
        if result.success:
            result.message = f"Updated {package}."
            result.data["package"] = package
        return result

    def list_installed(self, _: dict[str, object]) -> ActionResult:
        result = self._run_winget(["list"], timeout=180)
        if result.success:
            result.message = "Loaded installed applications."
        return result

    def list_updates(self, _: dict[str, object]) -> ActionResult:
        result = self._run_winget(["upgrade", "--source", "winget", "--accept-source-agreements"], timeout=180)
        if result.success:
            result.message = "Loaded available app updates."
        return result

    @staticmethod
    def _signature(path: Path) -> tuple[str, str]:
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            return "Unknown", "PowerShell is unavailable"
        script = (
            "$s = Get-AuthenticodeSignature -LiteralPath $args[0]; "
            "$subject = if ($s.SignerCertificate) {$s.SignerCertificate.Subject} else {''}; "
            "Write-Output ($s.Status.ToString() + '|' + $subject)"
        )
        try:
            completed = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", script, str(path)],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=30,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return "Unknown", "Signature check failed"
        status, _, signer = (completed.stdout or "Unknown|").strip().partition("|")
        return status or "Unknown", signer.strip()

    def install_file(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        try:
            path = self.guard.resolve(str(arguments["path"]))
        except (OSError, PermissionError) as exc:
            return ActionResult(False, str(exc), error="path_not_allowed")
        if not path.is_file():
            return ActionResult(False, f"Installer does not exist: {path}", error="file_not_found")
        if path.suffix.lower() not in _INSTALLER_EXTENSIONS:
            return ActionResult(False, "Only Windows installer file types are allowed.", error="not_installer")

        scan_status = DownloadTools._defender_scan(path)
        if scan_status == "attention_required":
            return ActionResult(
                False,
                "Microsoft Defender reported that this installer requires attention. It was not launched.",
                error="defender_attention",
            )
        signature_status, signer = self._signature(path)
        if self.require_signed_installers and signature_status.lower() != "valid":
            return ActionResult(
                False,
                f"Installer signature is {signature_status}; Aeris requires a valid digital signature.",
                data={"signature": signature_status, "signer": signer},
                error="invalid_signature",
            )

        try:
            if path.suffix.lower() == ".msi":
                result = int(
                    __import__("ctypes").windll.shell32.ShellExecuteW(
                        None, "runas", "msiexec.exe", f'/i "{path}"', str(path.parent), 1
                    )
                )
            elif path.suffix.lower() == ".exe":
                result = int(
                    __import__("ctypes").windll.shell32.ShellExecuteW(
                        None, "runas", str(path), None, str(path.parent), 1
                    )
                )
            else:
                os.startfile(str(path))  # type: ignore[attr-defined]
                result = 33
        except OSError as exc:
            return ActionResult(False, f"Windows could not launch the installer: {exc}", error="launch_failed")
        if result <= 32:
            return ActionResult(False, "Windows declined or could not launch the installer.", error="launch_failed")
        signer_note = f" Signed by {signer}." if signer else ""
        return ActionResult(
            True,
            f"Launched the verified installer {path.name}.{signer_note} Follow the Windows/UAC prompts.",
            data={"path": str(path), "signature": signature_status, "signer": signer},
        )
