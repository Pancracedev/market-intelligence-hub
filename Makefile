.PHONY: up down logs ps build test test-ingestion test-api lint dag-trigger clean

up:
	docker compose up -d --build

down:
	docker compose down

clean:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

test-ingestion:
	cd ingestion && pip install -q -e ".[dev]" && pytest -v

test-api:
	cd api && pip install -q -r requirements.txt && pytest -v

test: test-ingestion test-api

lint:
	cd ingestion && ruff check src tests
	cd api && ruff check app tests

dag-trigger:
	docker compose exec airflow-webserver airflow dags trigger market_intelligence_pipeline
