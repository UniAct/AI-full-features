FROM ghcr.io/astral-sh/uv:0.10.9-python3.11-trixie

# the working directory in this image.
WORKDIR /app

# Install additional system dependencies for lxml and other packages , -y: always yes.
RUN apt-get update && apt-get install -y \
    build-essential \
    libavif-dev pkg-config \
    libjpeg-dev \
    gcc unzip zip \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
    # && rm -rf /var/lib/apt/lists/* : optional as when i install all this those lists are written with them and i dont want them at all (to maek the image more smaller).

COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev


# copy the whole code this time as its the more changeble than the requirments.txt so i put it bellow it as when i change somethign in the code the upper parts of docker file will remain unchanged.
COPY src/ .

# Create directory structure for Alembic, -p: if existed continue.
RUN mkdir -p /app/models/db_schemes/ragapp/

COPY docker/ragapp/alembic.ini /app/models/db_schemes/ragapp/alembic.ini

# very tricky, as its here is in the step of building, it hasnt conntct to "backend" network yet, so it cant see what is pgvector at all , so if i run this it will get an error: RUN alembic upgrade head, so i will use extearnal script
COPY docker/ragapp/entrypoint.sh /entrypoint.sh
# chnge mode to execution mode.
RUN chmod +x /entrypoint.sh

# ENTRYPOINT, CMD: run after builidng, RUN: run while building.
ENTRYPOINT ["/entrypoint.sh"]

# Command to run the application, as you increase workers, handle requests will be faster, but it will take more memmory, if i use --reload it will only use one worker.
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]