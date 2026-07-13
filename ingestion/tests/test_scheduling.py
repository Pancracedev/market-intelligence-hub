from datetime import datetime, timezone

from ingestion.scheduling import _is_due


def test_never_run_watcher_is_always_due():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert _is_due("@daily", None, now) is True


def test_daily_watcher_not_due_before_a_day_has_passed():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    last_run = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
    assert _is_due("@daily", last_run, now) is False


def test_daily_watcher_due_after_a_day_has_passed():
    now = datetime(2026, 1, 3, 1, 0, tzinfo=timezone.utc)
    last_run = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
    assert _is_due("@daily", last_run, now) is True


def test_hourly_watcher_due_after_an_hour():
    now = datetime(2026, 1, 1, 13, 5, tzinfo=timezone.utc)
    last_run = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert _is_due("@hourly", last_run, now) is True


def test_raw_cron_expression_is_respected():
    # every 15 minutes
    last_run = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert _is_due("*/15 * * * *", last_run, now=datetime(2026, 1, 1, 12, 20, tzinfo=timezone.utc)) is True
    assert _is_due("*/15 * * * *", last_run, now=datetime(2026, 1, 1, 12, 10, tzinfo=timezone.utc)) is False
