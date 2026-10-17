import queue
import tempfile
import threading
import wave
from collections import deque
from enum import Enum
from pathlib import Path

from aeris.core.tts_worker import global_tts


class VoiceUnavailableError(RuntimeError):
    pass


class AudioState(str, Enum):
    DISABLED = "disabled"
    INITIALIZING = "initializing"
    WAKE_STANDBY = "wake standby"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    UNAVAILABLE = "unavailable"


class VoiceService:
    COMMAND_PROMPT = (
        "Aeris, Arish, Airis Windows assistant commands. Open Chrome. Open YouTube. "
        "Set volume to fifty percent. Set brightness to sixty percent. "
        "Play music. Pause music. Look at my screen. Explain this error. "
        "Write Python code for an expense tracker. Take a screenshot. "
        "Chrome kholo. Volume kam karo. Screen dekho. Kya error hai? Mute kar do. "
        "Batao ye kaise karna hai. Calendar dikhao. Mail bhejo."
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
        self._preload_thread = None
        self._capture_lock = threading.Lock()
        self.state = AudioState.DISABLED
        self.state_listener = None
        self.input_allowed = lambda: True

    def _set_state(self, state: AudioState, detail: str = ""):
        self.state = state
        if self.state_listener:
            self.state_listener(state, detail)

    def initialize_cached_model(self):
        """Called on the audio owner thread; never downloads assets."""
        self._model_state = "Initializing cached model"
        self._set_state(AudioState.INITIALIZING, "Loading cached speech assets; no download")
        self._get_or_load_model()
        if self._cancel_flag or not self.input_allowed():
            self._model_state = "Initialization interrupted"
            self._set_state(AudioState.INTERRUPTED, "Cached initialization finished after capture was paused")
            return
        self._model_state = "Ready (cached model)"

    def preload_model(self) -> None:
        """Loads the Whisper model in a background thread."""
        def load_task():
            self._model_state = "Loading cached model"
            try:
                self.initialize_cached_model()
                self._model_state = "Ready"
            except Exception:
                self._model_state = "Unavailable — prepare the configured speech model explicitly"
        
        if self._preload_thread and self._preload_thread.is_alive():
            return
        self._preload_thread = threading.Thread(target=load_task, daemon=True, name="Aeris-ASR-load")
        self._preload_thread.start()

    def _get_or_load_model(self):
        with self._model_lock:
            if self._model is not None:
                return self._model
                
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise VoiceUnavailableError("Voice packages are missing.") from exc
                
            compute_type = "float16" if self.device == "cuda" else "int8"
            def load_cached(device, compute_type):
                try:
                    return WhisperModel(self.model_name, device=device, compute_type=compute_type, local_files_only=True)
                except OSError as exc:
                    raise VoiceUnavailableError("Speech model is not available in the local cache. Prepare the configured model explicitly; Aeris will not download it during listening.") from exc
            try:
                self._model = load_cached(self.device, compute_type)
            except RuntimeError as exc:
                if self._cancel_flag or not self.input_allowed():
                    return None
                if self.device == "cpu" or not any(
                    marker in str(exc).lower() for marker in ("cublas", "cudnn", "cuda")
                ):
                    raise
                # CPU fallback
                self.device = "cpu"
                self._model = load_cached("cpu", "int8")
                
            return self._model

    def cancel_recording(self):
        self._cancel_flag = True
        self._set_state(AudioState.INTERRUPTED, "Capture cancelled; an in-progress model call may still finish")

    def begin_session(self):
        """Only the capture owner starts a new session; listen_once never resets cancellation."""
        self._cancel_flag = False

    def listen_once(self) -> str:
        if self._cancel_flag or not self.input_allowed():
            return ""
        if not self._capture_lock.acquire(blocking=False):
            raise VoiceUnavailableError("Microphone already owned by an active capture. Retry after it finishes.")
        try:
            return self._listen_once()
        except VoiceUnavailableError:
            self._set_state(AudioState.UNAVAILABLE, "Check optional audio packages, cached model and microphone permissions")
            raise
        finally:
            self._capture_lock.release()

    def _listen_once(self) -> str:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise VoiceUnavailableError("Voice packages are missing.") from exc

        except OSError as exc:
            raise VoiceUnavailableError("Audio native runtime unavailable. Repair PortAudio/sounddevice; text input remains available.") from exc

        sample_rate = 16_000
        q = queue.Queue(maxsize=80)
        
        def callback(indata, frames, time_info, status):
            if status:
                pass # Can log status
            try:
                q.put_nowait(indata.copy())
            except queue.Full:
                pass

        audio_data = []
        pre_roll = deque(maxlen=3)  # At most 300ms of silence before the first voiced chunk.
        speech_started = False
        silence_frames = 0
        frames_per_buffer = int(sample_rate * 0.1) # 100ms chunks
        max_frames = self.max_record_seconds * sample_rate
        total_frames = 0
        silence_limit = int((self.silence_timeout_ms / 1000.0) * sample_rate)

        try:
            import time
            self._set_state(AudioState.LISTENING, "Local microphone capture; bounded energy endpointing")
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frames_per_buffer, callback=callback):
                last_frame_time = time.monotonic()
                deadline = last_frame_time + self.max_record_seconds + 1
                while not self._cancel_flag and total_frames < max_frames and time.monotonic() < deadline and self.input_allowed():
                    try:
                        chunk = q.get(timeout=0.2)
                    except queue.Empty:
                        if time.monotonic() - last_frame_time > 2.0:
                            raise VoiceUnavailableError("Audio capture timed out (no frames received).")
                        continue
                        
                    last_frame_time = time.monotonic()
                        
                    total_frames += len(chunk)
                    
                    # Calculate RMS energy
                    rms = np.sqrt(np.mean(chunk.astype(np.float32)**2))
                    
                    if rms > self.noise_threshold:
                        if not speech_started:
                            audio_data.extend(pre_roll)
                            pre_roll.clear()
                        speech_started = True
                        silence_frames = 0
                        audio_data.append(chunk)
                    elif speech_started:
                        audio_data.append(chunk)
                        silence_frames += len(chunk)
                        if silence_frames >= silence_limit:
                            break # End of speech detected
                    else:
                        pre_roll.append(chunk)
                            
        except VoiceUnavailableError:
            raise
        except (OSError, getattr(sd, "PortAudioError", OSError)) as exc:
            raise VoiceUnavailableError("Microphone/PortAudio unavailable. Check the selected device and Windows microphone permissions; text input remains available.") from exc

        if self._cancel_flag or not self.input_allowed() or len(audio_data) == 0:
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
                
            if self._model is None:
                self._set_state(AudioState.INITIALIZING, "Loading cached speech model; text input remains available")
            model = self._get_or_load_model()
            if self._cancel_flag or not self.input_allowed():
                return ""
            self._set_state(AudioState.TRANSCRIBING, "Local cached model; inference may not be immediately interruptible")
            
            try:
                segments = list(model.transcribe(
                    str(wav_path),
                    vad_filter=True,
                    language=self.language,
                    initial_prompt=self.COMMAND_PROMPT,
                )[0])
            except RuntimeError as exc:
                if self._cancel_flag or not self.input_allowed():
                    return ""
                if self.device == "cpu" or not any(
                    marker in str(exc).lower() for marker in ("cublas", "cudnn", "cuda")
                ):
                    raise
                # CPU fallback during transcribe if init somehow succeeded but inference fails
                self.device = "cpu"
                self._model = None # Force reload
                model = self._get_or_load_model()
                if self._cancel_flag or not self.input_allowed():
                    return ""
                segments = list(model.transcribe(
                    str(wav_path),
                    vad_filter=True,
                    language=self.language,
                    initial_prompt=self.COMMAND_PROMPT,
                )[0])
                
            return "" if self._cancel_flag or not self.input_allowed() else " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            wav_path.unlink(missing_ok=True)

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        # Ensure TTS worker is started. This is safe to call multiple times.
        global_tts.start()
        global_tts.speak(text)
