"""Installed-app diagnostics: no model loads, network, devices, or user data."""
import importlib.util
import json
import platform
import sys

from .config import resource_root
from .router import LocalRouter


def run_diagnostics() -> int:
    route = LocalRouter().route("open notepad")
    core_ok = bool(route and route.actions and route.actions[0].tool == "desktop.open_app")
    report = {
        "python": sys.version.split()[0], "os": platform.platform(), "local_route": core_ok,
        "optional_packages": {name: importlib.util.find_spec(name) is not None for name in (
            "PySide6", "sounddevice", "faster_whisper", "playwright", "keyring")},
        "catalogs": {name: (resource_root() / "config" / name).is_file() for name in (
            "apps.windows.json", "packages.windows.json")},
        "limits": "Presence only; devices, model assets, browser binaries and accounts are not tested.",
    }
    print(json.dumps(report, indent=2))
    return 0 if core_ok and all(report["catalogs"].values()) else 1