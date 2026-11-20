# AdaptAid developer commands. Run `make help` for the list.
SHELL := /bin/bash
PY    := backend/.venv/bin
API_PORT ?= 8000
WEB_PORT ?= 3000

.PHONY: help install db db-down api web dev migrate test lint typecheck contract e2e gen-api ci clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Create the backend venv and install backend + frontend dependencies
	test -d backend/.venv || python3.11 -m venv backend/.venv
	$(PY)/pip install -q --upgrade pip
	$(PY)/pip install -q -e "backend[dev]"
	cd frontend && npm ci

db: ## Start PostgreSQL in Docker (host port 5434)
	docker compose up -d --wait db

db-down: ## Stop PostgreSQL (data is kept in the pgdata volume)
	docker compose stop db

api: ## Run the FastAPI dev server with reload
	cd backend && .venv/bin/uvicorn app.main:app --reload --port $(API_PORT)

web: ## Run the Next.js dev server
	cd frontend && npm run dev -- -p $(WEB_PORT)

dev: db ## Run database, API and web together (Ctrl+C stops both servers)
	$(MAKE) -j2 api web

test: ## Backend tests (engine + API)
	cd backend && .venv/bin/pytest

lint: ## Ruff + ESLint
	$(PY)/ruff check backend
	cd frontend && npm run lint

typecheck: ## TypeScript check
	cd frontend && npm run typecheck

contract: ## Proxy contract test (Playwright request tests through a production build)
	cd frontend && npx playwright test --project=contract

e2e: ## Browser journeys (Playwright)
	cd frontend && npx playwright test --project=e2e

gen-api: ## Regenerate the typed API client from FastAPI's OpenAPI schema
	cd backend && .venv/bin/python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=1, sort_keys=True))" > openapi.json
	cd frontend && npm run gen:api

ci: lint typecheck test ## Everything CI runs
	cd frontend && npm run build
