# ============================================================
# uniAct RAG App - Standalone Dockerfile
# Build:   docker build -t uniact-rag-app .
# Run:     docker run -p 8000:8000 --env-file src/.env uniact-rag-app
# ============================================================

# Use the official uv + Python 3.11 base image (fast dependency management)
FROM ghcr.io/astral-sh/uv:0.10.9-python3.11-trixie

# ---- System Dependencies ----------------------------------------
# Required for: lxml, Pillow, PyMuPDF, psycopg2, and docling[easyocr]
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libavif-dev \
    pkg-config \
    libjpeg-dev \
    gcc \
    unzip \
    zip \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Working Directory ------------------------------------------
WORKDIR /app

# ---- Install Python Dependencies --------------------------------
# Copy dependency files first so this layer is cached unless deps change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Copy Application Source ------------------------------------
# Copied after deps so code changes don't bust the dependency cache.
COPY src/ .

# ---- Alembic Setup ----------------------------------------------
# Ensure the alembic migrations directory exists inside the container.
RUN mkdir -p /app/models/db_schemes/ragapp/
COPY docker/ragapp/alembic.ini /app/models/db_schemes/ragapp/alembic.ini

# ---- Entrypoint Script ------------------------------------------
# The entrypoint runs DB migrations (alembic upgrade head) before
# starting the server. Migrations need the DB to be reachable at
# runtime, not at build time, so this cannot be a RUN step.
COPY docker/ragapp/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---- Expose Port ------------------------------------------------
EXPOSE 8000

# ---- Startup ----------------------------------------------------
# ENTRYPOINT runs migrations; CMD starts the ASGI server.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
