import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    user = os.environ.get("APP_DB_USER", "app")
    password = os.environ.get("APP_DB_PASSWORD", "app")
    host = os.environ.get("APP_DB_HOST", "localhost")
    port = os.environ.get("APP_DB_PORT", "5432")
    db = os.environ.get("APP_DB_NAME", "market_intelligence")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
