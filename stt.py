from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf
from pathlib import Path

class STT:
    def __init__(self, model_name="small.en"):
        self.model = WhisperModel(
            model_name,
            device="cuda",
            compute_type="float16"
        )

    def transcribe(self, audio_path: str) -> str:
        segments, _ = self.model.transcribe(
            audio_path,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False
        )

        text = "".join([s.text for s in segments]).strip()
        return text if text else ""