from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
from pathlib import Path

from ..models import ActionResult


class SystemTools:
    @staticmethod
    def _require_windows() -> ActionResult | None:
        if os.name != "nt":
            return ActionResult(False, "This system action is available on Windows only.", error="windows_only")
        return None

    def health(self, _: dict[str, object]) -> ActionResult:
        root = Path(os.environ.get("SystemDrive", "C:")) / "\\" if os.name == "nt" else Path("/")
        total, used, free = shutil.disk_usage(root)
        data: dict[str, object] = {
            "computer": platform.node() or "Unknown",
            "operating_system": f"{platform.system()} {platform.release()}",
            "processor": platform.processor() or "Unknown",
            "disk_total_gb": round(total / (1024**3), 1),
            "disk_free_gb": round(free / (1024**3), 1),
            "disk_used_percent": round((used / total) * 100, 1) if total else 0,
        }
        try:
            import psutil

            memory = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            data.update(
                {
                    "memory_total_gb": round(memory.total / (1024**3), 1),
                    "memory_used_percent": round(memory.percent, 1),
                    "cpu_used_percent": round(psutil.cpu_percent(interval=0.2), 1),
                    "battery_percent": round(battery.percent, 1) if battery else None,
                    "plugged_in": bool(battery.power_plugged) if battery else None,
                }
            )
        except ImportError:
            pass
        return ActionResult(True, "Loaded computer health information.", data=data)

    def battery(self, _: dict[str, object]) -> ActionResult:
        try:
            import psutil
        except ImportError:
            return ActionResult(False, "Install psutil to read battery status.", error="missing_dependency")
        battery = psutil.sensors_battery()
        if battery is None:
            return ActionResult(False, "No battery was detected.", error="battery_not_found")
        percent = round(battery.percent)
        power = "plugged in" if battery.power_plugged else "on battery"
        return ActionResult(
            True,
            f"Battery is at {percent}% and {power}.",
            data={"percent": percent, "plugged_in": bool(battery.power_plugged)},
        )

    def lock(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        if not ctypes.windll.user32.LockWorkStation():
            return ActionResult(False, "Windows could not lock the computer.", error="lock_failed")
        return ActionResult(True, "Computer locked.")

    def sleep(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        completed = subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return ActionResult(False, "Windows could not enter sleep mode.", error="sleep_failed")
        return ActionResult(True, "Sleep command sent.")

    def shutdown(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        completed = subprocess.run(
            ["shutdown.exe", "/s", "/t", "10", "/c", "Aeris confirmed shutdown"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return ActionResult(False, "Windows could not schedule shutdown.", error="shutdown_failed")
        return ActionResult(True, "Shutdown scheduled in 10 seconds. Say 'cancel shutdown' to stop it.")

    def restart(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        completed = subprocess.run(
            ["shutdown.exe", "/r", "/t", "10", "/c", "Aeris confirmed restart"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return ActionResult(False, "Windows could not schedule restart.", error="restart_failed")
        return ActionResult(True, "Restart scheduled in 10 seconds. Say 'cancel shutdown' to stop it.")

    def cancel_shutdown(self, _: dict[str, object]) -> ActionResult:
        if failure := self._require_windows():
            return failure
        completed = subprocess.run(
            ["shutdown.exe", "/a"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return ActionResult(False, "There was no shutdown or restart to cancel.", error="nothing_to_cancel")
        return ActionResult(True, "Shutdown or restart cancelled.")
