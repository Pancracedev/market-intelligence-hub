import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _):
        # SQLite ignores ON DELETE SET NULL/CASCADE unless this pragma is set - needed for
        # e.g. comparison_groups deletion to correctly detach (not orphan) its watchers.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

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


def test_cors_headers_present_for_allowed_frontend_origin(client):
    # Regression test: without CORSMiddleware, the browser (not curl) silently blocks every
    # cross-origin request from the frontend (localhost:3000) to the API (localhost:8000),
    # which surfaced to users as "impossible de contacter le serveur" on login.
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


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
    # alert_on_stock_out/alert_on_promo default to True, price-drop threshold is opt-in
    assert fetched.json()["alert_on_stock_out"] is True
    assert fetched.json()["alert_on_promo"] is True
    assert fetched.json()["alert_price_drop_pct"] is None


def test_create_watcher_with_alert_thresholds(client):
    token = signup(client)
    payload = {
        "watcher_type": "price",
        "name": "Competitor product Y",
        "config": {"type": "price", "url": "https://example.com/y", "css_selector": ".price"},
        "alert_price_drop_pct": 10,
        "alert_on_stock_out": False,
        "alert_on_promo": False,
    }
    created = client.post("/watchers", json=payload, headers=auth_headers(token))
    assert created.status_code == 201, created.text
    assert created.json()["alert_price_drop_pct"] == 10
    assert created.json()["alert_on_stock_out"] is False
    assert created.json()["alert_on_promo"] is False


def test_update_user_slack_webhook(client):
    token = signup(client)
    response = client.patch(
        "/auth/me", json={"slack_webhook_url": "https://hooks.slack.com/services/x"}, headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["slack_webhook_url"] == "https://hooks.slack.com/services/x"


def test_clear_user_slack_webhook(client):
    token = signup(client)
    client.patch("/auth/me", json={"slack_webhook_url": "https://hooks.slack.com/services/x"}, headers=auth_headers(token))

    response = client.patch("/auth/me", json={"slack_webhook_url": None}, headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["slack_webhook_url"] is None


def test_list_watcher_alerts_empty_by_default(client):
    token = signup(client)
    created = client.post(
        "/watchers",
        json={
            "watcher_type": "price",
            "name": "Z",
            "config": {"type": "price", "url": "https://example.com/z", "css_selector": ".price"},
        },
        headers=auth_headers(token),
    )
    watcher_id = created.json()["id"]

    response = client.get(f"/watchers/{watcher_id}/alerts", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []


def test_list_digests_empty_by_default(client):
    token = signup(client)
    response = client.get("/digests", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []


def test_generate_digest_now_without_watchers_rejected(client, monkeypatch):
    import ingestion.digest

    monkeypatch.setattr(ingestion.digest, "generate_weekly_digest", lambda user_id, user_email: None)

    token = signup(client)
    response = client.post("/digests/generate", headers=auth_headers(token))
    assert response.status_code == 400


def test_generate_digest_now_returns_created_digest(client, monkeypatch):
    import ingestion.digest
    from datetime import datetime, timezone

    monkeypatch.setattr(
        ingestion.digest,
        "generate_weekly_digest",
        lambda user_id, user_email: {"id": 1, "content": "Résumé test.", "generated_at": datetime.now(timezone.utc)},
    )

    token = signup(client)
    response = client.post("/digests/generate", headers=auth_headers(token))
    assert response.status_code == 201, response.text
    assert response.json()["content"] == "Résumé test."


def test_create_watcher_auto_mode_without_css_selector(client):
    token = signup(client)
    payload = {
        "watcher_type": "price",
        "name": "Produit simple",
        "config": {"type": "price", "url": "https://example.com/product"},
    }
    created = client.post("/watchers", json=payload, headers=auth_headers(token))
    assert created.status_code == 201, created.text
    assert created.json()["config"]["mode"] == "auto"


def test_create_watcher_manual_mode_requires_css_selector(client):
    token = signup(client)
    payload = {
        "watcher_type": "price",
        "name": "Produit avancé",
        "config": {"type": "price", "url": "https://example.com/product", "mode": "manual"},
    }
    response = client.post("/watchers", json=payload, headers=auth_headers(token))
    assert response.status_code == 422


def test_detect_product_success(client, monkeypatch):
    monkeypatch.setattr(
        "ingestion.sources.product_detector.detect_product",
        lambda url: {"value": 89.9, "currency": "EUR", "in_stock": True, "method": "json-ld"},
    )

    token = signup(client)
    response = client.post("/watchers/detect", json={"url": "https://example.com/product"}, headers=auth_headers(token))
    assert response.status_code == 200, response.text
    assert response.json()["value"] == 89.9
    assert response.json()["method"] == "json-ld"


def test_detect_product_not_found_returns_422(client, monkeypatch):
    from ingestion.sources.product_detector import ProductNotDetectedError

    def _raise(url):
        raise ProductNotDetectedError("nothing found")

    monkeypatch.setattr("ingestion.sources.product_detector.detect_product", _raise)

    token = signup(client)
    response = client.post("/watchers/detect", json={"url": "https://example.com/product"}, headers=auth_headers(token))
    assert response.status_code == 422


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


def _create_price_watcher(client, token, name="Produit"):
    return client.post(
        "/watchers",
        json={
            "watcher_type": "price",
            "name": name,
            "config": {"type": "price", "url": f"https://example.com/{name}"},
        },
        headers=auth_headers(token),
    ).json()


def test_create_comparison_group_and_assign_watcher(client):
    token = signup(client)
    group = client.post("/comparison-groups", json={"name": "Casque XZ200"}, headers=auth_headers(token))
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    watcher = _create_price_watcher(client, token, "Concurrent A")
    updated = client.patch(
        f"/watchers/{watcher['id']}", json={"comparison_group_id": group_id}, headers=auth_headers(token)
    )
    assert updated.status_code == 200
    assert updated.json()["comparison_group_id"] == group_id

    fetched_group = client.get(f"/comparison-groups/{group_id}", headers=auth_headers(token))
    assert len(fetched_group.json()["watchers"]) == 1
    assert fetched_group.json()["watchers"][0]["id"] == watcher["id"]


def test_unassign_watcher_from_comparison_group(client):
    token = signup(client)
    group = client.post("/comparison-groups", json={"name": "Groupe"}, headers=auth_headers(token)).json()
    watcher = _create_price_watcher(client, token)
    client.patch(f"/watchers/{watcher['id']}", json={"comparison_group_id": group["id"]}, headers=auth_headers(token))

    unassigned = client.patch(
        f"/watchers/{watcher['id']}", json={"comparison_group_id": None}, headers=auth_headers(token)
    )
    assert unassigned.json()["comparison_group_id"] is None


def test_comparison_group_isolation_between_users(client):
    token_a = signup(client, email="a@example.com")
    token_b = signup(client, email="b@example.com")
    group = client.post("/comparison-groups", json={"name": "A's group"}, headers=auth_headers(token_a)).json()

    listed_b = client.get("/comparison-groups", headers=auth_headers(token_b))
    assert listed_b.json() == []

    fetched_b = client.get(f"/comparison-groups/{group['id']}", headers=auth_headers(token_b))
    assert fetched_b.status_code == 404


def test_cannot_assign_watcher_to_another_users_group(client):
    token_a = signup(client, email="a2@example.com")
    token_b = signup(client, email="b2@example.com")
    group_a = client.post("/comparison-groups", json={"name": "A's group"}, headers=auth_headers(token_a)).json()
    watcher_b = _create_price_watcher(client, token_b)

    response = client.patch(
        f"/watchers/{watcher_b['id']}", json={"comparison_group_id": group_a["id"]}, headers=auth_headers(token_b)
    )
    assert response.status_code == 404


def test_delete_comparison_group_detaches_watchers_without_deleting_them(client):
    token = signup(client)
    group = client.post("/comparison-groups", json={"name": "Groupe"}, headers=auth_headers(token)).json()
    watcher = _create_price_watcher(client, token)
    client.patch(f"/watchers/{watcher['id']}", json={"comparison_group_id": group["id"]}, headers=auth_headers(token))

    deleted = client.delete(f"/comparison-groups/{group['id']}", headers=auth_headers(token))
    assert deleted.status_code == 204

    fetched_watcher = client.get(f"/watchers/{watcher['id']}", headers=auth_headers(token))
    assert fetched_watcher.status_code == 200
    assert fetched_watcher.json()["comparison_group_id"] is None
