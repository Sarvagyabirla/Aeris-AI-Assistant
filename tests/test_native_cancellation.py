import subprocess

from aeris.models import ActionResult
from aeris.state import CancellationToken
from aeris.tools.downloads import DownloadTools
from aeris.tools.packages import PackageTools


def test_cancelled_winget_does_not_launch(tmp_path, monkeypatch):
    tools = PackageTools((tmp_path,))
    monkeypatch.setattr(tools, "_require_windows", lambda: None)
    monkeypatch.setattr("aeris.tools.packages.shutil.which", lambda _: "fixture-winget")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("late process")))
    token = CancellationToken()
    token.cancel()
    result = tools._run_winget(["list"], token=token)
    assert not result.success and result.error == "cancelled"


def test_install_exit_alone_is_not_verified_presence(tmp_path, monkeypatch):
    tools = PackageTools((tmp_path,))
    calls = []
    def run(arguments, **kwargs):
        calls.append(arguments)
        if arguments[0] == "install":
            return ActionResult(True, "Process completed.", data={"output": ""})
        return ActionResult(False, "Not found.", error="winget_exit_1")
    monkeypatch.setattr(tools, "_run_winget", run)
    result = tools.install({"package": "Fixture.Package"})
    assert not result.success
    assert result.error == "installation_unverified"
    assert calls[1][:3] == ["list", "--id", "Fixture.Package"]


def test_cancelled_scan_does_not_launch(tmp_path, monkeypatch):
    token = CancellationToken()
    token.cancel()
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("late scan")))
    assert DownloadTools._defender_scan(tmp_path / "fixture.txt", token=token) == "cancelled"