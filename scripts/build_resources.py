"""Copy the single source catalog into wheel resources; no duplicated source catalog."""
from pathlib import Path

from setuptools.command.build_py import build_py


class BuildWithResources(build_py):
    def run(self):
        super().run()
        source = Path(__file__).resolve().parent.parent / "config"
        destination = Path(self.build_lib) / "aeris" / "resources" / "config"
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("apps.windows.json", "packages.windows.json"):
            self.copy_file(str(source / name), str(destination / name))
