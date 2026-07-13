"""Silver zone: clean and normalize bronze payloads into a structured Parquet table."""

from __future__ import annotations

import os

import pandas as pd

from .sources.eurostat import parse_jsonstat
from .storage import ensure_bucket, get_client, get_json, put_bytes, write_parquet_bytes

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


def price_bronze_to_dataframe(payload: dict) -> pd.DataFrame:
    """Convert a single scraped price/stock/promo observation into a one-row DataFrame."""
    return pd.DataFrame(
        [
            {
                "timestamp": payload["scraped_at"],
                "value": payload["value"],
                "currency": payload["currency"],
                "url": payload["url"],
                "in_stock": payload.get("in_stock"),
                "stock_text": payload.get("stock_text"),
                "original_value": payload.get("original_value"),
                "is_promo": payload.get("is_promo", False),
                "discount_pct": payload.get("discount_pct"),
            }
        ]
    )


def eurostat_bronze_to_silver(watcher_id: int, dataset_code: str, bronze_key: str, run_ts: str) -> str:
    """Read a bronze Eurostat JSON payload, clean it, and write a Parquet file to the silver zone."""
    client = get_client()
    ensure_bucket(client, SILVER_BUCKET)

    payload = get_json(client, BRONZE_BUCKET, bronze_key)
    records = parse_jsonstat(payload, dataset_code)
    df = bronze_records_to_dataframe(records)

    key = f"eurostat/{watcher_id}/{run_ts}.parquet"
    put_bytes(client, SILVER_BUCKET, key, write_parquet_bytes(df), content_type="application/octet-stream")
    return key


def price_bronze_to_silver(watcher_id: int, bronze_key: str, run_ts: str) -> str:
    """Read a single bronze price observation and write it as a one-row Parquet to the silver zone."""
    client = get_client()
    ensure_bucket(client, SILVER_BUCKET)

    payload = get_json(client, BRONZE_BUCKET, bronze_key)
    df = price_bronze_to_dataframe(payload)

    key = f"price/{watcher_id}/{run_ts}.parquet"
    put_bytes(client, SILVER_BUCKET, key, write_parquet_bytes(df), content_type="application/octet-stream")
    return key


def transform_bronze_to_silver(watcher: dict, bronze_key: str, run_ts: str) -> str:
    """Dispatch bronze-to-silver transformation based on `watcher["watcher_type"]`."""
    watcher_id = watcher["id"]
    watcher_type = watcher["watcher_type"]

    if watcher_type == "eurostat":
        return eurostat_bronze_to_silver(watcher_id, watcher["config"]["dataset_code"], bronze_key, run_ts)
    if watcher_type == "price":
        return price_bronze_to_silver(watcher_id, bronze_key, run_ts)
    raise ValueError(f"Unsupported watcher_type for silver transformation: {watcher_type!r}")
