.PHONY: install dev redis migrate seed worker test lint format demo

install:
	uv sync --frozen

dev:
	uv run uvicorn app.main:app --reload

redis:
	docker compose up -d redis

migrate:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed_demo.py

worker:
	uv run arq app.workers.worker.WorkerSettings

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

demo:
	uv run python scripts/run_happy_path.py
