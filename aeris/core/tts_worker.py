import queue
import threading
import time


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
        self.last_output_at = 0.0
        self.playback_generation = 0
        self._cleanup_pending = threading.Event()
        self._cleanup_retry = threading.Event()
        self._cleanup_complete = threading.Event()
        self._cleanup_complete.set()

    @property
    def cleanup_pending(self) -> bool:
        return self._cleanup_pending.is_set()

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return not self._stop_event.is_set() and not self.cleanup_pending
            if not self._cleanup_complete.is_set():
                # A failed COM release cannot be moved to another owner thread.
                return False
            self._stop_event.clear()
            self._cleanup_retry.clear()
            self._cleanup_complete.clear()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="Aeris-speech")
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            self._interrupt_and_drain()

    def _interrupt_and_drain(self):
        self._interrupt.set()
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def shutdown(self, timeout=2):
        with self._lock:
            self._interrupt_and_drain()
            self._stop_event.set()
            self._cleanup_retry.set()
            owner = self._thread
        if owner:
            if threading.current_thread() is owner:
                return False
            owner.join(timeout)
        return not owner or (not owner.is_alive() and self._cleanup_complete.is_set())

    def set_rate(self, rate: int):
        self._rate = rate

    def speak(self, text: str, token=None):
        if self.muted or not text.strip():
            return
        if not self.start():
            return False
        # Publication and shutdown's drain share a short lock; native engine
        # calls never hold it, so Stop cannot wait behind speech SDK work.
        with self._lock:
            if self._stop_event.is_set() or self.cleanup_pending or not self._thread or not self._thread.is_alive():
                return False
            try:
                self._queue.put_nowait((text, token))
                return True
            except queue.Full:
                return False

    def _worker_loop(self):
        com = None
        com_initialized = False
        loop_started = False
        try:
            import os

            import pyttsx3
            if os.name == "nt":
                import pythoncom
                com = pythoncom
                com.CoInitialize()
                com_initialized = True
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
                        if (not self.muted and not self._stop_event.is_set() and not self._interrupt.is_set()
                                and not (active_token and active_token.is_cancelled)):
                            self.playback_generation += 1
                            self.speaking.set()
                            self._engine.say(text[:500])
                self._engine.iterate()
                if self.speaking.is_set():
                    self.last_output_at = time.monotonic()
                if com:
                    com.PumpWaitingMessages()
                self._stop_event.wait(0.01)
        except Exception as exc:
            self.error = type(exc).__name__
        finally:
            # Retiring an owner also retires its pending utterances. Publish
            # shutdown under the queue lock before any native teardown call.
            with self._lock:
                self._stop_event.set()
                self._interrupt_and_drain()
            # Native cleanup stays on this thread. A failed stop/endLoop retains
            # its engine and COM apartment until an explicit shutdown retry.
            while self._engine is not None:
                self._cleanup_retry.clear()
                failures = []
                try:
                    self._engine.stop()
                except Exception as exc:
                    failures.append(type(exc).__name__)
                if loop_started:
                    try:
                        self._engine.endLoop()
                    except Exception as exc:
                        failures.append(type(exc).__name__)
                    else:
                        loop_started = False
                if not failures:
                    self._engine = None
                    break
                self.error = failures[0]
                self._cleanup_pending.set()
                if self.speaking.is_set():
                    self.last_output_at = time.monotonic()
                self.speaking.clear()
                self._cleanup_retry.wait()
            try:
                if com_initialized:
                    com.CoUninitialize()
            except Exception as exc:
                # Its release outcome is uncertain. Keep cleanup incomplete;
                # never create another engine or retry COM on the wrong thread.
                self.error = type(exc).__name__
                self._cleanup_pending.set()
            else:
                self._cleanup_pending.clear()
                self._cleanup_complete.set()
            finally:
                if self.speaking.is_set():
                    self.last_output_at = time.monotonic()
                self.speaking.clear()

global_tts = TTSWorker()
