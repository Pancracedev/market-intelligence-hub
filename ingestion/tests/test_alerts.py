import pytest

from ingestion import alerts


@pytest.fixture(autouse=True)
def no_db_logging(monkeypatch):
    # _dispatch writes to notifications_log via a live Postgres engine - out of scope for
    # these unit tests, which only exercise the trigger logic.
    monkeypatch.setattr(alerts, "_log_notification", lambda *a, **kw: None)


def _watcher(**overrides):
    base = {
        "id": 1,
        "name": "Casque XZ200",
        "watcher_type": "price",
        "user_email": "user@example.com",
        "slack_webhook_url": None,
        "alert_price_drop_pct": None,
        "alert_on_stock_out": True,
        "alert_on_promo": True,
    }
    base.update(overrides)
    return base


def test_price_drop_alert_triggers_when_threshold_exceeded(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher(alert_price_drop_pct=10)
    summary = {"latest_value": 17.99, "previous_value": 19.99, "delta": -2.0, "currency": "EUR"}

    alerts.evaluate_and_notify(watcher, summary)

    assert len(calls) == 1
    assert "Baisse de prix" in calls[0][2]


def test_price_drop_alert_not_triggered_below_threshold(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher(alert_price_drop_pct=50)
    summary = {"latest_value": 17.99, "previous_value": 19.99, "delta": -2.0, "currency": "EUR"}

    alerts.evaluate_and_notify(watcher, summary)

    assert calls == []


def test_stock_out_alert_triggers_on_transition(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher()
    summary = {"in_stock": False, "previous_in_stock": True}

    alerts.evaluate_and_notify(watcher, summary)

    assert len(calls) == 1
    assert "rupture de stock" in calls[0][2]


def test_stock_out_alert_not_repeated_if_already_out(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher()
    summary = {"in_stock": False, "previous_in_stock": False}

    alerts.evaluate_and_notify(watcher, summary)

    assert calls == []


def test_stock_out_alert_disabled_by_watcher_setting(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher(alert_on_stock_out=False)
    summary = {"in_stock": False, "previous_in_stock": True}

    alerts.evaluate_and_notify(watcher, summary)

    assert calls == []


def test_promo_alert_triggers_on_new_promo(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher()
    summary = {"is_promo": True, "previous_is_promo": False, "discount_pct": 15.0}

    alerts.evaluate_and_notify(watcher, summary)

    assert len(calls) == 1
    assert "promotion" in calls[0][2].lower()


def test_no_alerts_for_non_price_watcher_type(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: calls.append(a) or True)

    watcher = _watcher(watcher_type="eurostat", alert_price_drop_pct=1)
    summary = {"in_stock": False, "previous_in_stock": True}

    alerts.evaluate_and_notify(watcher, summary)

    assert calls == []


def test_dispatch_uses_slack_when_configured(monkeypatch):
    slack_calls = []
    monkeypatch.setattr(alerts, "send_email", lambda *a, **kw: True)
    monkeypatch.setattr(alerts, "send_slack", lambda *a, **kw: slack_calls.append(a) or True)

    watcher = _watcher(slack_webhook_url="https://hooks.slack.com/services/x", alert_price_drop_pct=10)
    summary = {"latest_value": 17.99, "previous_value": 19.99, "delta": -2.0, "currency": "EUR"}

    alerts.evaluate_and_notify(watcher, summary)

    assert len(slack_calls) == 1
