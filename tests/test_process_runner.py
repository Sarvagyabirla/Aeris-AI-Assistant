import sys
import threading

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