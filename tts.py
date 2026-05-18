import torch
import numpy as np
import soundfile as sf
from omnivoice import OmniVoice

class TTS:
    def __init__(self):
        print("Loading OmniVoice...")

        self.model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map="cuda:0",   # IMPORTANT
            dtype=torch.float16
        )

        self.sample_rate = 24000

        print("OmniVoice loaded")

    def synthesize(self, text: str, out_path="output.wav",
                   ref_audio=None, ref_text=None):

        print(f"TTS: {text}")

        with torch.no_grad():
            audio = self.model.generate(
                text=text,
                ref_audio=ref_audio,   # optional
                ref_text=ref_text      # optional
            )

        # OmniVoice returns list of arrays
        audio = audio[0]

        audio = np.asarray(audio)
        audio = audio / (np.max(np.abs(audio)) + 1e-8)

        sf.write(out_path, audio, self.sample_rate)

        return out_path