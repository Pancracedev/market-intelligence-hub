"""Gold zone: analytics-ready aggregates, plus run/dataset metadata in the app Postgres DB."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine, text

from .storage import ensure_bucket, get_client, get_bytes, read_parquet_bytes, write_parquet_bytes, put_bytes

SILVER_BUCKET = os.environ.get("MINIO_BUCKET_SILVER", "silver")
GOLD_BUCKET = os.environ.get("MINIO_BUCKET_GOLD", "gold")


def _app_db_engine():
    user = os.environ.get("APP_DB_USER", "app")
    password = os.environ.get("APP_DB_PASSWORD", "app")
    host = os.environ.get("APP_DB_HOST", "localhost")
    port = os.environ.get("APP_DB_PORT", "5432")
    db = os.environ.get("APP_DB_NAME", "market_intelligence")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """For each geo, compute the latest value and the delta vs. the previous period."""
    if df.empty:
        return df

    rows = []
    for geo, group in df.sort_values("time_period").groupby("geo"):
        latest = group.iloc[-1]
        previous_value = group.iloc[-2]["value"] if len(group) > 1 else None
        delta = latest["value"] - previous_value if previous_value is not None else None
        rows.append(
            {
                "geo": geo,
                "dataset_code": latest["dataset_code"],
                "indicator": latest.get("indicator"),
                "unit": latest.get("unit"),
                "latest_period": latest["time_period"],
                "latest_value": latest["value"],
                "previous_value": previous_value,
                "delta": delta,
            }
        )

    summary = pd.DataFrame(rows)
    return summary.sort_values("delta", ascending=False, na_position="last").reset_index(drop=True)


def transform_silver_to_gold(dataset_code: str, silver_key: str, run_ts: str) -> dict:
    """Read a silver Parquet file, aggregate it, write gold outputs and record metadata."""
    client = get_client()
    ensure_bucket(client, GOLD_BUCKET)

    df = read_parquet_bytes(get_bytes(client, SILVER_BUCKET, silver_key))

    timeseries_key = f"eurostat/{dataset_code}/{run_ts}_timeseries.parquet"
    put_bytes(client, GOLD_BUCKET, timeseries_key, write_parquet_bytes(df))

    summary_df = build_summary(df)
    summary_key = f"eurostat/{dataset_code}/{run_ts}_summary.parquet"
    put_bytes(client, GOLD_BUCKET, summary_key, write_parquet_bytes(summary_df))

    _record_metadata(
        dataset_code=dataset_code,
        run_ts=run_ts,
        timeseries_key=timeseries_key,
        summary_key=summary_key,
        records_count=len(df),
    )

    return {
        "timeseries_key": timeseries_key,
        "summary_key": summary_key,
        "records_count": len(df),
    }


def _record_metadata(
    dataset_code: str,
    run_ts: str,
    timeseries_key: str,
    summary_key: str,
    records_count: int,
) -> None:
    engine = _app_db_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO datasets (dataset_code, latest_gold_timeseries_key, latest_gold_summary_key, updated_at)
                VALUES (:dataset_code, :timeseries_key, :summary_key, now())
                ON CONFLICT (dataset_code) DO UPDATE SET
                    latest_gold_timeseries_key = EXCLUDED.latest_gold_timeseries_key,
                    latest_gold_summary_key = EXCLUDED.latest_gold_summary_key,
                    updated_at = now()
                """
            ),
            {"dataset_code": dataset_code, "timeseries_key": timeseries_key, "summary_key": summary_key},
        )
        conn.execute(
            text(
                """
                INSERT INTO runs (run_ts, dataset_code, status, records_count, gold_key)
                VALUES (:run_ts, :dataset_code, 'success', :records_count, :summary_key)
                """
            ),
            {
                "run_ts": run_ts,
                "dataset_code": dataset_code,
                "records_count": records_count,
                "summary_key": summary_key,
            },
        )
