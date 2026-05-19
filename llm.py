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
        
        # Conversation history for memory management
        self.conversation_history = []

    def generate(self, text: str, use_history: bool = False) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Add conversation history if enabled
        if use_history:
            messages.extend(self.conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": text})

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

        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the assistant's response (after the last <|assistant|> token)
        assistant_response = self._extract_assistant_response(full_response)
        
        # Append to history for next turns
        self.conversation_history.append({"role": "user", "content": text})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        return assistant_response
    
    def _extract_assistant_response(self, full_response: str) -> str:
        """Extract only the assistant's response from the full decoded output."""
        # Find the last occurrence of assistant marker and extract response after it
        if "<|assistant|>" in full_response:
            parts = full_response.split("<|assistant|>")
            if len(parts) > 1:
                response = parts[-1].strip()
                # Remove end markers if present
                response = response.replace("<|end_header_id|>", "").strip()
                return response
        return full_response.strip()