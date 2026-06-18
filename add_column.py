from sqlalchemy import create_engine, text
import os

url = "postgresql://postgres.zekcpkxrbnhruxapggxv:Ma01276760898%40@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
engine = create_engine(url)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE assets ADD COLUMN asset_group VARCHAR;"))
        conn.commit()
        print("Column asset_group added successfully.")
    except Exception as e:
        print(f"Error: {e}")
