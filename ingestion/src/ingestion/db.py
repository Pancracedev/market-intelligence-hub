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
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)
