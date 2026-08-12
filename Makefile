.PHONY: help install dev compose-up compose-down compose-logs db-migrate db-revision \
	test test-api test-web lint format portability clean deploy-api deploy-web deploy

COMPOSE := docker compose -f infra/compose/docker-compose.yml

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install web + api deps
	bun install
	cd apps/api && uv sync

compose-up: ## Bring up the full dev stack
	$(COMPOSE) up --build

compose-down: ## Tear down + remove volumes
	$(COMPOSE) down -v

compose-logs: ## Tail compose logs
	$(COMPOSE) logs -f

db-migrate: ## Apply latest Alembic migrations
	cd apps/api && uv run alembic upgrade head

db-revision: ## Create a new auto-generated migration: make db-revision m="add patients"
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

test: test-api test-web ## Run all tests

test-api: ## Run pytest (unit + integration)
	cd apps/api && uv run pytest

test-web: ## Run vitest
	cd apps/web && bun run test

lint: ## Run all linters
	cd apps/api && uv run ruff check . && uv run mypy app
	bun run lint

format: ## Format everything
	cd apps/api && uv run ruff format .
	bun run format

portability: ## Verify portability invariants
	python3 scripts/check_portability.py

deploy-api: ## Deploy API to Fly.io (local)
	fly deploy --config infra/fly/fly.toml --dockerfile infra/docker/api.Dockerfile --remote-only

deploy-web: ## Deploy web to Cloudflare Pages (MUST run from apps/web so functions/ ships)
	cd apps/web && VITE_API_BASE_URL=$${PROD_API_BASE_URL:-https://clinic-crm-api.fly.dev} VITE_NEON_AUTH_URL=/neon-auth bun run build
	cd apps/web && bunx wrangler pages deploy dist --project-name=clinic-crm-web --branch=main --commit-dirty=true

deploy: deploy-api deploy-web ## Deploy API + web from local machine

clean: ## Remove caches + build artifacts
	rm -rf apps/api/.venv apps/api/.pytest_cache apps/api/.mypy_cache apps/api/.ruff_cache
	rm -rf apps/web/dist apps/web/node_modules
	rm -rf node_modules
