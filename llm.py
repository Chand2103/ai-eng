from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class LLM:
    def __init__(self):
        self.model_id = "meta-llama/Llama-3.1-8B-Instruct"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True
        )

        self.system_prompt = (
            "You are a friendly English speaking tutor. "
            "Keep responses short, natural, and conversational. "
            "Correct the user's English if needed."
        )

    def generate(self, text: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text}
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=80,
            temperature=0.7,
            do_sample=True
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return response