import os
import io
import uuid

import torch
import numpy as np
import soundfile as sf
from omnivoice import OmniVoice

# ---------------------------------------------------------------------------
# Voice registry – maps a short voice_id to its reference audio file path
# and corresponding reference transcript.
#
# To add a new voice:
#   1. Place the .wav file in this directory (or at a path accessible at
#      runtime — paths can be absolute).
#   2. Add an entry below.
#   3. Rebuild the Docker image so the new file is baked in.
#
# When voice_id=None is passed, synthesizers fall back to the raw
# ref_audio / ref_text arguments for backward compatibility.
# ---------------------------------------------------------------------------
VOICES: dict[int, dict[str, str]] = {
    1: {
        "ref_audio": "ref-aud.wav",
        "ref_text": "Hi, This is alice, how are you doing today?",
    },
    2: {
        "ref_audio": "ref-aud2.wav",
        "ref_text": "ශ්‍රී ලංකාව තුල ආයෝජනය සහ නව ව්‍යාපාරික අවස්තා ගවේශනය කිරීමට පැමිනෙන්නැයි",
    },
}


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
        voice_id: int | None = None,
    ) -> np.ndarray | bytes | str:
        """
        Synthesize text to audio.

        Args:
            text: Text to speak.
            out_path: Optional path to write a WAV file for debugging. If None,
                no file is written.
            ref_audio: Optional reference audio for voice cloning (overridden
                by *voice_id* if provided).
            ref_text: Optional reference text (overridden by *voice_id* if
                provided).
            return_wav_bytes: If True (default), return in-memory WAV bytes.
                If False, return the raw numpy audio array.
            voice_id: If set, look up ref_audio/ref_text from the VOICES
                registry instead of using the explicit *ref_audio* / *ref_text*
                arguments.

        Returns:
            WAV bytes, raw audio array, or the output file path if out_path
            was provided and return_wav_bytes is False.
        """
        # Resolve ref_audio / ref_text from voice_id if given
        if voice_id is not None:
            voice = VOICES.get(voice_id)
            if voice is None:
                raise ValueError(
                    f"Unknown voice_id={voice_id}. "
                    f"Available: {list(VOICES)}"
                )
            ref_audio = voice["ref_audio"]
            ref_text = voice["ref_text"]

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
        voice_id: int | None = None,
    ) -> np.ndarray | bytes | str:
        """
        Convenience wrapper that namespaces any debug WAV file by session ID
        so concurrent sessions never race on a fixed output path.
        """
        out_path = f"/tmp/tts_output_{session_id}_{uuid.uuid4().hex}.wav"

        # Resolve ref_audio / ref_text from voice_id if given, otherwise
        # fall back to the explicit args (which themselves default to
        # voice 1's values for backward compatibility).
        if voice_id is not None:
            voice = VOICES.get(voice_id)
            if voice is None:
                raise ValueError(
                    f"Unknown voice_id={voice_id}. "
                    f"Available: {list(VOICES)}"
                )
            ref_audio = voice["ref_audio"]
            ref_text = voice["ref_text"]
        else:
            if ref_audio is None:
                ref_audio = "ref-aud.wav"
            if ref_text is None:
                ref_text = "Hi, This is alice, how are you doing today?"

        return self.synthesize(
            text=text,
            out_path=out_path,
            ref_audio=ref_audio,
            ref_text=ref_text,
            return_wav_bytes=return_wav_bytes,
        )
