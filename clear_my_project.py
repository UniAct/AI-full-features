import os
import sys
import asyncio
import shutil
import urllib.parse

sys.path.append(os.path.join(os.getcwd(), 'src'))

from helpers.config import get_settings
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def clear_db():
    settings = get_settings()
    
    # 1. Clear Postgres
    print("Clearing Postgres...")
    pwd = settings.POSTGRES_PASSWORD.replace('%40', '@')
    encoded_pwd = urllib.parse.quote_plus(pwd)
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{encoded_pwd}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    engine = create_async_engine(db_url)
    
    try:
        async with engine.begin() as conn:
            # Delete chunks first
            await conn.execute(text("DELETE FROM chunks WHERE chunk_asset_id IN (SELECT asset_id FROM assets WHERE asset_project_id IN (SELECT project_id FROM projects WHERE project_id = 'my-project'))"))
            # Delete assets
            await conn.execute(text("DELETE FROM assets WHERE asset_project_id IN (SELECT project_id FROM projects WHERE project_id = 'my-project')"))
            print("Postgres cleared for 'my-project'.")
    except Exception as e:
        print(f"Postgres delete error: {e}")
    
    # 2. Clear Qdrant
    print("Clearing Qdrant...")
    try:
        qdrant = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        await qdrant.delete_collection("my-project")
        print("Qdrant collection deleted.")
    except Exception as e:
        print(f"Qdrant delete error: {e}")
        
    # 3. Clear Files
    print("Clearing Files...")
    path = "src/assets/files/my-project"
    if os.path.exists(path):
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))
        print("Files deleted.")
            
    print("Done!")

if __name__ == "__main__":
    asyncio.run(clear_db())
