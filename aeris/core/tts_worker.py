import queue
import threading
import time

class TTSWorker:
    def __init__(self, rate: int = 175):
        self._queue = queue.Queue()
        self._thread = None
        self._stop_event = threading.Event()
        self._rate = rate
        self._engine = None
        self.muted = False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        # Re-initialize the queue so it isn't blocked by previous sentinel
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._queue.put(None) # Sentinel

    def set_rate(self, rate: int):
        self._rate = rate
        if self._engine:
            # We must set property on the worker thread, but pyttsx3 is mostly thread-sensitive.
            # Easiest way is to restart the thread if rate changes.
            self.stop()
            time.sleep(0.1)
            self.start()

    def speak(self, text: str):
        if self.muted or not text.strip():
            return
        self._queue.put(text)

    def _worker_loop(self):
        import pythoncom
        import pyttsx3
        # Initialize COM on this background thread safely
        pythoncom.CoInitialize()
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            
            while not self._stop_event.is_set():
                try:
                    text = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                    
                if text is None or self._stop_event.is_set():
                    break
                    
                try:
                    self._engine.say(text[:2_000])
                    self._engine.runAndWait()
                except Exception as e:
                    print(f"TTS Error: {e}")
                finally:
                    self._queue.task_done()
        finally:
            self._engine = None
            pythoncom.CoUninitialize()

global_tts = TTSWorker()
