"""Silver zone: clean and normalize bronze payloads into a structured Parquet table."""

from __future__ import annotations

import os

import pandas as pd

from .sources.eurostat import parse_jsonstat
from .storage import ensure_bucket, get_client, get_json, write_parquet_bytes, put_bytes

BRONZE_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")
SILVER_BUCKET = os.environ.get("MINIO_BUCKET_SILVER", "silver")


def bronze_records_to_dataframe(records) -> pd.DataFrame:
    """Convert a list of EurostatRecord into a cleaned, typed DataFrame."""
    df = pd.DataFrame([r.__dict__ for r in records])
    if df.empty:
        return df

    df = df.dropna(subset=["geo", "time_period", "value"])
    df = df[df["geo"] != "UNKNOWN"]
    df = df[df["time_period"] != "UNKNOWN"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df = df.drop_duplicates(subset=["dataset_code", "geo", "time_period", "indicator", "unit"])
    df = df.sort_values(["geo", "time_period"]).reset_index(drop=True)
    return df


def transform_bronze_to_silver(dataset_code: str, bronze_key: str, run_ts: str) -> str:
    """Read a bronze JSON payload, clean it, and write a Parquet file to the silver zone."""
    client = get_client()
    ensure_bucket(client, SILVER_BUCKET)

    payload = get_json(client, BRONZE_BUCKET, bronze_key)
    records = parse_jsonstat(payload, dataset_code)
    df = bronze_records_to_dataframe(records)

    key = f"eurostat/{dataset_code}/{run_ts}.parquet"
    put_bytes(
        client,
        SILVER_BUCKET,
        key,
        write_parquet_bytes(df),
        content_type="application/octet-stream",
    )
    return key
