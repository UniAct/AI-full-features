"""
LLM provider factory module for creating specific LLM provider instances.
"""

from .LLMEnums import LLMEnums
from .providers import OpenAIProvider, CoHereProvider
from typing import Optional, Union, Any


class LLMProviderFactory:
    """
    Factory class to instantiate LLM providers based on configuration.
    """

    def __init__(self, config: Any):
        """
        Initializes the factory with application configuration.
        """
        self.config = config

    def create(self, provider: str) -> Optional[Union[OpenAIProvider, CoHereProvider]]:
        """
        Creates an instance of the specified LLM provider.
        
        Args:
            provider (str): The name/ID of the provider to create.
            
        Returns:
            Optional[Union[OpenAIProvider, CoHereProvider]]: The provider instance or None if not supported.
        """
        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                # Use GENERATION_API_URL (Modal endpoint) as primary; fall back to OPENAI_API_URL
                api_url=self.config.GENERATION_API_URL or self.config.OPENAI_API_URL,
                embedding_url=self.config.EMBEDDING_API_URL,
                generation_fallback_url=self.config.SUMMARIZATION_API_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key=self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        return None