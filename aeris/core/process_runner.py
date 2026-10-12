"""Owned, non-shell native commands with bounded output and cooperative cancellation.

Not a sandbox or a Windows Job Object. Detached/elevated installers may escape ownership;
callers must treat interrupted consequential operations as uncertain.
"""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessOutcome:
    returncode: int | None
    output: str
    reason: str | None = None
    cleanup_complete: bool = True


def _terminate_owned(process):
    descendants = []
    try:
        import psutil
        descendants = psutil.Process(process.pid).children(recursive=True)
        for child in reversed(descendants):
            try:
                child.terminate()
            except psutil.Error:
                pass
    except (ImportError, OSError):
        pass
    except Exception:
        # Process may have exited before enumeration. Never search by app name.
        pass
    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            return False
    except (OSError, ProcessLookupError):
        pass
    if descendants:
        import psutil
        _, alive = psutil.wait_procs(descendants, timeout=0.3)
        for child in alive:
            try:
                child.kill()
            except psutil.Error:
                pass
        _, alive = psutil.wait_procs(alive, timeout=0.3)
        return not alive and process.poll() is not None
    return process.poll() is not None


def run_owned(command, *, timeout=60, token=None, cwd=None, output_limit=16_384):
    """Drain output while polling; never persist or print arguments/output by default."""
    if token and token.is_cancelled:
        return ProcessOutcome(None, "", "cancelled")
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, cwd=cwd, shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
    except OSError:
        return ProcessOutcome(None, "", "launch_failed")
    tail = bytearray()
    lock = threading.Lock()
    def drain():
        try:
            while chunk := process.stdout.read(4096):
                with lock:
                    tail.extend(chunk)
                    del tail[:-output_limit]
        except (OSError, ValueError):
            pass
        finally:
            process.stdout.close()
    reader = threading.Thread(target=drain, daemon=True, name="Aeris-process-output")
    reader.start()
    reason = None
    cleanup = True
    while process.poll() is None:
        if token and token.is_cancelled:
            reason = "cancelled"
        elif time.monotonic() >= deadline:
            reason = "timeout"
        if reason:
            cleanup = _terminate_owned(process)
            break
        time.sleep(0.02)
    reader.join(timeout=0.5)
    with lock:
        output = bytes(tail).decode("utf-8", errors="replace")
    return ProcessOutcome(process.poll(), output, reason, cleanup and not reader.is_alive())