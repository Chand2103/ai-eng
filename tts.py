import os
import io
import uuid

import torch
import numpy as np
import soundfile as sf
from omnivoice import OmniVoice


class TTS:
    def __init__(self, model_path: str | None = None):
        self.model_id = model_path or os.getenv(
            "OMNIVOICE_MODEL_PATH", "k2-fsa/OmniVoice"
        )

        print("Loading OmniVoice...")
        self.model = OmniVoice.from_pretrained(
            self.model_id,
            device_map="cuda:0",  # IMPORTANT
            dtype=torch.float16,
        )
        self.sample_rate = 24000
        print("OmniVoice loaded")

    def synthesize(
        self,
        text: str,
        out_path: str | None = None,
        ref_audio=None,
        ref_text=None,
        return_wav_bytes: bool = True,
    ) -> np.ndarray | bytes | str:
        """
        Synthesize text to audio.

        Args:
            text: Text to speak.
            out_path: Optional path to write a WAV file for debugging. If None,
                no file is written.
            ref_audio: Optional reference audio for voice cloning.
            ref_text: Optional reference text.
            return_wav_bytes: If True (default), return in-memory WAV bytes.
                If False, return the raw numpy audio array.

        Returns:
            WAV bytes, raw audio array, or the output file path if out_path
            was provided and return_wav_bytes is False.
        """
        print(f"TTS: {text}")

        with torch.no_grad():
            audio = self.model.generate(
                text=text,
                ref_audio=ref_audio,
                ref_text=ref_text,
            )

        # OmniVoice returns list of arrays
        audio = audio[0]
        audio = np.asarray(audio)
        audio = audio / (np.max(np.abs(audio)) + 1e-8)

        if out_path:
            sf.write(out_path, audio, self.sample_rate)

        if return_wav_bytes:
            buffer = io.BytesIO()
            sf.write(buffer, audio, self.sample_rate, format="WAV")
            return buffer.getvalue()

        if out_path:
            return out_path

        return audio

    def synthesize_for_session(
        self,
        session_id: str,
        text: str,
        ref_audio=None,
        ref_text=None,
        return_wav_bytes: bool = True,
    ) -> np.ndarray | bytes | str:
        """
        Convenience wrapper that namespaces any debug WAV file by session ID
        so concurrent sessions never race on a fixed output path.
        """
        out_path = f"/tmp/tts_output_{session_id}_{uuid.uuid4().hex}.wav"
        return self.synthesize(
            text=text,
            out_path=out_path,
            ref_audio="ref-aud.wav",
            ref_text="Hi, This is alice, how are you doing today?",
            return_wav_bytes=return_wav_bytes,
        )
