"""Owned, non-shell native commands with bounded output and cooperative cancellation.

Windows extras enable a kill-on-close Job Object, assigned before the child is resumed.
Not a sandbox. UAC/service-launched external installers may escape ownership; callers
must still treat interrupted consequential operations as uncertain.
"""

import math
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
    ownership: str = "process"


class _WindowsJob:
    """Own normal child descendants before any child code can execute."""
    def __init__(self):
        import psutil
        import win32api
        import win32job
        import win32process
        self.api, self.jobs, self.processes, self.psutil = win32api, win32job, win32process, psutil
        self.handle = win32job.CreateJobObject(None, "")
        try:
            limits = win32job.QueryInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation)
            limits["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation, limits)
        except Exception:
            self.close()
            raise

    def attach_and_resume(self, process, token=None):
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE; do not depend on Popen's private handle.
        handle = self.api.OpenProcess(0x0100 | 0x0001, False, process.pid)
        try:
            self.jobs.AssignProcessToJobObject(self.handle, handle)
        finally:
            handle.Close()
        threads = self.psutil.Process(process.pid).threads()
        if len(threads) != 1:
            raise RuntimeError("Suspended process did not expose one initial thread")
        thread = self.api.OpenThread(0x0002, False, threads[0].id)  # THREAD_SUSPEND_RESUME
        try:
            def resume():
                return self.processes.ResumeThread(thread)
            previous_count = token.commit(resume) if token else resume()
            if previous_count != 1:
                raise RuntimeError("Initial thread was not suspended")
        finally:
            thread.Close()

    def active(self):
        return self.jobs.QueryInformationJobObject(self.handle, self.jobs.JobObjectBasicAccountingInformation)["ActiveProcesses"]

    def terminate(self):
        self.jobs.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle is not None:
            self.handle.Close()
            self.handle = None


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
    if (not isinstance(command, (list, tuple)) or not command or len(command) > 64
            or any(not isinstance(arg, str) or "\x00" in arg for arg in command)
            or sum(len(arg) for arg in command) > 32_000
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 3600
            or type(output_limit) is not int or not 1 <= output_limit <= 1_048_576):
        return ProcessOutcome(None, "", "invalid_process_arguments")
    if token and token.is_cancelled:
        return ProcessOutcome(None, "", "cancelled")
    deadline = time.monotonic() + timeout
    job = None
    if os.name == "nt":
        try:
            job = _WindowsJob()
        except ImportError:
            pass  # Portable text installation: explicitly weaker process ownership.
        except Exception:
            return ProcessOutcome(None, "", "ownership_unavailable")
    ownership = "windows_job" if job else "process_group" if os.name != "nt" else "process"
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, cwd=cwd, shell=False,
            creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) | (0x00000004 if job else 0)) if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
    except OSError:
        if job:
            job.close()
        return ProcessOutcome(None, "", "launch_failed")
    if job:
        try:
            if token:
                token.raise_if_cancelled()
            job.attach_and_resume(process, token)
        except Exception:
            job.close()  # Assigned suspended children are killed before executing.
            cleaned = _terminate_owned(process)
            process.stdout.close()
            return ProcessOutcome(process.poll(), "", "cancelled" if token and token.is_cancelled else "ownership_unavailable",
                                  cleaned, ownership)
    tail = bytearray()
    lock = threading.Lock()
    def drain():
        try:
            while chunk := process.stdout.read1(4096):
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
    try:
        while True:
            try:
                descendants_active = bool(job and job.active())
            except Exception:
                reason = "ownership_failed"
                cleanup = False
                descendants_active = False
            if process.poll() is not None and not reader.is_alive() and not descendants_active:
                break
            if token and token.is_cancelled:
                reason = "cancelled"
            elif time.monotonic() >= deadline:
                reason = "timeout"
            if reason:
                if job:
                    try:
                        job.terminate()
                    except Exception:
                        cleanup = False
                cleanup = _terminate_owned(process) and cleanup
                break
            time.sleep(0.02)
    finally:
        if job:
            job.close()
    reader.join(timeout=0.5)
    if reader.is_alive() and reason is None:
        reason = "cleanup_incomplete"
    with lock:
        output = bytes(tail).decode("utf-8", errors="replace")
    return ProcessOutcome(process.poll(), output, reason, cleanup and not reader.is_alive(), ownership)
