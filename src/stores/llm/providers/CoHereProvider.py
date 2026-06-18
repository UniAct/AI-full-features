"""
CoHere provider module for handling text generation and embedding.
This module integrates with the CoHere API.
"""

from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnum
import cohere
import logging
from typing import List, Union, Optional


class CoHereProvider(LLMInterface):
    """
    Provider implementation for CoHere's LLM services.
    """

    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):
        """
        Initializes the CoHere provider with API credentials and default settings.
        
        Args:
            api_key (str): CoHere API key.
            default_input_max_characters (int): Maximum characters allowed for input processing.
            default_generation_max_output_tokens (int): Default token limit for generations.
            default_generation_temperature (float): Default temperature for generations.
        """
        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        # Only initialise the CoHere client when a real key is present
        if api_key and api_key.strip():
            self.client = cohere.Client(api_key=self.api_key)
        else:
            self.client = None
            self.logger = logging.getLogger(__name__)
            self.logger.warning(
                "COHERE_API_KEY is missing or empty — CoHere provider will not function."
            )

        self.enums = CoHereEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        """
        Sets the model ID to be used for text generation.
        """
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        """
        Sets the model ID and dimension size for embeddings.
        """
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str) -> str:
        """
        Preprocesses input text, including truncation based on character limits.
        """
        return text[: self.default_input_max_characters].strip()

    def generate_text(
        self, 
        prompt: str, 
        chat_history: List[dict] = [], 
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generates text using the configured CoHere model.
        
        Args:
            prompt (str): The input prompt or query.
            chat_history (List[dict]): Previous conversation turns.
            max_output_tokens (Optional[int]): Token limit for this specific call.
            temperature (Optional[float]): Temperature for this specific call.
            
        Returns:
            Optional[str]: Generated text content or None on error.
        """
        if not self.client:
            self.logger.error("CoHere client not initialized.")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model ID not set.")
            return None
        
        tokens = max_output_tokens or self.default_generation_max_output_tokens
        temp = temperature or self.default_generation_temperature

        try:
            response = self.client.chat(
                model=self.generation_model_id,
                chat_history=chat_history,
                message=self.process_text(prompt),
                temperature=temp,
                max_tokens=tokens
            )

            if response and response.text:
                return response.text
        except Exception as e:
            self.logger.error(f"Failed to generate text using CoHere: {e}")

        return None
    
    def embed_text(self, text: Union[str, List[str]], document_type: str = None) -> Optional[List[List[float]]]:
        """
        Generates embeddings for the provided text(s).
        
        Args:
            text (Union[str, List[str]]): Singular text or list of texts to embed.
            document_type (str): The context type for the embedding (QUERY or DOCUMENT).
            
        Returns:
            Optional[List[List[float]]]: List of embedding vectors or None on error.
        """
        if not self.client:
            self.logger.error("CoHere client not initialized.")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        if not self.embedding_model_id:
            self.logger.error("Embedding model ID not set.")
            return None
        
        # Determine input type for CoHere embedding
        input_type = CoHereEnums.DOCUMENT
        if document_type == DocumentTypeEnum.QUERY:
            input_type = CoHereEnums.QUERY

        try:
            response = self.client.embed(
                model=self.embedding_model_id,
                texts=[self.process_text(t) for t in text],
                input_type=input_type,
                embedding_types=['float'],
            )

            if response and response.embeddings and response.embeddings.float:
                return [f for f in response.embeddings.float]
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings using CoHere: {e}")

        return None
    
    def construct_prompt(self, prompt: str, role: str) -> dict:
        """
        Constructs a prompt dictionary in the format expected by CoHere.
        """
        return {
            "role": role,
            "text": prompt,
        }