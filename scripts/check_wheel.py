"""Check wheel exclusions/resources/imports in a disposable directory, without installation."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.wheel) as archive, tempfile.TemporaryDirectory(prefix="aeris-wheel-check-") as temporary:
        names = archive.namelist()
        required = {"aeris/resources/config/apps.windows.json", "aeris/resources/config/packages.windows.json"}
        if not required <= set(names):
            raise RuntimeError("Wheel is missing application catalogs")
        forbidden = [name for name in names if Path(name).suffix.lower() in {".db", ".sqlite3", ".pem", ".pfx", ".key"}
                     or Path(name).name.lower() in {".env", "credentials.json", "token.json", "settings.json"}
                     or Path(name).name.lower().startswith((".env.", "client_secret", "oauth-token"))]
        if forbidden:
            raise RuntimeError("Wheel contains excluded runtime/credential artifacts")
        destination = Path(temporary).resolve()
        if any(not (destination / name).resolve().is_relative_to(destination) for name in names):
            raise RuntimeError("Wheel contains an escaping archive path")
        archive.extractall(destination)
        code = (
            "import pathlib,sys; sys.path.insert(0,sys.argv[1]); "
            "import aeris, aeris.cli, aeris.schemas, aeris.tools; "
            "import importlib.util; "
            "[__import__(name) for name in ('aeris.ui.desktop','aeris.ui.hotkeys','aeris.ui.single_instance')] if importlib.util.find_spec('PySide6') else None; "
            "assert pathlib.Path(aeris.__file__).is_relative_to(sys.argv[1]); "
            "from aeris.diagnostics import run_diagnostics; raise SystemExit(run_diagnostics())"
        )
        result = subprocess.run([sys.executable, "-I", "-c", code, str(destination)], cwd=destination,
                                capture_output=True, text=True, timeout=30, check=False)
        print(json.dumps({"sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                          "catalogs_present": True, "excluded_artifacts": len(forbidden),
                          "isolated_import_self_test_exit": result.returncode}, indent=2))
        if result.returncode:
            raise RuntimeError("Wheel import/self-test failed; inspect package resources and dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
