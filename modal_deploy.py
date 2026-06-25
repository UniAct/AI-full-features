import modal

# 1. تجهيز البيئة السحابية وتثبيت المكتبات اللي السيستم بتاعك بيعتمد عليها
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        # Web framework
        "fastapi[standard]",
        "uvicorn",
        "starlette",
        # Database
        "sqlalchemy",
        "asyncpg",
        "alembic",
        # Vector DB
        "qdrant-client",
        # LangChain — core + community (needed for document loaders)
        "langchain",
        "langchain-community",
        "langchain-core",
        # PDF parsing
        "pymupdf",
        # HTTP requests
        "requests",
        "aiofiles",
        # Pydantic
        "pydantic",
        "pydantic-settings",
        # AI / LLM providers
        "cohere",
        "openai",
        # Monitoring
        "prometheus-client",
        # Utilities
        "tqdm",
        "python-multipart",
        "python-dotenv",
    )
    .add_local_dir("./src", remote_path="/root/src")
)

app = modal.App("uniact-rag-backend-v2")

# Persistent network file system for real-time file sharing between concurrent web requests
files_volume = modal.NetworkFileSystem.from_name("uniact-files-nfs", create_if_missing=True)

# 2. رفع فولدر الكود وقراءة ملف الـ .env
@app.function(
    image=image,
    secrets=[modal.Secret.from_dotenv("./src/.env")],
    timeout=900,
    network_file_systems={"/root/src/assets/files": files_volume},
)
@modal.asgi_app()
def fastapi_app():
    import sys
    import os
    # /root/src is already on the mount, add it so Python can find the modules
    sys.path.insert(0, "/root/src")

    # Ensure the files directory exists on the volume
    os.makedirs("/root/src/assets/files", exist_ok=True)

    # Correct import — no "src." prefix because /root/src is already in sys.path
    from main import app as my_fastapi_app
    return my_fastapi_app