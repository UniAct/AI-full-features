"""
Modal Embedding API - Qwen3 Embedding model
Deploys a fast, reliable embedding endpoint on Modal.
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

app = modal.App("rag-embedding-api")

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"


@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=120,
)
class EmbeddingAPI:
    @modal.enter()
    def load(self):
        """Load model once when container starts."""
        from transformers import AutoModel, AutoTokenizer
        import torch

        print(f"Loading embedding model {MODEL_ID}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        self.model.eval()
        print("Embedding model loaded!")

    @modal.fastapi_endpoint(method="POST")
    def embed(self, request: dict):
        """
        Embed a list of texts.
        Accepts: {"input": ["text1", "text2", ...]}
        Returns: {"embeddings": [[...], [...]]}
        """
        import torch

        texts = request.get("input") or request.get("texts") or request.get("inputs") or []
        if not texts:
            return {"embeddings": [], "error": "No input texts provided"}

        if isinstance(texts, str):
            texts = [texts]

        try:
            # Tokenize
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.model.device)

            with torch.no_grad():
                outputs = self.model(**encoded)

            # Mean pooling
            token_embeddings = outputs.last_hidden_state
            attention_mask = encoded["attention_mask"]
            input_mask_expanded = (
                attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            )
            sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            embeddings = sum_embeddings / sum_mask

            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            return {"embeddings": embeddings.cpu().tolist()}

        except Exception as e:
            return {"embeddings": [], "error": f"Embedding failed: {str(e)}"}
