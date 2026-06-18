import os
import io
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel


class STT:
    def __init__(
        self,
        model_name: str | None = None,
        download_root: str | None = None,
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        self.model_name = model_name or os.getenv(
            "WHISPER_MODEL_NAME", "small.en"
        )
        self.download_root = download_root or os.getenv(
            "WHISPER_DOWNLOAD_ROOT", None
        )

        kwargs = {"device": device, "compute_type": compute_type}
        if self.download_root:
            kwargs["download_root"] = self.download_root

        self.model = WhisperModel(self.model_name, **kwargs)

    def transcribe(self, audio_path: str) -> str:
        """File-based transcription (useful for local testing)."""
        segments, _ = self.model.transcribe(
            audio_path,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
        )
        text = "".join([s.text for s in segments]).strip()
        return text if text else ""

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        """
        Transcribe raw audio bytes (e.g. a WAV file sent over a WebSocket).
        The bytes are decoded in-memory via soundfile.
        """
        buffer = io.BytesIO(audio_bytes)
        data, _ = sf.read(buffer, dtype="float32")

        # faster-whisper expects a 1-D numpy array of float32 samples
        if data.ndim > 1:
            data = data.mean(axis=1)

        segments, _ = self.model.transcribe(
            data,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
        )
        text = "".join([s.text for s in segments]).strip()
        return text if text else ""
