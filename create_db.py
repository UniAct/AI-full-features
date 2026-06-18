import os
import sys
import asyncio
import importlib
import urllib.parse

# تعريف مسار الأكواد للسيستم
sys.path.append(os.path.join(os.getcwd(), 'src'))

from helpers.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine

async def init_db():
    print("⏳ Preparing database connection...")
    settings = get_settings()
    
    # تظبيط الباسورد عشان يقبل الاتصال
    pwd = settings.POSTGRES_PASSWORD.replace('%40', '@')
    encoded_pwd = urllib.parse.quote_plus(pwd)
    
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{encoded_pwd}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    engine = create_async_engine(db_url)
    
    modules = ['project', 'asset', 'datachunk', 'session', 'chat_message']
    metadata = None
    
    print("⏳ Scanning database models...")
    for mod_name in modules:
        try:
            mod = importlib.import_module(f"models.db_schemes.ragapp.schemes.{mod_name}")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                # البحث عن الموديل عشان ناخد منه الـ metadata الخاصة ببناء الجداول
                if hasattr(attr, '__tablename__') and hasattr(attr, 'metadata'):
                    metadata = attr.metadata
        except Exception as e:
            print(f"Warning: Could not load {mod_name}: {e}")
            
    if metadata is None:
        print("❌ Could not find database models. Make sure you are in the root directory.")
        return
        
    print("⏳ Building tables in Supabase...")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        
    print("✅ All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
