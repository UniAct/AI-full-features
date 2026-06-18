"""
Custom Modal provider module for handling text generation and embedding.
Supports both plain-text Modal endpoints and OpenAI-compatible (structured messages) endpoints.
"""

from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenAIEnums
import requests
import os
import logging
from typing import List, Union, Optional


class OpenAIProvider(LLMInterface):
    """
    Provider implementation that calls custom Modal LLM endpoints.
    Falls back gracefully if URLs are missing.
    """

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        embedding_url: Optional[str] = None,
        generation_fallback_url: Optional[str] = None,
        default_input_max_characters: int = 100000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.7,
    ):
        # Prefer URLs passed from settings over raw env-var lookups
        self.generation_url = api_url or os.getenv("GENERATION_API_URL")
        self.embedding_url = embedding_url or os.getenv("EMBEDDING_API_URL")
        # Fallback generation URL (e.g. the summarization endpoint which is also a Qwen model)
        self.generation_fallback_url = generation_fallback_url or os.getenv("SUMMARIZATION_API_URL")

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.last_error = None

        self.enums = OpenAIEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str) -> str:
        return text[: self.default_input_max_characters].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: List[dict] = [],
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """
        Generates text using the Modal Generation API.

        Tries plain-text prompt first (Modal/vLLM endpoints),
        then structured messages (OpenAI-compatible),
        then a fallback generation URL if configured.
        Timeout is 180s to accommodate Modal cold starts.
        """
        if not self.generation_url and not self.generation_fallback_url:
            self.last_error = "GENERATION_API_URL is not set in .env"
            self.logger.error(self.last_error)
            return None

        # Build structured messages list (system + history + current prompt)
        messages = list(chat_history) if chat_history else []
        messages.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        )

        plain_prompt = "\n".join(
            [msg["content"] for msg in messages if isinstance(msg, dict) and "content" in msg]
        )
        plain_payload = {"prompt": plain_prompt}

        # --- Attempt 1: plain-text prompt to primary URL ---
        if self.generation_url:
            try:
                response = requests.post(
                    self.generation_url, json=plain_payload, timeout=180
                )
                if response.ok:
                    data = response.json()
                    result = data.get("response") or data.get("text") or data.get("content")
                    if result:
                        return result
                else:
                    self.logger.warning(
                        f"Primary generation URL returned HTTP {response.status_code}"
                    )
            except Exception as e:
                self.logger.warning(f"Primary generation URL failed: {e}")

        # --- Attempt 2: structured messages to primary URL ---
        if self.generation_url:
            structured_payload = {"messages": messages}
            try:
                response = requests.post(
                    self.generation_url, json=structured_payload, timeout=180
                )
                if response.ok:
                    data = response.json()
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                    result = data.get("response") or data.get("text") or data.get("content")
                    if result:
                        return result
            except Exception as e:
                self.logger.warning(f"Structured messages to primary URL failed: {e}")

        # --- Attempt 3: fallback generation URL (e.g. summarization endpoint) ---
        if self.generation_fallback_url and self.generation_fallback_url != self.generation_url:
            self.logger.info("Trying fallback generation URL...")
            try:
                response = requests.post(
                    self.generation_fallback_url, json=plain_payload, timeout=180
                )
                if response.ok:
                    data = response.json()
                    result = data.get("response") or data.get("text") or data.get("content")
                    if result:
                        return result
            except Exception as e:
                self.last_error = str(e)
                self.logger.error(f"Fallback generation URL also failed: {e}")
                return None

        self.last_error = "All generation attempts failed"
        return None

    def embed_text(
        self, text: Union[str, List[str]], document_type: str = None
    ) -> Optional[List[List[float]]]:
        """
        Generates embeddings using the Modal Embedding API.
        """
        if not self.embedding_url:
            self.last_error = "EMBEDDING_API_URL is not set in .env"
            self.logger.error(self.last_error)
            return None

        if isinstance(text, str):
            text = [text]

        # NOTE: The Modal embedding API expects key 'input' not 'texts'
        payload = {"input": text}
        try:
            response = requests.post(self.embedding_url, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            return data.get("embeddings")
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Embedding API failed: {e}")
            return None

    def construct_prompt(self, prompt: str, role: str) -> dict:
        return {"role": role, "content": prompt}
