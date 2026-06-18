import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


class LLM:
    def __init__(self, model_path: str | None = None):
        self.model_id = model_path or os.getenv(
            "LLM_MODEL_PATH", "meta-llama/Llama-3.1-8B-Instruct"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )

        self.system_prompt = (
            "You are a friendly English speaking tutor. "
            "Keep responses short, natural, and conversational. "
            "Correct the user's English if needed."
        )

    def generate(self, text: str, history: list[dict] | None = None) -> str:
        """
        Generate an assistant response for `text`.

        Args:
            text: The user's current turn.
            history: Optional list of previous chat messages (OpenAI-style
                dicts with "role" and "content"). The caller owns this state.

        Returns:
            The assistant's response text.
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": text})

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=80,
            temperature=0.7,
            do_sample=True,
        )

        # Extract only the generated tokens (skip the input tokens)
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        assistant_response = self.tokenizer.decode(
            generated_ids, skip_special_tokens=True
        ).strip()

        return assistant_response
