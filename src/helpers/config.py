"""
Configuration module for the RAG App.
This module defines the Settings class for managing application configuration
via environment variables and .env files.
"""

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from typing import List, Optional


class Settings(BaseSettings):
    """
    Application settings class.
    Inherits from pydantic_settings.BaseSettings to automatically load
    configuration from environment variables or a .env file.
    """

    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNCK_SIZE: int

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    # خلينا المفاتيح القديمة اختيارية عشان السيستم ميضربش إيرور لو مش موجودة
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # الروابط الجديدة الخاصة بموديلاتك على Modal
    GENERATION_API_URL: Optional[str] = None
    EMBEDDING_API_URL: Optional[str] = None
    MCQ_API_URL: Optional[str] = None
    SUMMARIZATION_API_URL: Optional[str] = None

    GENERATION_MODEL_ID_LITERAL: Optional[List[str]] = None
    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    INPUT_DAFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DAFAULT_MAX_TOKENS: Optional[int] = None
    GENERATION_DAFAULT_TEMPERATURE: Optional[float] = None

    VECTOR_DB_BACKEND_LITERAL: Optional[List[str]] = None
    VECTOR_DB_BACKEND: str
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: Optional[str] = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    # Qdrant Cloud connection
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    # ضفنا extra="ignore" عشان لو ملف الـ .env فيه متغيرات زيادة السيستم يتجاهلها وميعملش إيرور
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    """
    Retrieves the application settings instance.
    
    Returns:
        Settings: The application configuration settings.
    """
    return Settings()