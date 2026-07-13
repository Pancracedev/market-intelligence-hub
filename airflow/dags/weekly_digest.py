"""Market Intelligence Hub — weekly AI-generated digest.

Runs once a week, and for every user with at least one active watcher, turns the week's
runs and alerts into a short narrative summary (via Claude, with a plain-text fallback if
ANTHROPIC_API_KEY isn't configured) and emails it - closing the loop so users don't have
to piece together what changed from the raw dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

default_args = {
    "owner": "market-intelligence-hub",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="weekly_digest",
    description="Generate and send a weekly AI digest to every user with active watchers",
    default_args=default_args,
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market-intelligence", "digest"],
)
def weekly_digest():
    @task
    def list_recipients() -> list[dict]:
        from ingestion.digest import get_users_with_active_watchers

        return get_users_with_active_watchers()

    @task
    def send_digest(user: dict) -> str | None:
        from ingestion.digest import generate_weekly_digest

        return generate_weekly_digest(user["id"], user["email"])

    send_digest.expand(user=list_recipients())


weekly_digest()
