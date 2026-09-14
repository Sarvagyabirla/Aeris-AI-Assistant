import math
import queue
import tempfile
import threading
import wave
from pathlib import Path
from typing import Any, Callable

from aeris.core.tts_worker import global_tts

class VoiceUnavailableError(RuntimeError):
    pass


class VoiceService:
    COMMAND_PROMPT = (
        "Aeris, Arish, Airis Windows assistant commands. Open Chrome. Open YouTube. "
        "Set volume to fifty percent. Set brightness to sixty percent. "
        "Play music. Pause music. Look at my screen. Explain this error. "
        "Write Python code for an expense tracker. Take a screenshot."
    )

    def __init__(
        self,
        model_name: str = "base",
        record_seconds: int = 6,
        device: str = "cpu",
        language: str = "auto",
        silence_timeout_ms: int = 700,
        noise_threshold: int = 500, # A basic RMS energy threshold
    ):
        self.model_name = model_name
        self.max_record_seconds = record_seconds
        self.device = device if device in {"auto", "cpu", "cuda"} else "cpu"
        self.language = None if language in {"", "auto"} else language
        self.silence_timeout_ms = silence_timeout_ms
        self.noise_threshold = noise_threshold
        
        self._model = None
        self._model_lock = threading.Lock()
        self._model_state = "Not loaded"
        self._speaker = None
        self._cancel_flag = False

    def preload_model(self) -> None:
        """Loads the Whisper model in a background thread."""
        def load_task():
            self._model_state = "Downloading/Loading"
            try:
                self._get_or_load_model()
                self._model_state = "Ready"
            except Exception as e:
                self._model_state = f"Failed: {e}"
        
        thread = threading.Thread(target=load_task, daemon=True)
        thread.start()

    def _get_or_load_model(self):
        with self._model_lock:
            if self._model is not None:
                return self._model
                
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise VoiceUnavailableError("Voice packages are missing.") from exc
                
            compute_type = "float16" if self.device == "cuda" else "int8"
            try:
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=compute_type,
                )
            except RuntimeError as exc:
                if self.device == "cpu" or not any(
                    marker in str(exc).lower() for marker in ("cublas", "cudnn", "cuda")
                ):
                    raise
                # CPU fallback
                self.device = "cpu"
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                
            return self._model

    def cancel_recording(self):
        self._cancel_flag = True

    def listen_once(self) -> str:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise VoiceUnavailableError("Voice packages are missing.") from exc

        self._cancel_flag = False
        sample_rate = 16_000
        q = queue.Queue()
        
        def callback(indata, frames, time_info, status):
            if status:
                pass # Can log status
            q.put(indata.copy())

        audio_data = []
        speech_started = False
        silence_frames = 0
        frames_per_buffer = int(sample_rate * 0.1) # 100ms chunks
        max_frames = self.max_record_seconds * sample_rate
        total_frames = 0
        silence_limit = int((self.silence_timeout_ms / 1000.0) * sample_rate)

        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frames_per_buffer, callback=callback):
                while not self._cancel_flag and total_frames < max_frames:
                    try:
                        chunk = q.get(timeout=0.2)
                    except queue.Empty:
                        continue
                        
                    audio_data.append(chunk)
                    total_frames += len(chunk)
                    
                    # Calculate RMS energy
                    rms = np.sqrt(np.mean(chunk.astype(np.float32)**2))
                    
                    if rms > self.noise_threshold:
                        speech_started = True
                        silence_frames = 0
                    elif speech_started:
                        silence_frames += len(chunk)
                        if silence_frames >= silence_limit:
                            break # End of speech detected
                            
        except Exception as exc:
            raise VoiceUnavailableError(f"Microphone error: {exc}")

        if self._cancel_flag or len(audio_data) == 0:
            return ""

        recording = np.concatenate(audio_data, axis=0)
        
        # If no significant speech was detected
        if not speech_started:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            wav_path = Path(handle.name)
            
        try:
            with wave.open(str(wav_path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(sample_rate)
                output.writeframes(recording.tobytes())
                
            model = self._get_or_load_model()
            
            try:
                segments, _ = model.transcribe(
                    str(wav_path),
                    vad_filter=True,
                    language=self.language,
                    initial_prompt=self.COMMAND_PROMPT,
                )
            except RuntimeError as exc:
                if self.device == "cpu" or not any(
                    marker in str(exc).lower() for marker in ("cublas", "cudnn", "cuda")
                ):
                    raise
                # CPU fallback during transcribe if init somehow succeeded but inference fails
                self.device = "cpu"
                self._model = None # Force reload
                model = self._get_or_load_model()
                segments, _ = model.transcribe(
                    str(wav_path),
                    vad_filter=True,
                    language=self.language,
                    initial_prompt=self.COMMAND_PROMPT,
                )
                
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            wav_path.unlink(missing_ok=True)

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        # Ensure TTS worker is started. This is safe to call multiple times.
        global_tts.start()
        global_tts.speak(text)
