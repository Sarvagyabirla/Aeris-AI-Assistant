import os
import sys
import threading
import time

import pytest

from aeris.core.process_runner import run_owned
from aeris.state import CancellationToken


def test_owned_process_drains_bounded_output():
    result = run_owned([sys.executable, "-c", "print('x'*100000)"], timeout=5, output_limit=1024)
    assert result.returncode == 0 and result.reason is None
    assert len(result.output.encode()) <= 1024
    assert result.cleanup_complete


def test_owned_process_cancellation_reaps_child():
    token = CancellationToken()
    timer = threading.Timer(0.1, token.cancel)
    timer.start()
    try:
        result = run_owned([sys.executable, "-c", "import time;time.sleep(10)"], timeout=5, token=token)
    finally:
        timer.join()
    assert result.reason == "cancelled"
    assert result.returncode is not None and result.cleanup_complete


def test_owned_process_timeout_and_missing_executable():
    result = run_owned([sys.executable, "-c", "import time;time.sleep(10)"], timeout=0.1)
    assert result.reason == "timeout" and result.cleanup_complete
    assert run_owned(["aeris-nonexistent-fixture-executable"]).reason == "launch_failed"


def test_parent_exit_does_not_hide_running_child_or_inherited_pipe(tmp_path):
    psutil = pytest.importorskip("psutil", reason="Process-tree fixture needs psutil for cleanup")
    pid_file = tmp_path / "child.pid"
    script = (
        "import subprocess,sys,pathlib; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(5)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid))"
    )
    start = time.monotonic()
    try:
        result = run_owned([sys.executable, "-c", script, str(pid_file)], timeout=0.5)
        assert result.reason == "timeout", "A parent exit must not be reported as completed while its child owns the pipe"
        assert time.monotonic() - start < 3
        child_pid = int(pid_file.read_text())
        if os.name == "nt" and result.ownership == "process":
            assert not result.cleanup_complete  # Optional Windows APIs absent: honest weak boundary.
        else:
            assert result.cleanup_complete
            assert not psutil.pid_exists(child_pid) or psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE
    finally:
        if pid_file.exists():
            try:
                child = psutil.Process(int(pid_file.read_text()))
                child.terminate()
                child.wait(timeout=2)
            except psutil.Error:
                pass


@pytest.mark.skipif(os.name != "nt", reason="Windows suspended-child gate")
def test_cancel_before_windows_resume_never_executes_child(tmp_path, monkeypatch):
    pytest.importorskip("win32job")
    from aeris.core.process_runner import _WindowsJob
    token = CancellationToken()
    marker = tmp_path / "must-not-exist.txt"
    original = _WindowsJob.attach_and_resume
    def cancel_before_resume(self, process, token=None):
        token.cancel()
        original(self, process, token)
    monkeypatch.setattr(_WindowsJob, "attach_and_resume", cancel_before_resume)
    result = run_owned([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('late')", str(marker)], token=token)
    assert result.reason == "cancelled" and result.cleanup_complete
    assert not marker.exists()
