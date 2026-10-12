import queue
import threading


class TTSWorker:
    def __init__(self, rate: int = 175):
        self._queue = queue.Queue(maxsize=16)
        self._thread = None
        self._stop_event = threading.Event()
        self._rate = rate
        self._engine = None
        self.muted = False
        self.speaking = threading.Event()
        self._interrupt = threading.Event()
        self._lock = threading.Lock()
        self.error = None

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="Aeris-speech")
            self._thread.start()

    def stop(self):
        self._interrupt.set()
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def shutdown(self, timeout=2):
        self.stop()
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout)
        return not self._thread or not self._thread.is_alive()

    def set_rate(self, rate: int):
        self._rate = rate

    def speak(self, text: str, token=None):
        if self.muted or not text.strip():
            return
        self.start()
        try:
            self._queue.put_nowait((text, token))
            return True
        except queue.Full:
            return False

    def _worker_loop(self):
        com = None
        loop_started = False
        try:
            import os

            import pyttsx3
            if os.name == "nt":
                import pythoncom
                com = pythoncom
                com.CoInitialize()
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.startLoop(False)
            loop_started = True
            active_token = None
            rate = self._rate
            
            while not self._stop_event.is_set():
                if self._interrupt.is_set() or self.muted or (active_token and active_token.is_cancelled):
                    self._engine.stop()
                    self._interrupt.clear()
                    active_token = None
                if rate != self._rate:
                    rate = self._rate
                    self._engine.setProperty("rate", rate)
                if not self._engine.isBusy():
                    self.speaking.clear()
                    try:
                        text, active_token = self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        if not self.muted and not (active_token and active_token.is_cancelled):
                            self.speaking.set()
                            self._engine.say(text[:500])
                self._engine.iterate()
                if com:
                    com.PumpWaitingMessages()
                self._stop_event.wait(0.01)
        except Exception as exc:
            self.error = type(exc).__name__
        finally:
            if self._engine:
                self._engine.stop()
                if loop_started:
                    self._engine.endLoop()
            self._engine = None
            self.speaking.clear()
            if com:
                com.CoUninitialize()

global_tts = TTSWorker()
