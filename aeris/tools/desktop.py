from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..models import ActionResult


def _windows_paths(*parts: str) -> list[str]:
    roots = [os.getenv("ProgramFiles"), os.getenv("ProgramFiles(x86)"), os.getenv("LOCALAPPDATA")]
    return [str(Path(root, *parts)) for root in roots if root]


DEFAULT_APPS: dict[str, list[str]] = {
    "chrome": ["chrome.exe", *_windows_paths("Google", "Chrome", "Application", "chrome.exe")],
    "edge": ["msedge.exe", *_windows_paths("Microsoft", "Edge", "Application", "msedge.exe")],
    "firefox": ["firefox.exe", *_windows_paths("Mozilla Firefox", "firefox.exe")],
    "vscode": ["code.cmd", "code.exe", *_windows_paths("Programs", "Microsoft VS Code", "Code.exe")],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "blender": ["blender.exe"],
    "spotify": ["spotify.exe", *_windows_paths("Spotify", "Spotify.exe")],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "powerpoint": ["powerpnt.exe"],
    "vlc": ["vlc.exe", *_windows_paths("VideoLAN", "VLC", "vlc.exe")],
    "obs studio": ["obs64.exe", *_windows_paths("obs-studio", "bin", "64bit", "obs64.exe")],
    "notepad++": ["notepad++.exe", *_windows_paths("Notepad++", "notepad++.exe")],
    "task manager": ["taskmgr.exe"],
    "terminal": ["wt.exe"],
    "windows terminal": ["wt.exe"],
    "control panel": ["control.exe"],
}

PROCESS_NAMES: dict[str, set[str]] = {
    "chrome": {"chrome.exe"},
    "edge": {"msedge.exe"},
    "firefox": {"firefox.exe"},
    "vscode": {"code.exe"},
    "notepad": {"notepad.exe"},
    "calculator": {"calculatorapp.exe", "calculator.exe"},
    "paint": {"mspaint.exe"},
    "explorer": {"explorer.exe"},
    "blender": {"blender.exe"},
    "spotify": {"spotify.exe"},
    "fl studio": {"fl64.exe"},
    "davinci resolve": {"resolve.exe"},
    "word": {"winword.exe"},
    "excel": {"excel.exe"},
    "powerpoint": {"powerpnt.exe"},
    "vlc": {"vlc.exe"},
    "obs studio": {"obs64.exe"},
    "notepad++": {"notepad++.exe"},
    "task manager": {"taskmgr.exe"},
    "terminal": {"windowsTerminal.exe", "wt.exe"},
}


class AppCatalog:
    def __init__(self, custom_file: Path | None = None):
        self.apps = {name: list(candidates) for name, candidates in DEFAULT_APPS.items()}
        self._start_apps: dict[str, str] | None = None
        if custom_file and custom_file.exists():
            payload = json.loads(custom_file.read_text(encoding="utf-8"))
            for name, candidates in payload.items():
                if isinstance(candidates, str):
                    candidates = [candidates]
                if isinstance(candidates, list) and all(isinstance(item, str) for item in candidates):
                    self.apps[name.strip().lower()] = candidates

    def resolve(self, name: str) -> str | None:
        for candidate in self.apps.get(name.strip().lower(), []):
            expanded = os.path.expandvars(candidate)
            located = shutil.which(expanded)
            if located:
                return located
            if Path(expanded).exists():
                return str(Path(expanded))
        return None

    @staticmethod
    def _normalized_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def resolve_start_app(self, name: str) -> str | None:
        if os.name != "nt":
            return None
        if self._start_apps is None:
            self._start_apps = {}
            powershell = shutil.which("powershell.exe") or shutil.which("powershell")
            if not powershell:
                return None
            try:
                completed = subprocess.run(
                    [
                        powershell,
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress",
                    ],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=20,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                payload = json.loads(completed.stdout or "[]") if completed.returncode == 0 else []
                if isinstance(payload, dict):
                    payload = [payload]
                for item in payload if isinstance(payload, list) else []:
                    if isinstance(item, dict) and item.get("Name") and item.get("AppID"):
                        self._start_apps[self._normalized_name(str(item["Name"]))] = str(item["AppID"])
            except (OSError, ValueError, subprocess.TimeoutExpired):
                return None
        return self._start_apps.get(self._normalized_name(name))


class DesktopTools:
    def __init__(self, app_catalog_file: Path | None = None, screenshot_dir: Path | None = None):
        self.catalog = AppCatalog(app_catalog_file)
        self.screenshot_dir = screenshot_dir or (Path.home() / "Pictures" / "Aeris")

    @staticmethod
    def _require_windows() -> ActionResult | None:
        if os.name != "nt":
            return ActionResult(
                False, "This desktop control is available on Windows only.", error="windows_only"
            )
        return None

    def open_app(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        name = str(arguments["name"]).strip().lower()
        if name in {"settings", "windows settings"}:
            os.startfile("ms-settings:")  # type: ignore[attr-defined]
            return ActionResult(True, "Opened Windows Settings.")
        executable = self.catalog.resolve(name)
        if not executable:
            app_id = self.catalog.resolve_start_app(name)
            if not app_id:
                available = ", ".join(sorted(self.catalog.apps))
                return ActionResult(
                    False,
                    f"App '{name}' was not found by exact name. Configured apps: {available}. "
                    "Say 'list installed apps' to check the Windows name.",
                    error="app_not_configured",
                )
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{app_id}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            return ActionResult(True, f"Opened {name} from the Windows Start menu.", data={"app_id": app_id})
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            [executable],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        return ActionResult(True, f"Opened {name}.", data={"executable": executable})

    def close_app(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        try:
            import psutil
        except ImportError:
            return ActionResult(False, "Install psutil to close applications.", error="missing_dependency")
        name = str(arguments["name"]).strip().lower()
        expected = PROCESS_NAMES.get(name)
        if not expected:
            return ActionResult(False, f"Closing '{name}' is not configured.", error="app_not_configured")
        closed = 0
        for process in psutil.process_iter(["name"]):
            try:
                if (process.info.get("name") or "").lower() in expected:
                    process.terminate()
                    closed += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        if not closed:
            return ActionResult(False, f"{name} is not currently running.", error="not_running")
        return ActionResult(
            True,
            f"Requested {name} to close. Unsaved-work confirmation was required.",
            data={"processes": closed},
        )

    def set_volume(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        level = max(0, min(int(arguments["level"]), 100))
        try:
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            endpoint.SetMasterVolumeLevelScalar(level / 100.0, None)
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to control volume.", error="missing_dependency"
            )
        return ActionResult(True, f"Volume set to {level}%.", data={"level": level})

    def change_volume(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        delta = int(arguments.get("delta", 10))
        try:
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            current = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            target = max(0, min(current + delta, 100))
            endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to control volume.", error="missing_dependency"
            )
        return ActionResult(True, f"Volume set to {target}%.", data={"level": target})

    def set_brightness(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        level = max(0, min(int(arguments["level"]), 100))
        try:
            import screen_brightness_control as brightness
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to control brightness.", error="missing_dependency"
            )
        brightness.set_brightness(level)
        return ActionResult(True, f"Brightness set to {level}%.", data={"level": level})

    def change_brightness(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        delta = int(arguments.get("delta", 10))
        try:
            import screen_brightness_control as brightness
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to control brightness.", error="missing_dependency"
            )
        current_value = brightness.get_brightness()
        current = int(current_value[0] if isinstance(current_value, list) else current_value)
        target = max(0, min(current + delta, 100))
        brightness.set_brightness(target)
        return ActionResult(True, f"Brightness set to {target}%.", data={"level": target})

    def media_control(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        action = str(arguments["action"]).strip().lower()
        key_codes = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2, "mute": 0xAD}
        if action not in key_codes:
            return ActionResult(False, f"Unsupported media action: {action}", error="invalid_action")
        key = key_codes[action]
        ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)
        return ActionResult(True, f"Media action: {action.replace('_', ' ')}.")

    def type_text(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        text = str(arguments["text"])
        if len(text) > 5_000:
            return ActionResult(
                False, "Typing is limited to 5,000 characters per action.", error="text_too_long"
            )
        try:
            import pyautogui
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to type into applications.", error="missing_dependency"
            )
        pyautogui.write(text, interval=0.01)
        return ActionResult(True, f"Typed {len(text)} characters into the active window.")

    def screenshot(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        try:
            from PIL import ImageGrab
        except ImportError:
            return ActionResult(False, "Install Pillow to capture screenshots.", error="missing_dependency")
        from datetime import datetime

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        destination = self.screenshot_dir / f"aeris-{datetime.now():%Y%m%d-%H%M%S}.png"
        ImageGrab.grab(all_screens=True).save(destination)
        return ActionResult(True, f"Screenshot saved as {destination.name}", data={"path": str(destination)})

    def copy_clipboard(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        text = str(arguments["text"])
        if len(text) > 20_000:
            return ActionResult(False, "Clipboard text is limited to 20,000 characters.", error="text_too_long")
        try:
            import pyperclip
        except ImportError:
            return ActionResult(False, "Install pyperclip to use the clipboard.", error="missing_dependency")
        pyperclip.copy(text)
        return ActionResult(True, f"Copied {len(text)} characters to the clipboard.")

    def read_clipboard(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        try:
            import pyperclip
        except ImportError:
            return ActionResult(False, "Install pyperclip to use the clipboard.", error="missing_dependency")
        text = str(pyperclip.paste())
        if not text:
            return ActionResult(True, "The clipboard does not contain text.", data={"text": ""})
        return ActionResult(
            True,
            "Read text from the clipboard.",
            data={"text": text[:5_000], "truncated": len(text) > 5_000},
        )

    def window_action(self, arguments: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        action = str(arguments["action"]).strip().lower()
        shortcuts = {
            "show_desktop": ("win", "d"),
            "switch_window": ("alt", "tab"),
            "task_view": ("win", "tab"),
            "minimize_all": ("win", "m"),
            "maximize_current": ("win", "up"),
            "minimize_current": ("win", "down"),
        }
        keys = shortcuts.get(action)
        if not keys:
            return ActionResult(False, f"Unsupported window action: {action}", error="invalid_action")
        try:
            import pyautogui
        except ImportError:
            return ActionResult(False, "Install pyautogui for window controls.", error="missing_dependency")
        pyautogui.hotkey(*keys)
        return ActionResult(True, f"Window action: {action.replace('_', ' ')}.")

    def close_current_window(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        try:
            import pyautogui
        except ImportError:
            return ActionResult(False, "Install pyautogui for window controls.", error="missing_dependency")
        pyautogui.hotkey("alt", "f4")
        return ActionResult(True, "Close-current-window shortcut sent after confirmation.")
