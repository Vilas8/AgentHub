.PHONY: help dev-backend dev-frontend dev-worker migrate test-backend test-frontend lint format

help:
	@echo "AgentHub Development Commands"
	@echo ""
	@echo "  make dev-backend     Start FastAPI backend"
	@echo "  make dev-frontend    Start Next.js frontend"
	@echo "  make dev-worker      Start execution worker"
	@echo "  make migrate         Run database migrations"
	@echo "  make test-backend    Run backend tests"
	@echo "  make test-frontend   Run frontend tests"
	@echo "  make lint            Run linters"
	@echo "  make format          Format code"

dev-backend:
	cd apps/api && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd apps/web && npm run dev

dev-worker:
	cd apps/api && python -m workers.execution.worker

migrate:
	cd apps/api && alembic upgrade head

migrate-create:
	cd apps/api && alembic revision --autogenerate -m "$(name)"

test-backend:
	cd apps/api && pytest tests/ -v

test-frontend:
	cd apps/web && npm test

lint:
	cd apps/api && ruff check .
	cd apps/web && npm run lint

format:
	cd apps/api && ruff format .
	cd apps/web && npm run format
