"""Market Intelligence Hub — dynamic ELT pipeline for user-configured watchers.

Runs hourly, queries which active watchers are "due" for a run based on their own
per-watcher `schedule` (see ingestion.scheduling), and dynamically maps the
ingest -> silver -> gold pipeline across all of them in a single DAG run
(Airflow 2.9 dynamic task mapping) instead of one DAG per watcher.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

default_args = {
    "owner": "market-intelligence-hub",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
}


@dag(
    dag_id="watcher_pipeline",
    description="Fan out ingest/silver/gold across all due, user-configured watchers",
    default_args=default_args,
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market-intelligence", "watchers", "elt"],
)
def watcher_pipeline():
    @task
    def list_due_watchers() -> list[dict]:
        from ingestion.scheduling import get_due_watchers

        return get_due_watchers()

    @task
    def ingest(watcher: dict, **context) -> dict:
        from ingestion.bronze import ingest_watcher_to_bronze
        from ingestion.gold import record_failed_run

        run_ts = context["ts_nodash"]
        try:
            bronze_key = ingest_watcher_to_bronze(watcher, run_ts=run_ts)
        except Exception as exc:
            record_failed_run(watcher["id"], run_ts, str(exc))
            raise
        return {"watcher": watcher, "run_ts": run_ts, "bronze_key": bronze_key}

    @task
    def to_silver(ingest_result: dict) -> dict:
        from ingestion.gold import record_failed_run
        from ingestion.silver import transform_bronze_to_silver

        try:
            silver_key = transform_bronze_to_silver(
                ingest_result["watcher"], ingest_result["bronze_key"], ingest_result["run_ts"]
            )
        except Exception as exc:
            record_failed_run(ingest_result["watcher"]["id"], ingest_result["run_ts"], str(exc))
            raise
        return {**ingest_result, "silver_key": silver_key}

    @task(trigger_rule="all_done")
    def to_gold(silver_result: dict) -> dict | None:
        from ingestion.gold import record_failed_run, transform_silver_to_gold

        if silver_result is None:
            return None
        try:
            return transform_silver_to_gold(
                silver_result["watcher"], silver_result["silver_key"], silver_result["run_ts"]
            )
        except Exception as exc:
            record_failed_run(silver_result["watcher"]["id"], silver_result["run_ts"], str(exc))
            raise

    watchers = list_due_watchers()
    to_gold.expand(silver_result=to_silver.expand(ingest_result=ingest.expand(watcher=watchers)))


watcher_pipeline()
