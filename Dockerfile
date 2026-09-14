# Relay API — production image for the FastAPI backend.
# The AgentCore Intake runtime is packaged separately (see docs/agentcore-deployment.md).
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install locked runtime dependencies first so source changes don't invalidate the layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY backend/app ./backend/app
COPY backend/migrations ./backend/migrations
COPY scripts/start_api.sh ./scripts/start_api.sh
RUN chmod +x ./scripts/start_api.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000
EXPOSE 8000

CMD ["./scripts/start_api.sh"]
