import asyncio
import os
import asyncpg
from dotenv import load_dotenv

async def remove_column():
    load_dotenv("src/.env")
    db_url = os.getenv("DATABASE_URL")
    print(f"Connecting to {db_url}")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute('ALTER TABLE assets DROP COLUMN IF EXISTS asset_group;')
        print("Dropped asset_group column.")
    except Exception as e:
        print(f"Error dropping column: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(remove_column())
