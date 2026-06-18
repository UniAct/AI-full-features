#!/bin/sh
# this will not run wile bild , it will run after building and connect to backend network.

set -e # if i got an error in any line stop execution and donot continue.

echo "Running database migrations..."
cd /app/models/db_schemes/ragapp/
uv run alembic upgrade head
cd /app

# THIS IS THE MAGIC LINE: Execute the CMD from the Dockerfile
exec "$@"