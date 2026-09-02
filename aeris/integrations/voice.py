from __future__ import annotations

import tempfile
import wave
from pathlib import Path


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
        model_name: str = "small",
        record_seconds: int = 6,
        device: str = "cpu",
        language: str = "en",
    ):
        self.model_name = model_name
        self.record_seconds = record_seconds
        self.device = device if device in {"auto", "cpu", "cuda"} else "cpu"
        self.language = None if language in {"", "auto"} else language
        self._model = None
        self._speaker = None

    def listen_once(self) -> str:
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise VoiceUnavailableError(
                "Voice packages are missing. Install Aeris with the voice extra."
            ) from exc

        sample_rate = 16_000
        recording = sd.rec(
            int(self.record_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        if not np.any(recording):
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
                compute_type = "float16" if self.device == "cuda" else "int8"
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=compute_type,
                )
            try:
                segments, _ = self._model.transcribe(
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
                self.device = "cpu"
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                segments, _ = self._model.transcribe(
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
        try:
            import pyttsx3
        except ImportError as exc:
            raise VoiceUnavailableError("Text-to-speech is not installed.") from exc
        if self._speaker is None:
            self._speaker = pyttsx3.init()
            self._speaker.setProperty("rate", 175)
        self._speaker.say(text[:2_000])
        self._speaker.runAndWait()
