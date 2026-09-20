.PHONY: help install test test-backend test-frontend lint lint-backend lint-frontend \
        format format-check dev-backend dev-worker dev-frontend infra-up infra-down \
        migrate seed demo prod-build prod-up prod-down

help:
	@echo "Paytm ONE Vyapar (Vyapaar Commander) - Monorepo Commands"
	@echo "=========================================================="
	@echo "Setup:"
	@echo "  make install        Install both backend (uv) and frontend (pub) dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           Run all backend and frontend tests"
	@echo "  make test-backend   Run backend pytest suite"
	@echo "  make test-frontend  Run Flutter test suite"
	@echo "  make lint           Run backend ruff and Flutter analyze"
	@echo "  make lint-backend   Run ruff linter on backend"
	@echo "  make lint-frontend  Run flutter analyze on client"
	@echo "  make format         Auto-format backend and Flutter code"
	@echo "  make format-check   Check code formatting without modifying"
	@echo ""
	@echo "Local Development:"
	@echo "  make infra-up       Start local PostgreSQL & Redis via Docker"
	@echo "  make infra-down     Stop local Docker infrastructure"
	@echo "  make migrate        Apply PostgreSQL schema migrations (Alembic)"
	@echo "  make seed           Populate database with deterministic demo data"
	@echo "  make dev-backend    Start FastAPI dev server with hot reload"
	@echo "  make dev-worker     Start ARQ background worker for Outbox events"
	@echo "  make dev-frontend   Launch Flutter app on default connected device"
	@echo "  make demo           Execute full credential-free happy path workflow"
	@echo ""
	@echo "Production Deployment:"
	@echo "  make prod-build     Build production Docker images"
	@echo "  make prod-up        Start production stack (Nginx, API, DB, Redis)"
	@echo "  make prod-down      Stop production containers"

install:
	@echo "--> Installing backend dependencies..."
	cd backend && uv sync --frozen
	@echo "--> Installing Flutter dependencies..."
	cd vyapar && flutter pub get

test: test-backend test-frontend

test-backend:
	@echo "--> Running backend pytest suite..."
	cd backend && uv run pytest

test-frontend:
	@echo "--> Running Flutter test suite..."
	cd vyapar && flutter test

lint: lint-backend lint-frontend

lint-backend:
	@echo "--> Running ruff check on backend..."
	cd backend && uv run ruff check .

lint-frontend:
	@echo "--> Running flutter analyze..."
	cd vyapar && flutter analyze

format:
	@echo "--> Formatting backend code..."
	cd backend && uv run ruff format .
	@echo "--> Formatting Flutter code..."
	cd vyapar && dart format .

format-check:
	@echo "--> Checking backend formatting..."
	cd backend && uv run ruff format --check .
	@echo "--> Checking Flutter formatting..."
	cd vyapar && dart format --output=none --set-exit-if-changed .

infra-up:
	@echo "--> Starting local Postgres & Redis..."
	cd backend && docker compose up -d

infra-down:
	@echo "--> Stopping local Postgres & Redis..."
	cd backend && docker compose down

migrate:
	@echo "--> Running database migrations..."
	cd backend && uv run alembic upgrade head

seed:
	@echo "--> Seeding demo database..."
	cd backend && uv run python scripts/seed_demo.py

dev-backend:
	@echo "--> Starting FastAPI server (reload enabled)..."
	cd backend && uv run uvicorn app.main:app --reload

dev-worker:
	@echo "--> Starting ARQ background worker..."
	cd backend && uv run arq app.workers.worker.WorkerSettings

dev-frontend:
	@echo "--> Running Flutter application..."
	cd vyapar && flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1

demo:
	@echo "--> Running credential-free happy path workflow demo..."
	cd backend && uv run python scripts/run_happy_path.py

prod-build:
	@echo "--> Building production Docker containers..."
	docker compose -f deploy/docker-compose.prod.yml build

prod-up:
	@echo "--> Starting production Docker stack..."
	docker compose -f deploy/docker-compose.prod.yml up -d

prod-down:
	@echo "--> Stopping production Docker stack..."
	docker compose -f deploy/docker-compose.prod.yml down
