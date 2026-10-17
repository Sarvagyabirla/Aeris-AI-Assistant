"""Owned-thread speech cleanup fixtures; no OS speech or COM calls."""
import sys
import threading
from types import SimpleNamespace

import pytest

from aeris.core.tts_worker import TTSWorker


class Engine:
    def __init__(self, failure):
        self.failure = failure
        self.failed = False
        self.ready = threading.Event()
        self.calls = []

    def record(self, name):
        self.calls.append((name, threading.get_ident()))
        if name == self.failure and not self.failed:
            self.failed = True
            raise RuntimeError("fixture private speech backend failure")

    def setProperty(self, *_):
        self.record("property")

    def startLoop(self, *_):
        self.record("start")
        self.ready.set()

    def isBusy(self):
        return False

    def iterate(self):
        pass

    def stop(self):
        self.record("stop")

    def endLoop(self):
        self.record("end")

    def say(self, *_):
        self.record("say")


@pytest.mark.parametrize("failure", ["stop", "end"])
def test_native_cleanup_failure_is_truthful_and_retry_stays_on_owner_thread(monkeypatch, failure):
    engine = Engine(failure)
    com = []
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: engine))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: com.append(("init", threading.get_ident())),
        CoUninitialize=lambda: com.append(("uninit", threading.get_ident())),
        PumpWaitingMessages=lambda: None))
    worker = TTSWorker()
    worker.start()
    assert engine.ready.wait(1)
    try:
        assert not worker.shutdown(timeout=0.1), "A dead thread alone does not prove native cleanup succeeded"
        assert worker.cleanup_pending
        assert worker._engine is engine
        assert worker.speak("Must not start after failed cleanup") is False
        assert worker.shutdown(timeout=1)
        assert not worker.cleanup_pending and worker._engine is None
        assert not worker.speaking.is_set()
        owner_threads = {thread for _, thread in engine.calls}
        assert len(owner_threads) == 1 and threading.get_ident() not in owner_threads
        if sys.platform == "win32":
            assert [name for name, _ in com] == ["init", "uninit"]
            assert {thread for _, thread in com} == owner_threads
        assert worker.error == "RuntimeError"
        assert "private" not in str(worker.error)
    finally:
        # Explicitly wake/retry the retained fixture owner if an assertion fails.
        engine.failed = True
        worker.shutdown(timeout=1)


def test_engine_initialization_failure_balances_com_without_false_cleanup_failure(monkeypatch):
    com = []

    def broken_init():
        raise RuntimeError("fixture initialization failure")

    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=broken_init))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: com.append("init"), CoUninitialize=lambda: com.append("uninit")))
    worker = TTSWorker()
    worker.start()
    worker._thread.join(1)
    assert worker.shutdown(timeout=1)
    if sys.platform == "win32":
        assert com == ["init", "uninit"]
    assert worker._engine is None and not worker.speaking.is_set()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows COM ownership fixture")
def test_com_initialization_failure_does_not_uninitialize_an_unowned_apartment(monkeypatch):
    calls = []

    def failed_initialize():
        calls.append("init")
        raise RuntimeError("fixture COM initialization failed")

    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: pytest.fail("COM initialization failed")))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=failed_initialize, CoUninitialize=lambda: calls.append("uninit")))
    worker = TTSWorker()
    worker.start()
    worker._thread.join(1)
    assert worker.shutdown(timeout=1)
    assert calls == ["init"] and worker.error == "RuntimeError"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows COM ownership fixture")
def test_uncertain_com_release_cannot_create_an_engine_on_another_thread(monkeypatch):
    engine = Engine(None)
    calls = []

    def failed_release():
        calls.append(threading.get_ident())
        raise RuntimeError("fixture uncertain COM release")

    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: engine))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=failed_release, PumpWaitingMessages=lambda: None))
    worker = TTSWorker()
    worker.start()
    assert engine.ready.wait(1)
    assert not worker.shutdown(timeout=1)
    assert worker.cleanup_pending and not worker._thread.is_alive()
    assert not worker.shutdown(timeout=0.01) and worker.start() is False
    assert worker.speak("No second owner") is False
    assert len(calls) == 1 and calls[0] != threading.get_ident()
    assert worker._engine is None and not worker.speaking.is_set()


def test_utterance_waiting_to_publish_cannot_survive_shutdown(monkeypatch):
    engine = Engine(None)
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: engine))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None, PumpWaitingMessages=lambda: None))
    worker = TTSWorker()
    started, release = threading.Event(), threading.Event()
    start = worker.start
    published = []

    def paused_start():
        ready = start()
        started.set()
        assert release.wait(1)
        return ready

    monkeypatch.setattr(worker, "start", paused_start)
    publisher = threading.Thread(target=lambda: published.append(worker.speak("Fixture stale speech")))
    publisher.start()
    try:
        assert started.wait(1) and engine.ready.wait(1)
        assert worker.shutdown(timeout=1)
        release.set()
        publisher.join(1)
        assert published == [False] and worker._queue.empty()
        assert not any(name == "say" for name, _ in engine.calls)
    finally:
        release.set()
        publisher.join(1)
        worker.shutdown(timeout=1)


def test_failed_initialization_discards_queued_speech_before_clean_retry(monkeypatch):
    entered, release, spoken = threading.Event(), threading.Event(), threading.Event()
    engine = Engine(None)
    utterances = []
    attempts = []

    def initialize():
        attempts.append(True)
        if len(attempts) == 1:
            entered.set()
            assert release.wait(1)
            raise RuntimeError("fixture first initialization failure")
        return engine

    def say(text):
        utterances.append(text)
        spoken.set()

    engine.say = say
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=initialize))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None, PumpWaitingMessages=lambda: None))
    worker = TTSWorker()
    try:
        assert worker.speak("Fixture stale speech")
        assert entered.wait(1)
        release.set()
        worker._thread.join(1)
        assert worker._queue.empty(), "Speech from a failed owner must not be replayed by its replacement"
        assert worker.speak("Fixture current speech")
        assert spoken.wait(1)
        assert utterances == ["Fixture current speech"]
    finally:
        release.set()
        worker.shutdown(timeout=1)


def test_worker_runtime_failure_rejects_publication_during_teardown(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    engine = Engine(None)

    def failed_iterate():
        raise RuntimeError("fixture runtime failure")

    def stopping():
        entered.set()
        assert release.wait(1)

    engine.iterate = failed_iterate
    engine.stop = stopping
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: engine))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None, PumpWaitingMessages=lambda: None))
    worker = TTSWorker()
    worker.start()
    try:
        assert entered.wait(1)
        assert worker.speak("Fixture speech during teardown") is False
        assert worker._queue.empty()
    finally:
        release.set()
        worker.shutdown(timeout=1)
