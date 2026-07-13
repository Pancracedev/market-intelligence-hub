"""Market Intelligence Hub — ELT pipeline: ingest Eurostat data through Bronze -> Silver -> Gold.

Bronze : raw JSON-stat payload, untouched, dumped to MinIO.
Silver : cleaned, typed, deduplicated Parquet table.
Gold   : analytics-ready aggregates (time series + per-geo summary with period-over-period delta),
         with run metadata recorded in the app Postgres DB.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

DATASET_CODE = os.environ.get("EUROSTAT_DATASET_CODE", "prc_hicp_manr")

default_args = {
    "owner": "market-intelligence-hub",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
}


@dag(
    dag_id="market_intelligence_pipeline",
    description="Ingest Eurostat data and transform it through Bronze/Silver/Gold zones",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market-intelligence", "eurostat", "elt"],
)
def market_intelligence_pipeline():
    @task
    def ingest(**context) -> dict:
        from ingestion.bronze import ingest_eurostat_to_bronze

        run_ts = context["ts_nodash"]
        bronze_key = ingest_eurostat_to_bronze(DATASET_CODE, run_ts=run_ts)
        return {"run_ts": run_ts, "bronze_key": bronze_key}

    @task
    def to_silver(ingest_result: dict) -> dict:
        from ingestion.silver import transform_bronze_to_silver

        silver_key = transform_bronze_to_silver(
            DATASET_CODE,
            bronze_key=ingest_result["bronze_key"],
            run_ts=ingest_result["run_ts"],
        )
        return {**ingest_result, "silver_key": silver_key}

    @task
    def to_gold(silver_result: dict) -> dict:
        from ingestion.gold import transform_silver_to_gold

        gold_result = transform_silver_to_gold(
            DATASET_CODE,
            silver_key=silver_result["silver_key"],
            run_ts=silver_result["run_ts"],
        )
        return {**silver_result, **gold_result}

    to_gold(to_silver(ingest()))


market_intelligence_pipeline()
