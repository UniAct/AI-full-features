"""
Main application module for the RAG App.
This module initializes the FastAPI application, sets up database connections,
LLM providers, and includes project routes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <-- تمت إضافة الاستيراد هنا
from routes import base, data, nlp, session, study
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Import metrics setup
from utils.metrics import setup_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown logic.
    """
    # Startup logic
    settings = get_settings()

    # Configure PostgreSQL connection
    # Decode literal %40 → @ first, then re-encode so the URL is valid for asyncpg
    raw_password = settings.POSTGRES_PASSWORD.replace('%40', '@')
    encoded_password = urllib.parse.quote_plus(raw_password)
    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{encoded_password}@"
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )

    # Initialize SQLAlchemy async engine
    app.db_engine = create_async_engine(postgres_conn)

    # Initialize session maker
    app.db_client = sessionmaker(
        app.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Initialize LLM and VectorDB provider factories
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings, db_client=app.db_client
    )

    # Initialize generation client
    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    # Initialize embedding client
    app.embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    # Initialize vector database client
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await app.vectordb_client.connect()

    # Initialize template parser
    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    yield

    # Shutdown logic
    await app.db_engine.dispose()
    await app.vectordb_client.disconnect()


app = FastAPI(lifespan=lifespan)

# <-- تمت إضافة إعدادات الـ CORS هنا مباشرة بعد تعريف التطبيق -->
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
setup_metrics(app)

# Include application routers
app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(session.session_router)
app.include_router(study.study_router)