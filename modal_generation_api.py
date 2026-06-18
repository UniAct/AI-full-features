"""
Modal Generation API - Lightweight Qwen2.5 deployment using transformers.
Avoids vLLM (which crashes due to flashinfer CUDA JIT issues on Modal Starter).
Uses transformers + torch directly with a smaller model for reliability.
"""

import modal

# Build the image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers",
        "accelerate",
        "sentencepiece",
        "fastapi[standard]",
    )
)

app = modal.App("rag-generation-api-v2")

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"


@app.cls(
    image=image,
    gpu="T4",  # Cheapest GPU, sufficient for 1.5B model
    timeout=300,
    scaledown_window=120,  # Keep warm for 2 min to avoid cold starts
)
class GenerationAPI:
    @modal.enter()
    def load(self):
        """Load model once when container starts."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        print(f"Loading model {MODEL_ID}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        print("Model loaded successfully!")

    @modal.fastapi_endpoint(method="POST")
    def generate(self, request: dict):
        """
        Generate text from a prompt.
        Accepts: {"prompt": "your text here"}
        Returns: {"response": "generated text"}
        """
        import torch

        prompt = request.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided"}

        max_new_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)

        try:
            # Build chat messages format for Qwen
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ]

            # Apply chat template
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                )

            # Decode only the new tokens (skip the input prompt)
            generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
            response_text = self.tokenizer.decode(
                generated_ids, skip_special_tokens=True
            )

            return {"response": response_text.strip()}

        except Exception as e:
            return {"error": f"Generation failed: {str(e)}"}
