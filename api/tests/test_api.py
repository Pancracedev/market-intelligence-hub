import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def signup(client, email="user@example.com", password="supersecret1"):
    response = client.post("/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_then_me(client):
    token = signup(client)
    response = client.get("/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_signup_duplicate_email_rejected(client):
    signup(client)
    response = client.post(
        "/auth/signup", json={"email": "user@example.com", "password": "anotherpass1"}
    )
    assert response.status_code == 409


def test_login_success_and_wrong_password(client):
    signup(client)
    ok = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "supersecret1"}
    )
    assert ok.status_code == 200

    bad = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "wrongpass"}
    )
    assert bad.status_code == 401


def test_me_requires_valid_token(client):
    response = client.get("/auth/me", headers=auth_headers("not-a-real-token"))
    assert response.status_code == 401


def test_create_and_list_watcher(client):
    token = signup(client)
    payload = {
        "watcher_type": "price",
        "name": "Competitor product X",
        "config": {"type": "price", "url": "https://example.com/product", "css_selector": ".price"},
        "schedule": "@daily",
    }
    created = client.post("/watchers", json=payload, headers=auth_headers(token))
    assert created.status_code == 201, created.text
    watcher_id = created.json()["id"]

    listed = client.get("/watchers", headers=auth_headers(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == watcher_id

    fetched = client.get(f"/watchers/{watcher_id}", headers=auth_headers(token))
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Competitor product X"


def test_watcher_type_config_mismatch_rejected(client):
    token = signup(client)
    payload = {
        "watcher_type": "price",
        "name": "Mismatched",
        "config": {"type": "trend", "keyword": "foo"},
        "schedule": "@daily",
    }
    response = client.post("/watchers", json=payload, headers=auth_headers(token))
    assert response.status_code == 422


def test_watcher_isolation_between_users(client):
    token_a = signup(client, email="a@example.com")
    token_b = signup(client, email="b@example.com")

    created = client.post(
        "/watchers",
        json={
            "watcher_type": "trend",
            "name": "User A's watcher",
            "config": {"type": "trend", "keyword": "widget"},
        },
        headers=auth_headers(token_a),
    )
    watcher_id = created.json()["id"]

    # user B must not see user A's watcher in their list, nor fetch it by id.
    listed_b = client.get("/watchers", headers=auth_headers(token_b))
    assert listed_b.json() == []

    fetched_b = client.get(f"/watchers/{watcher_id}", headers=auth_headers(token_b))
    assert fetched_b.status_code == 404


def test_delete_watcher(client):
    token = signup(client)
    created = client.post(
        "/watchers",
        json={
            "watcher_type": "eurostat",
            "name": "Inflation FR",
            "config": {"type": "eurostat", "dataset_code": "prc_hicp_manr", "filters": {"geo": "FR"}},
        },
        headers=auth_headers(token),
    )
    watcher_id = created.json()["id"]

    deleted = client.delete(f"/watchers/{watcher_id}", headers=auth_headers(token))
    assert deleted.status_code == 204

    fetched = client.get(f"/watchers/{watcher_id}", headers=auth_headers(token))
    assert fetched.status_code == 404


def test_list_runs_empty_by_default(client):
    token = signup(client)
    response = client.get("/runs", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []
