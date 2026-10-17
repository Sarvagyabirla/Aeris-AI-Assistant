from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from ..models import ActionResult
from ..state import CancelledError


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


class _KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32),
                ("dwExtraInfo", ctypes.c_size_t)]


class _MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32),
                ("mouseData", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class _HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16), ("wParamH", ctypes.c_uint16)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyboardInput), ("mi", _MouseInput), ("hi", _HardwareInput)]


class _Input(ctypes.Structure):
    _anonymous_ = ("event",)
    _fields_ = [("type", ctypes.c_uint32), ("event", _InputUnion)]


class _Rect(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int32) for name in ("left", "top", "right", "bottom")]


class _GuiThreadInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                *[(name, ctypes.c_void_p) for name in ("hwndActive", "hwndFocus", "hwndCapture",
                                                       "hwndMenuOwner", "hwndMoveSize", "hwndCaret")],
                ("rcCaret", _Rect)]


class _UnicodeKeyboard:
    """One owner-thread Unicode SendInput adapter; never reads or replaces the clipboard.

    Native ABI and restrictions: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
    https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-keybdinput
    """

    def __init__(self, user32=None):
        self.user32 = user32 if user32 is not None else ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = (ctypes.c_uint32, ctypes.POINTER(_Input), ctypes.c_int)
        self.user32.SendInput.restype = ctypes.c_uint32
        self.user32.GetGUIThreadInfo.argtypes = (ctypes.c_uint32, ctypes.POINTER(_GuiThreadInfo))
        self.user32.GetGUIThreadInfo.restype = ctypes.c_int
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = ctypes.c_int16

    def focus(self, thread_id):
        info = _GuiThreadInfo(cbSize=ctypes.sizeof(_GuiThreadInfo))
        if not self.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            return None, None
        return info.hwndActive, info.hwndFocus

    def modifiers_down(self):
        return any(self.user32.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, 0x5B, 0x5C))

    def send_scalar(self, character):
        encoded = character.encode("utf-16-le", errors="strict")
        units = [int.from_bytes(encoded[index:index + 2], "little") for index in range(0, len(encoded), 2)]
        # Keep each scalar's surrogate pair in one native batch, with balanced down/up events.
        events = (_Input * (2 * len(units)))()
        for index, (unit, flags) in enumerate([(unit, 0x0004) for unit in units] +
                                              [(unit, 0x0004 | 0x0002) for unit in units]):
            events[index].type = 1  # INPUT_KEYBOARD
            events[index].ki = _KeyboardInput(0, unit, flags, 0, 0)
        return int(self.user32.SendInput(len(events), events, ctypes.sizeof(_Input)))


class _WindowState:
    """Typed native exports; pywin32 does not wrap all of these Windows APIs."""
    def __init__(self, user32=None):
        self.user32 = user32 if user32 is not None else ctypes.WinDLL('user32', use_last_error=True)
        self.user32.ShowWindowAsync.argtypes = (ctypes.c_void_p, ctypes.c_int)
        self.user32.ShowWindowAsync.restype = ctypes.c_int
        for name in ('IsIconic', 'IsZoomed'):
            function = getattr(self.user32, name)
            function.argtypes = (ctypes.c_void_p,)
            function.restype = ctypes.c_int

    def show(self, window_id, value):
        return bool(self.user32.ShowWindowAsync(window_id, value))

    def is_minimized(self, window_id):
        return bool(self.user32.IsIconic(window_id))

    def is_maximized(self, window_id):
        return bool(self.user32.IsZoomed(window_id))


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
        
        # Fallback to Windows Registry App Paths
        if os.name == "nt":
            import winreg
            for hkey in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    key = winreg.OpenKey(hkey, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
                    # Try name.exe
                    try:
                        subkey = winreg.OpenKey(key, f"{name}.exe")
                        path, _ = winreg.QueryValueEx(subkey, "")
                        if path and Path(path).exists():
                            return path
                    except FileNotFoundError:
                        pass
                except OSError:
                    continue
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
        self._typing_selection_lock = threading.Lock()
        self._typing_selection = None

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

    @staticmethod
    def _window_identity(window_id, expected_names=None):
        import psutil
        import win32gui
        import win32process
        if not win32gui.IsWindow(window_id) or not win32gui.IsWindowVisible(window_id):
            return None
        if win32gui.GetClassName(window_id) in {"Progman", "WorkerW", "Shell_TrayWnd"}:
            return None
        _, pid = win32process.GetWindowThreadProcessId(window_id)
        process = psutil.Process(pid)
        process_name = process.name().lower()
        if expected_names is not None and process_name not in expected_names:
            return None
        title = win32gui.GetWindowText(window_id)
        if len(title) > 512:
            return None
        return {"window_id": window_id, "process_id": pid, "process_created": float(process.create_time()),
                "expected_title": title, "process_name": process_name}

    def prepare_close_app(self, arguments, token=None):
        if failure := self._require_windows():
            return failure
        name = str(arguments["name"]).strip().lower()
        expected = PROCESS_NAMES.get(name)
        if not expected:
            return ActionResult(False, f"Closing '{name}' is not configured.", error="app_not_configured")
        try:
            import time

            import psutil
            import win32gui
            candidates = []
            deadline = time.monotonic() + 2
            def inspect(window_id, _):
                if token:
                    token.raise_if_cancelled()
                if len(candidates) >= 20 or time.monotonic() >= deadline:
                    return
                try:
                    identity = self._window_identity(window_id, expected)
                    if identity and identity["process_name"] in expected:
                        candidates.append(identity)
                except (psutil.Error, OSError):
                    pass
            win32gui.EnumWindows(inspect, None)
            requested = arguments.get("window_id") or win32gui.GetForegroundWindow()
            selected = next((item for item in candidates if item["window_id"] == requested), None)
            if selected is None and len(candidates) == 1:
                selected = candidates[0]
            if selected is None:
                return ActionResult(False, "No unique application window is selected. Focus the intended app window and retry; no process was terminated.", error="ambiguous_window")
            return {"name": name, **{key: value for key, value in selected.items() if key != "process_name"}}
        except ImportError:
            return ActionResult(False, "Windows window-control dependencies are unavailable.", error="missing_dependency")

    def close_app(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        window_id = arguments.get("window_id")
        if not window_id:
            return ActionResult(False, "A current exact window preview is required before closing an app.", error="window_scope_required")
        try:
            import win32gui
            if token:
                token.raise_if_cancelled()
            identity = self._window_identity(window_id, PROCESS_NAMES.get(arguments["name"], set()))
            keys = ("window_id", "process_id", "process_created", "expected_title")
            if not identity or identity["process_name"] not in PROCESS_NAMES.get(arguments["name"], set()) or any(
                identity[key] != arguments.get(key) for key in keys
            ):
                return ActionResult(False, "The window changed after approval. Request a fresh preview.", error="stale_window")
            def post_close():
                win32gui.PostMessage(window_id, 0x0010, 0, 0)  # WM_CLOSE; never process termination.
            if token:
                token.commit(post_close)
            else:
                post_close()
            data = {"window_id": window_id, "process_id": identity["process_id"], "requested": True, "verified": False}
            if token and token.is_cancelled:
                data["uncertain"] = True
                return ActionResult(False, "Close was requested before cancellation. Review the app's unsaved-work prompt; closure is not verified.", data, "cancelled_after_effect")
            return ActionResult(True, "Requested this window to close normally. Unsaved-work prompts remain in the app; closure is not yet verified.", data)
        except CancelledError:
            return ActionResult(False, "Window close cancelled before dispatch.", error="cancelled")
        except ImportError:
            return ActionResult(False, "Windows window-control dependencies are unavailable.", error="missing_dependency")
        except Exception:
            return ActionResult(False, "The selected window is unavailable or Windows denied the close request.", error="window_close_failed")

    def _audio_operation(self, operation, token=None) -> ActionResult:
        """Own COM and endpoint references on the calling task thread for one operation."""
        initialized = False
        operation_started = False
        endpoint = interface = device = None
        try:
            from ctypes import POINTER, cast

            import pythoncom
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            if token:
                token.raise_if_cancelled()
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            initialized = True
            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            if token:
                token.raise_if_cancelled()
            operation_started = True
            result = operation(endpoint)
            result.data["device"] = "default output endpoint"
            if token and token.is_cancelled:
                result.success = False
                result.error = "cancelled_after_effect"
                result.message += " Cancellation arrived after the native call; the observed effect is retained."
            return result
        except CancelledError:
            return ActionResult(False, "Audio command cancelled before the native call.", error="cancelled")
        except ImportError:
            return ActionResult(
                False, "Install the Windows extras to control volume.", error="missing_dependency"
            )
        except Exception:
            return ActionResult(False, "Windows audio service is unavailable. Check the default output device.",
                                data={"uncertain": operation_started}, error="com_error")
        finally:
            # Drop native references before closing this thread's COM scope.
            endpoint = interface = device = None
            if initialized:
                pythoncom.CoUninitialize()

    def set_volume(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        level = arguments["level"]
        if type(level) is not int or not 0 <= level <= 100:
            return ActionResult(False, "Use a whole percentage from 0 to 100.", error="invalid_arguments")
        def set_level(endpoint):
            endpoint.SetMasterVolumeLevelScalar(level / 100.0, None)
            observed = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            verified = abs(observed - level) <= 1
            return ActionResult(verified, f"Observed volume: {observed}% (requested {level}%).",
                                {"level": observed, "requested": level, "verified": verified},
                                None if verified else "verification_failed")
        return self._audio_operation(set_level, token)

    def change_volume(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        delta = arguments.get("delta", 10)
        if type(delta) is not int or not -100 <= delta <= 100:
            return ActionResult(False, "Use a whole volume change from -100 to 100.", error="invalid_arguments")
        def change_level(endpoint):
            current = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            target = max(0, min(current + delta, 100))
            if token:
                token.raise_if_cancelled()
            endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)
            observed = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
            verified = abs(observed - target) <= 1
            return ActionResult(verified, f"Observed volume: {observed}% (requested {target}%).",
                                {"level": observed, "requested": target, "verified": verified},
                                None if verified else "verification_failed")
        return self._audio_operation(change_level, token)

    def _brightness_operation(self, value, relative=False, token=None):
        if failure := self._require_windows():
            return failure
        if type(value) is not int or not (-100 <= value <= 100 if relative else 0 <= value <= 100):
            return ActionResult(False, "Use a whole percentage in the supported range.", error="invalid_arguments")
        requested = False
        try:
            import screen_brightness_control as brightness
            if token:
                token.raise_if_cancelled()
            before = brightness.get_brightness()
            before = [int(item) for item in (before if isinstance(before, list) else [before])]
            if not before:
                return ActionResult(False, "No controllable display brightness was observed.", error="display_unavailable")
            targets = [max(0, min(100, level + value)) for level in before] if relative else [value] * len(before)
            if token:
                token.raise_if_cancelled()
            requested = True
            brightness.set_brightness(f"{value:+d}" if relative else value)
            observed = brightness.get_brightness()
            observed = [int(item) for item in (observed if isinstance(observed, list) else [observed])]
            verified = observed == targets
            data = {"levels": observed, "requested_levels": targets, "verified": verified,
                    "scope": "all supported displays", "level": observed[0] if observed else None}
            message = f"Observed display brightness: {observed}% (requested {targets}%)."
            if token and token.is_cancelled:
                return ActionResult(False, message + " Cancellation arrived after the native call; observed effects are retained.", data, "cancelled_after_effect")
            return ActionResult(verified, message, data, None if verified else "verification_failed")
        except CancelledError:
            return ActionResult(False, "Brightness command cancelled before the native call.", error="cancelled")
        except ImportError:
            return ActionResult(False, "Install the declared Windows extras to control brightness.", error="missing_dependency")
        except Exception:
            return ActionResult(False, "Display brightness could not be read back. Check Windows monitor support before retrying.",
                                {"uncertain": requested}, "display_error")

    def set_brightness(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._brightness_operation(arguments["level"], token=token)

    def change_brightness(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._brightness_operation(arguments.get("delta", 10), relative=True, token=token)

    def media_control(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        action = str(arguments["action"]).strip().lower()
        if action in {"mute", "unmute", "toggle_mute"}:
            def mute(endpoint):
                desired = not bool(endpoint.GetMute()) if action == "toggle_mute" else action == "mute"
                if token:
                    token.raise_if_cancelled()
                endpoint.SetMute(desired, None)
                observed = bool(endpoint.GetMute())
                return ActionResult(observed == desired, "Output is muted." if observed else "Output is unmuted.",
                                    {"muted": observed, "verified": observed == desired},
                                    None if observed == desired else "verification_failed")
            return self._audio_operation(mute, token)
        if action in {"play", "pause"}:
            return ActionResult(False, "Absolute play/pause needs a supported selected media session, which is not connected yet. Use 'toggle playback' only if you intend a toggle.", error="unsupported_absolute_media")
        key_codes = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2}
        if action not in key_codes:
            return ActionResult(False, f"Unsupported media action: {action}", error="invalid_action")
        key = key_codes[action]
        if token and token.is_cancelled:
            return ActionResult(False, "Media command cancelled before key dispatch.", error="cancelled")
        ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)
        return ActionResult(True, f"Sent media command: {action.replace('_', ' ')}. Playback state is not verified.", data={"verified": False})

    _typing_keys = ("window_id", "process_id", "process_created", "expected_title", "process_name", "focus_window_id")

    def _typing_identity(self, window_id, keyboard=None):
        import win32gui
        import win32process

        identity = self._window_identity(window_id)
        if not identity or identity["process_id"] == os.getpid():
            return None
        # Do not bind a truncated title: two different titles could share a prefix.
        if len(win32gui.GetWindowText(window_id)) > 512:
            return None
        thread_id, pid = win32process.GetWindowThreadProcessId(window_id)
        keyboard = keyboard or _UnicodeKeyboard()
        active, focus = keyboard.focus(thread_id)
        if active != window_id or not focus or not win32gui.IsWindow(focus):
            return None
        if focus != window_id and not win32gui.IsChild(window_id, focus):
            return None
        if win32process.GetWindowThreadProcessId(focus)[1] != pid:
            return None
        return {**identity, "focus_window_id": focus}

    def list_typing_targets(self, token=None):
        """Bounded metadata-only chooser; selection is reobserved before approval."""
        if self._require_windows():
            return []
        import psutil
        import win32gui

        keyboard = _UnicodeKeyboard()
        candidates = []
        deadline = time.monotonic() + 2

        def inspect(window_id, _):
            if token:
                token.raise_if_cancelled()
            if len(candidates) >= 20 or time.monotonic() >= deadline:
                return
            try:
                identity = self._typing_identity(window_id, keyboard)
                if identity and identity["expected_title"]:
                    candidates.append(identity)
            except (psutil.Error, OSError):
                pass

        win32gui.EnumWindows(inspect, None)
        return candidates

    def select_typing_target(self, window_id):
        if failure := self._require_windows():
            return failure
        try:
            identity = self._typing_identity(window_id)
            if not identity:
                return ActionResult(False, "Choose an available application window with a focused control.", error="typing_target_unavailable")
            with self._typing_selection_lock:
                self._typing_selection = dict(identity)
            return ActionResult(True, "Selected this window for the next typing preview.", data=dict(identity))
        except Exception:
            return ActionResult(False, "The selected typing window is unavailable. Choose it again.", error="typing_target_unavailable")

    def restore_typing_target(self, arguments, token=None):
        """Refocus only after UI explicitly approves this exact target; never sends keys.

        SetForegroundWindow may be refused by Windows. False always forbids typing,
        even if activation itself succeeded but the expected child focus did not return.
        """
        if self._require_windows() or any(key not in arguments for key in self._typing_keys):
            return False
        try:
            import win32gui

            if token:
                token.raise_if_cancelled()
            keyboard = _UnicodeKeyboard()
            window_id = arguments["window_id"]
            identity = self._typing_identity(window_id, keyboard)
            if not identity or any(identity[key] != arguments[key] for key in self._typing_keys):
                return False
            def activate():
                win32gui.SetForegroundWindow(window_id)
            token.commit(activate) if token else activate()
            identity = self._typing_identity(window_id, keyboard)
            return bool((not token or not token.is_cancelled) and win32gui.GetForegroundWindow() == window_id and identity and
                        all(identity[key] == arguments[key] for key in self._typing_keys))
        except Exception:
            return False

    def prepare_type_text(self, arguments, token=None):
        if failure := self._require_windows():
            return failure
        try:
            import win32gui

            if token:
                token.raise_if_cancelled()
            with self._typing_selection_lock:
                selected = dict(self._typing_selection) if self._typing_selection else None
            window_id = arguments.get("window_id") or (selected["window_id"] if selected else win32gui.GetForegroundWindow())
            identity = self._typing_identity(window_id)
            if not identity:
                return ActionResult(False, "Select the intended application window and focused control before requesting typing.", error="typing_target_unavailable")
            if selected and not arguments.get("window_id") and any(identity[key] != selected[key] for key in self._typing_keys):
                return ActionResult(False, "The selected typing window or control changed. Select it again before a fresh preview.", error="stale_typing_target")
            return {"text": arguments["text"], **identity}
        except CancelledError:
            raise
        except ImportError:
            return ActionResult(False, "Windows window-control dependencies are unavailable.", error="missing_dependency")
        except Exception:
            return ActionResult(False, "The typing target could not be observed. Select the window again.", error="typing_target_unavailable")

    def type_text(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        text = str(arguments["text"])
        if len(text) > 5_000:
            return ActionResult(
                False, "Typing is limited to 5,000 characters per action.", error="text_too_long"
            )
        if any(key not in arguments for key in self._typing_keys):
            return ActionResult(False, "An exact window and focused-control preview is required before typing.", error="typing_scope_required")
        characters = inserted = 0
        attempted = False

        def finish(success, message, error=None):
            data = {"window_id": arguments["window_id"], "process_id": arguments["process_id"],
                    "focus_window_id": arguments["focus_window_id"], "characters_dispatched": characters,
                    "input_events_inserted": inserted, "requested_characters": len(text), "verified": False,
                    "uncertain": attempted}
            if not success and attempted:
                message += f" Complete character batches dispatched: {characters}/{len(text)}; native input events accepted: {inserted}."
            return ActionResult(success, message + " Text insertion is not read back; inspect the target before retrying.", data, error)

        try:
            import win32gui
            import win32process

            # Validate all text before any effect, including direct Python callers.
            text.encode("utf-16-le", errors="strict")
            if not text or any(ord(char) < 32 and char not in "\t\r\n" or ord(char) == 127 for char in text):
                return finish(False, "Text contains an unsupported control character or is empty.", "invalid_arguments")
            keyboard = _UnicodeKeyboard()
            window_id = arguments["window_id"]
            for character in text:
                if token:
                    token.raise_if_cancelled()
                identity = self._typing_identity(window_id, keyboard)
                if not identity or any(identity[key] != arguments[key] for key in self._typing_keys):
                    return finish(False, "The approved typing target changed. Select it again and request a fresh preview.", "stale_typing_target")

                def dispatch():
                    nonlocal attempted
                    # Check again immediately inside the Stop gate. Windows does not provide
                    # an atomic compare-foreground-and-inject API; one scalar remains the race bound.
                    thread_id, _ = win32process.GetWindowThreadProcessId(window_id)
                    active, focus = keyboard.focus(thread_id)
                    if win32gui.GetForegroundWindow() != window_id or active != window_id or focus != arguments["focus_window_id"]:
                        return None
                    if keyboard.modifiers_down():
                        return -1
                    attempted = True
                    return keyboard.send_scalar(character)

                count = token.commit(dispatch) if token else dispatch()
                if count is None:
                    return finish(False, "The foreground window or focused control changed. Typing stopped.", "stale_typing_target")
                if count == -1:
                    return finish(False, "Release Shift, Ctrl, Alt and Windows keys before requesting typing again.", "keyboard_modifiers_active")
                inserted += count
                expected = len(character.encode("utf-16-le"))  # two events per UTF-16 code unit
                if count != expected:
                    return finish(False, "Windows did not accept the complete input batch. No retry was attempted; elevated windows or application input restrictions may block typing.", "input_dispatch_failed")
                characters += 1
            if token and token.is_cancelled:
                return finish(False, "Typing stopped after input was dispatched.", "cancelled_after_effect")
            return finish(True, f"Dispatched {characters} Unicode characters to the approved window.")
        except CancelledError:
            return finish(False, "Typing cancelled; dispatched input is retained.", "cancelled_after_effect" if attempted else "cancelled")
        except UnicodeError:
            return finish(False, "Text must contain valid Unicode scalar values.", "invalid_arguments")
        except ImportError:
            return finish(False, "Windows window-control dependencies are unavailable.", "missing_dependency")
        except Exception:
            return finish(False, "Windows input or the approved window became unavailable. Typing stopped.", "typing_failed")

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

    def prepare_window_action(self, arguments, token=None):
        if arguments['action'] not in {'minimize_current', 'maximize_current'}:
            return arguments
        if failure := self._require_windows():
            return failure
        import win32gui
        if token:
            token.raise_if_cancelled()
        with self._typing_selection_lock:
            selected = dict(self._typing_selection) if self._typing_selection else None
        target = arguments.get('window_id') or (selected['window_id'] if selected else win32gui.GetForegroundWindow())
        identity = self._window_identity(target)
        if not identity or identity['process_id'] == os.getpid():
            return ActionResult(False, 'Select an external task window before minimizing or maximizing it. Aeris will not guess a foreground target.', error='window_scope_required')
        keys = ('window_id', 'process_id', 'process_created', 'expected_title')
        if selected and not arguments.get('window_id') and any(identity[key] != selected[key] for key in keys):
            return ActionResult(False, 'Selected task window changed. Select it again.', error='stale_window')
        return {'action': arguments['action'], **{key: identity[key] for key in keys}}

    def window_action(self, arguments: dict[str, object], token=None) -> ActionResult:
        if failure := self._require_windows():
            return failure
        action = str(arguments["action"]).strip().lower()
        if action in {'minimize_current', 'maximize_current'}:
            window_api = _WindowState()
            keys = ('window_id', 'process_id', 'process_created', 'expected_title')
            if any(key not in arguments for key in keys):
                return ActionResult(False, 'An observed selected task window is required.', error='window_scope_required')
            sent = False
            try:
                def dispatch():
                    identity = self._window_identity(arguments['window_id'])
                    if not identity or any(identity[key] != arguments[key] for key in keys) or identity['process_id'] == os.getpid():
                        raise ValueError('Window identity changed')
                    if not window_api.show(arguments['window_id'], 6 if action == 'minimize_current' else 3):
                        raise OSError('Window show request was not accepted')
                token.commit(dispatch) if token else dispatch()
                sent = True
                check = window_api.is_minimized if action == 'minimize_current' else window_api.is_maximized
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    identity = self._window_identity(arguments['window_id'])
                    if not identity or any(identity[key] != arguments[key] for key in keys):
                        break
                    if check(arguments['window_id']):
                        return ActionResult(True, 'Selected window ' + ('minimized.' if action == 'minimize_current' else 'maximized.'),
                            {'window_id': arguments['window_id'], 'process_id': arguments['process_id'], 'verified': True, 'published': True})
                    if token:
                        token.raise_if_cancelled()
                    time.sleep(.02)
                return ActionResult(False, 'Window request was dispatched, but its effect could not be verified.',
                    {'window_id': arguments['window_id'], 'uncertain': True}, 'verification_failed')
            except (CancelledError, ValueError, OSError):
                return ActionResult(False, 'Window action stopped. A dispatched effect may remain; inspect the selected window.',
                    {'window_id': arguments['window_id'], 'uncertain': sent, 'published': sent}, 'cancelled' if token and token.is_cancelled else 'stale_window')
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
        token.commit(lambda: pyautogui.hotkey(*keys)) if token else pyautogui.hotkey(*keys)
        return ActionResult(True, f"Window shortcut dispatched: {action.replace('_', ' ')}. Effect is not read back.", {'verified': False})

    def prepare_close_current_window(self, arguments, token=None):
        observed = self.prepare_window_action({'action': 'minimize_current', **arguments}, token)
        if isinstance(observed, ActionResult):
            return observed
        identity = self._window_identity(observed['window_id'])
        name = next((name for name, processes in PROCESS_NAMES.items() if identity and identity.get('process_name') in processes), None)
        if not name:
            return ActionResult(False, 'Graceful closing is not configured for this selected app.', error='app_not_configured')
        return {'name': name, **{key: value for key, value in observed.items() if key != 'action'}}

    def close_current_window(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self.close_app(arguments, token)
