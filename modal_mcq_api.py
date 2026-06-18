"""
Modal MCQ API - Dedicated Multiple Choice Question generator.
Uses fine-tuned LoRA model: mohamedashraff22/qwen2.5-3b-mcq-lora
Base model: Qwen/Qwen2.5-3B-Instruct with MCQ-specific LoRA adapter.
"""

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers",
        "accelerate",
        "sentencepiece",
        "peft",          # Required for LoRA adapter loading
        "fastapi[standard]",
    )
)

app = modal.App("rag-mcq-api")

BASE_MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
LORA_ADAPTER_ID = "mohamedashraff22/qwen2.5-3b-mcq-lora"

SYSTEM_PROMPT = (
    "You are an expert exam question generator. "
    "You generate multiple choice questions strictly in JSON format. "
    "Always return ONLY a valid JSON object. No extra text, no markdown."
)


@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=120,
)
class MCQApi:
    @modal.enter()
    def load(self):
        """Load base model + LoRA adapter once when container starts."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        import torch

        print(f"Loading base model {BASE_MODEL_ID}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            BASE_MODEL_ID, trust_remote_code=True
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

        print(f"Applying LoRA adapter {LORA_ADAPTER_ID}...")
        self.model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_ID)
        self.model.eval()
        print("MCQ model with LoRA adapter loaded successfully!")

    @modal.fastapi_endpoint(method="POST")
    def generate(self, request: dict):
        """
        Generate MCQ questions in JSON format using fine-tuned LoRA model.
        Accepts: {"prompt": "...", "max_tokens": 1500}
        Returns: {"response": "..."}
        """
        import torch

        prompt = request.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided"}

        max_new_tokens = request.get("max_tokens", 1500)

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                )

            generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
            response_text = self.tokenizer.decode(
                generated_ids, skip_special_tokens=True
            )

            return {"response": response_text.strip()}

        except Exception as e:
            return {"error": f"MCQ generation failed: {str(e)}"}
