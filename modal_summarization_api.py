"""
Modal Summarization API - Dedicated chapter/text summarizer.
Uses Qwen2.5-1.5B-Instruct model optimised for long-form summarization.
"""

import modal

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

app = modal.App("rag-summarization-api")

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

SYSTEM_PROMPT = (
    "You are an expert academic summarizer. "
    "You read provided text and produce clear, concise, well-structured summaries "
    "that capture the key concepts, main ideas, and important details."
)


@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=120,
)
class SummarizationApi:
    @modal.enter()
    def load(self):
        """Load model once when container starts."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        print(f"Loading Summarization model {MODEL_ID}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        print("Summarization model loaded successfully!")

    @modal.fastapi_endpoint(method="POST")
    def generate(self, request: dict):
        """
        Summarize provided text.
        Accepts: {"prompt": "...", "max_tokens": 1024}
        Returns: {"response": "summary text...", "summary": "summary text..."}
        """
        import torch

        prompt = request.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided"}

        max_new_tokens = request.get("max_tokens", 1024)

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
                    temperature=0.5,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                )

            generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
            response_text = self.tokenizer.decode(
                generated_ids, skip_special_tokens=True
            )

            result = response_text.strip()
            # Return both keys so the backend can pick either one
            return {"response": result, "summary": result}

        except Exception as e:
            return {"error": f"Summarization failed: {str(e)}"}
