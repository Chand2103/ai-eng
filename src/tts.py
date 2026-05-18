import torch
import numpy as np
import soundfile as sf
from transformers import AutoProcessor, AutoModel

class TTS:
    def __init__(self):
        self.model_id = "k2-fsa/OmniVoice"

        self.processor = AutoProcessor.from_pretrained(self.model_id)

        self.model = AutoModel.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype=torch.float16
        )

        self.sample_rate = 24000

    def synthesize(self, text: str, out_path="output.wav"):
        inputs = self.processor(text=text, return_tensors="pt").to("cuda")

        with torch.no_grad():
            try:
                audio = self.model.generate(**inputs)
            except Exception:
                audio = self.model(text)

        audio = audio.cpu().numpy()

        audio = audio / (np.max(np.abs(audio)) + 1e-8)

        sf.write(out_path, audio, self.sample_rate)

        return out_path