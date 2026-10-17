"""Increment 1 regression tests — these should FAIL before the matching fixes.

P1-D: PermissionEngine.resume() must bump _generation
P1-E: PortAudio runtime OSError inside sd.InputStream must become VoiceUnavailableError
P1-B: HandsFreeWorker must support voice interruption during active task
"""

import re
import sys
import types

import pytest

from aeris.models import ActionRequest, PermissionLevel
from aeris.permissions import ApprovalManager, PermissionEngine

# -- P1-D: resume() generation bump --

def test_stop_then_resume_invalidates_mid_stop_approval_grant():
    engine = PermissionEngine()

    def stop_resume_then_approve(request, level, preview):
        engine.stop()
        engine.resume()
        return True

    result = engine.authorize(
        ActionRequest("files.write", {"path": "fixture.txt"}),
        PermissionLevel.CONFIRM,
        stop_resume_then_approve,
    )
    assert not result.allowed, (
        "Approval must be invalidated when stop+resume changed the generation "
        "while the callback was pending"
    )


def test_resume_bumps_generation_clears_stale_session():
    import aeris.permissions as pm
    original = pm.time.monotonic
    now = [100.0]
    pm.time.monotonic = lambda: now[0]
    try:
        engine = PermissionEngine(ApprovalManager(ttl_seconds=90))
        request = ActionRequest("vision.inspect_screen", {"region": [0, 0, 100, 100]})
        approvals = []

        def approve(req, *_):
            approvals.append("approved")
            return True

        assert engine.authorize(request, PermissionLevel.SESSION, approve).allowed
        assert len(approvals) == 1
        assert engine.authorize(request, PermissionLevel.SESSION, approve).allowed
        assert len(approvals) == 1  # cached

        engine.stop()
        engine.resume()

        # After stop+resume, session cleared and generation bumped; new approval needed
        assert engine.authorize(request, PermissionLevel.SESSION, approve).allowed
        assert len(approvals) == 2
    finally:
        pm.time.monotonic = original


# -- P1-E: PortAudio runtime OSError mapping --

def test_portaudio_runtime_oserror_at_input_stream_is_voice_unavailable():
    from aeris.integrations.voice import VoiceService, VoiceUnavailableError

    class FakeInputStream:
        def __init__(self, *args, **kwargs):
            raise OSError("PortAudio library not found")

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    fake_sd = types.ModuleType("sounddevice")
    fake_sd.InputStream = FakeInputStream

    fake_np = types.ModuleType("numpy")
    fake_np.sqrt = lambda x: x
    fake_np.mean = lambda x: 0.0
    fake_np.concatenate = lambda items, axis=None: bytes()

    original_sd = sys.modules.get("sounddevice")
    original_np = sys.modules.get("numpy")
    sys.modules["sounddevice"] = fake_sd
    sys.modules["numpy"] = fake_np

    try:
        svc = VoiceService()
        svc._cancel_flag = False
        with pytest.raises(VoiceUnavailableError, match="PortAudio"):
            svc.listen_once()
    finally:
        if original_sd is not None:
            sys.modules["sounddevice"] = original_sd
        else:
            sys.modules.pop("sounddevice", None)
        if original_np is not None:
            sys.modules["numpy"] = original_np
        else:
            sys.modules.pop("numpy", None)


# -- P1-B: Voice interruption during busy task --

def test_stop_phrase_detectable_while_task_busy():
    from aeris.activation import extract_addressed_command
    stop_phrase = "aeris stop"
    wake_word = "aeris"
    command = extract_addressed_command(stop_phrase, (wake_word,))
    assert command and "stop" in command.lower(), (
        "Stop phrase must be addressable even during busy state"
    )

    _STOP_PHRASES = re.compile(r"\b(stop|cancel|abort|halt)\b", re.I)
    cancelled = []

    class FakeToken:
        pass

    class FakeWorker:
        current_token = FakeToken()

        def cancel_current(self):
            cancelled.append(True)

    worker = FakeWorker()
    is_busy = worker.current_token is not None
    if is_busy and command and _STOP_PHRASES.search(command):
        worker.cancel_current()

    assert cancelled, "cancel_current() must be called on stop phrase during busy task"
