"""Shared app-db (Postgres) engine builder, used by gold.py, ratelimit.py and scheduling.py."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_app_db_engine() -> Engine:
    # .strip() guards against a stray trailing newline/space from copy-pasting a value into
    # a dashboard env var field.
    user = os.environ.get("APP_DB_USER", "app").strip()
    password = os.environ.get("APP_DB_PASSWORD", "app").strip()
    host = os.environ.get("APP_DB_HOST", "localhost").strip()
    port = os.environ.get("APP_DB_PORT", "5432").strip()
    db = os.environ.get("APP_DB_NAME", "market_intelligence").strip()
    # "prefer" uses TLS when the server offers it (e.g. Neon, which requires it) and falls
    # back to plaintext otherwise (e.g. the local docker-compose Postgres) — one default
    # works for both without needing separate config per environment.
    sslmode = os.environ.get("APP_DB_SSLMODE", "prefer").strip()
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"
    return create_engine(url, pool_pre_ping=True)
