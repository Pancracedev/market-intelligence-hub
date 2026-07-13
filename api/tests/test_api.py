from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, Dataset, Run


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    session.add(
        Dataset(
            dataset_code="prc_hicp_manr",
            latest_gold_timeseries_key="eurostat/prc_hicp_manr/20260101T000000_timeseries.parquet",
            latest_gold_summary_key="eurostat/prc_hicp_manr/20260101T000000_summary.parquet",
            updated_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        Run(
            run_ts="20260101T000000",
            dataset_code="prc_hicp_manr",
            status="success",
            records_count=42,
            gold_key="eurostat/prc_hicp_manr/20260101T000000_summary.parquet",
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_datasets(client):
    response = client.get("/datasets")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["dataset_code"] == "prc_hicp_manr"


def test_list_runs(client):
    response = client.get("/runs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "success"
    assert body[0]["records_count"] == 42


def test_list_runs_filters_by_dataset_code(client):
    response = client.get("/runs", params={"dataset_code": "unknown_dataset"})
    assert response.status_code == 200
    assert response.json() == []
