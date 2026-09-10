.PHONY: install lint format format-check typecheck test check run migrate

install:
	uv sync --dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest

check: lint format-check typecheck test

run:
	uv run uvicorn app.main:app --app-dir backend --reload

migrate:
	uv run alembic upgrade head

