import asyncio
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from helpers.config import get_settings
from stores.vectordb.providers.QdrantDBProvider import QdrantDBProvider

async def wipe():
    settings = get_settings()
    raw_password = settings.POSTGRES_PASSWORD.replace('%40', '@')
    encoded_password = urllib.parse.quote_plus(raw_password)
    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{encoded_password}@"
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    
    print("Wiping PostgreSQL...")
    engine = create_async_engine(postgres_conn)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE chat_messages, sessions, chunks, assets, projects CASCADE;"))
    print("Postgres wiped successfully.")

    print("Wiping Qdrant...")
    provider = QdrantDBProvider(
        db_client="localhost",
        qdrant_url=settings.QDRANT_URL,
        qdrant_api_key=settings.QDRANT_API_KEY,
    )
    await provider.connect()
    try:
        await provider.delete_collection("collection_1024_my-project")
        print("Qdrant wiped successfully.")
    except Exception as e:
        print(f"Error wiping Qdrant: {e}")

if __name__ == "__main__":
    asyncio.run(wipe())
