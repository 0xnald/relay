#!/bin/sh
# Apply pending migrations, then serve the Relay API. Used by the production image.
set -eu
cd "$(dirname "$0")/.."
alembic upgrade head
exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
