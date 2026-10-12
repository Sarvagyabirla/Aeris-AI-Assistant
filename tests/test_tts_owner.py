import sys
import threading
import time
from types import SimpleNamespace

from aeris.core.tts_worker import TTSWorker


def test_engine_operations_stay_on_owner_thread(monkeypatch):
    operations = []
    entered = threading.Event()
    class Engine:
        def record(self, name):
            operations.append((name, threading.get_ident()))
        def setProperty(self, *args):
            self.record("rate")
        def startLoop(self, *args):
            self.record("start")
        def endLoop(self):
            self.record("end")
        def stop(self):
            self.record("stop")
        def isBusy(self):
            self.record("busy")
            return False
        def say(self, *args):
            self.record("say")
            entered.set()
        def iterate(self):
            self.record("iterate")
    engine = Engine()
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(init=lambda: engine))
    monkeypatch.setitem(sys.modules, "pythoncom", SimpleNamespace(
        CoInitialize=lambda: engine.record("COM-init"), CoUninitialize=lambda: engine.record("COM-close"),
        PumpWaitingMessages=lambda: engine.record("COM-pump")))
    worker = TTSWorker()
    assert worker.speak("fixture")
    assert entered.wait(2)
    worker.set_rate(190)
    time.sleep(0.03)
    worker.stop()
    assert worker.shutdown(2)
    assert worker.error is None
    assert {identity for _, identity in operations} == {worker._thread.ident}
    assert worker._thread.ident != threading.get_ident()