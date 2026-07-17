import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

INIT_SQL_PATH = Path(__file__).resolve().parent.parent / "infra" / "postgres" / "init.sql"


def _database_url() -> str:
    # .strip() guards against a stray trailing newline/space from copy-pasting a value into
    # a dashboard env var field.
    user = os.environ.get("APP_DB_USER", "app").strip()
    password = os.environ.get("APP_DB_PASSWORD", "app").strip()
    host = os.environ.get("APP_DB_HOST", "localhost").strip()
    port = os.environ.get("APP_DB_PORT", "5432").strip()
    db = os.environ.get("APP_DB_NAME", "market_intelligence").strip()
    # "prefer" uses TLS when the server offers it (e.g. Neon, which requires it) and falls
    # back to plaintext otherwise (e.g. the local docker-compose Postgres).
    sslmode = os.environ.get("APP_DB_SSLMODE", "prefer").strip()
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """Applies infra/postgres/init.sql on startup - safe to run every time since every
    statement in it is idempotent (CREATE TABLE/INDEX IF NOT EXISTS). Lets a fresh managed
    Postgres (e.g. Neon) provision its own schema without a separate manual psql step.
    """
    sql = INIT_SQL_PATH.read_text()
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
