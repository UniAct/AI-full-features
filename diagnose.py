"""
Full system diagnostics script — tests all APIs and clears old data.
"""
import os
import sys
import asyncio
import urllib.parse
import requests

sys.path.append(os.path.join(os.getcwd(), 'src'))

from helpers.config import get_settings
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

settings = get_settings()

# ─── 1. Clear old data ───────────────────────────────────────────
async def clear_project():
    pwd = settings.POSTGRES_PASSWORD.replace('%40', '@')
    encoded_pwd = urllib.parse.quote_plus(pwd)
    db_url = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{encoded_pwd}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    engine = create_async_engine(db_url)
    
    print("\n[1/5] Clearing Postgres (chunks + assets for my-project)...")
    try:
        async with engine.begin() as conn:
            r = await conn.execute(text(
                "DELETE FROM chunks WHERE chunk_asset_id IN "
                "(SELECT asset_id FROM assets WHERE asset_project_id='my-project')"
            ))
            print(f"  ✔ Deleted {r.rowcount} chunks.")
            r = await conn.execute(text(
                "DELETE FROM assets WHERE asset_project_id='my-project'"
            ))
            print(f"  ✔ Deleted {r.rowcount} assets.")
    except Exception as e:
        print(f"  ✗ Postgres error: {e}")

    print("[2/5] Clearing Qdrant vector collection...")
    try:
        qdrant = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        collections = await qdrant.get_collections()
        names = [c.name for c in collections.collections]
        for col in names:
            if 'my-project' in col:
                await qdrant.delete_collection(col)
                print(f"  ✔ Deleted collection: {col}")
        if not any('my-project' in n for n in names):
            print("  ℹ No collections found for my-project (already clean).")
    except Exception as e:
        print(f"  ✗ Qdrant error: {e}")

    print("[3/5] Clearing uploaded files...")
    path = "src/assets/files/my-project"
    if os.path.exists(path):
        files = os.listdir(path)
        for f in files:
            try:
                os.remove(os.path.join(path, f))
            except Exception:
                pass
        print(f"  ✔ Deleted {len(files)} file(s).")
    else:
        print("  ℹ No files directory found (already clean).")


# ─── 2. Test all external APIs ───────────────────────────────────
def test_api(name, url, payload, response_key, timeout=30):
    print(f"\n  Testing {name}...")
    print(f"    URL: {url}")
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        val = data.get(response_key, "")
        if val:
            preview = str(val)[:80].replace('\n', ' ')
            print(f"    ✔ OK — response key '{response_key}': {preview}...")
            return True
        else:
            print(f"    ✗ Response missing key '{response_key}'. Got: {list(data.keys())}")
            return False
    except requests.exceptions.Timeout:
        print(f"    ✗ TIMEOUT after {timeout}s — API is too slow or cold-starting")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"    ✗ CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"    ✗ FAILED: {e}")
        return False

def test_all_apis():
    print("\n[4/5] Testing External APIs...")

    # Embedding
    emb_ok = test_api(
        "Embedding API",
        settings.EMBEDDING_API_URL,
        {"input": ["hello world test sentence"]},
        "embeddings",
        timeout=90
    )

    # Generation
    gen_ok = test_api(
        "Generation API",
        settings.GENERATION_API_URL,
        {"prompt": "Say 'hello' in one word.", "max_tokens": 20},
        "response",
        timeout=90
    )

    # MCQ API
    mcq_ok = test_api(
        "MCQ API",
        settings.MCQ_API_URL,
        {"prompt": "Generate 1 MCQ about Python in JSON format.", "max_tokens": 300},
        "response",
        timeout=120
    )

    # Summarization
    summ_ok = test_api(
        "Summarization API",
        settings.SUMMARIZATION_API_URL,
        {"prompt": "Summarize: 'Machine learning is a subset of AI.'", "max_tokens": 50},
        "response",
        timeout=90
    )

    print("\n  API Health Summary:")
    print(f"    Embedding:      {'✔ OK' if emb_ok else '✗ FAILING'}")
    print(f"    Generation:     {'✔ OK' if gen_ok else '✗ FAILING'}")
    print(f"    MCQ:            {'✔ OK' if mcq_ok else '✗ FAILING'}")
    print(f"    Summarization:  {'✔ OK' if summ_ok else '✗ FAILING'}")

    return emb_ok, gen_ok, mcq_ok, summ_ok


async def main():
    print("=" * 60)
    print("  UniAct RAG System — Full Diagnostic")
    print("=" * 60)
    
    await clear_project()
    
    emb_ok, gen_ok, mcq_ok, summ_ok = test_all_apis()
    
    print("\n[5/5] Summary & Recommendations:")
    if not emb_ok:
        print("  ⚠ Embedding API is offline or slow.")
        print("    → The system CANNOT search or index without this.")
        print("    → Check your Modal dashboard that the embedding container is running.")
        print("    → If it's a cold start, wait 30s and try again.")
    if not gen_ok:
        print("  ⚠ Generation API is offline — RAG answers will fail.")
    if not mcq_ok:
        print("  ⚠ MCQ API is offline — Exam generation will fail.")
    if not summ_ok:
        print("  ⚠ Summarization API is offline — Summaries will fail.")
    if emb_ok and gen_ok:
        print("  ✔ Core APIs (Embedding + Generation) are working.")
        print("  ✔ You can now upload your file and it will be indexed correctly.")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
