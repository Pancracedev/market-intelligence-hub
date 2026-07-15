"""Shared app-db (Postgres) engine builder, used by gold.py, ratelimit.py and scheduling.py."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_app_db_engine() -> Engine:
    user = os.environ.get("APP_DB_USER", "app")
    password = os.environ.get("APP_DB_PASSWORD", "app")
    host = os.environ.get("APP_DB_HOST", "localhost")
    port = os.environ.get("APP_DB_PORT", "5432")
    db = os.environ.get("APP_DB_NAME", "market_intelligence")
    # "prefer" uses TLS when the server offers it (e.g. Neon, which requires it) and falls
    # back to plaintext otherwise (e.g. the local docker-compose Postgres) — one default
    # works for both without needing separate config per environment.
    sslmode = os.environ.get("APP_DB_SSLMODE", "prefer")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"
    return create_engine(url, pool_pre_ping=True)
