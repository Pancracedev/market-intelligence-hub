.PHONY: up down up-prod down-prod logs ps build sync test test-ingestion test-api lint dag-trigger clean

up:
	docker compose up -d --build

down:
	docker compose down

up-prod:
	docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build

down-prod:
	docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml down

clean:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

sync:
	cd ingestion && uv sync
	cd api && uv sync

test-ingestion:
	cd ingestion && uv sync && uv run pytest tests -v

test-api:
	cd api && uv sync && PYTHONPATH=. uv run pytest tests -v

test: test-ingestion test-api

lint:
	cd ingestion && uv run ruff check src tests
	cd api && uv run ruff check app tests

dag-trigger:
	docker compose exec airflow-webserver airflow dags trigger watcher_pipeline
