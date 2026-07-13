"""Gold zone: analytics-ready aggregates, plus run/watcher metadata in the app Postgres DB."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import text

from .alerts import evaluate_and_notify
from .db import get_app_db_engine
from .storage import (
    ensure_bucket,
    get_bytes,
    get_client,
    list_keys,
    put_bytes,
    read_parquet_bytes,
    write_parquet_bytes,
)

SILVER_BUCKET = os.environ.get("MINIO_BUCKET_SILVER", "silver")
GOLD_BUCKET = os.environ.get("MINIO_BUCKET_GOLD", "gold")


def build_summary_by_geo(df: pd.DataFrame) -> pd.DataFrame:
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


def build_summary_single_series(df: pd.DataFrame, value_col: str = "value", ts_col: str = "timestamp") -> pd.DataFrame:
    """Latest value + delta vs. the previous observation, for a single (non-grouped) time series."""
    if df.empty:
        return df

    ordered = df.sort_values(ts_col)
    latest = ordered.iloc[-1]
    previous_value = ordered.iloc[-2][value_col] if len(ordered) > 1 else None
    delta = latest[value_col] - previous_value if previous_value is not None else None

    # Pass through whichever optional per-observation fields are present (e.g. stock/promo
    # status for price watchers) so the frontend can surface them without a separate call.
    passthrough_cols = ["currency", "in_stock", "stock_text", "original_value", "is_promo", "discount_pct"]
    extra = {col: latest[col] for col in passthrough_cols if col in ordered.columns}

    # Also carry the *previous* observation's stock/promo status so alerts.py can detect a
    # transition (e.g. in stock -> out of stock) rather than re-alerting every run.
    previous = ordered.iloc[-2] if len(ordered) > 1 else None
    if previous is not None:
        if "in_stock" in ordered.columns:
            extra["previous_in_stock"] = previous["in_stock"]
        if "is_promo" in ordered.columns:
            extra["previous_is_promo"] = previous["is_promo"]

    return pd.DataFrame(
        [
            {
                "latest_timestamp": latest[ts_col],
                "latest_value": latest[value_col],
                "previous_value": previous_value,
                "delta": delta,
                **extra,
            }
        ]
    )


def eurostat_silver_to_gold(watcher_id: int, silver_key: str, run_ts: str) -> dict:
    """Eurostat silver already contains the full historical series in one file per run."""
    client = get_client()
    ensure_bucket(client, GOLD_BUCKET)

    df = read_parquet_bytes(get_bytes(client, SILVER_BUCKET, silver_key))

    timeseries_key = f"eurostat/{watcher_id}/{run_ts}_timeseries.parquet"
    put_bytes(client, GOLD_BUCKET, timeseries_key, write_parquet_bytes(df))

    summary_df = build_summary_by_geo(df)
    summary_key = f"eurostat/{watcher_id}/{run_ts}_summary.parquet"
    put_bytes(client, GOLD_BUCKET, summary_key, write_parquet_bytes(summary_df))

    return {"timeseries_key": timeseries_key, "summary_key": summary_key, "records_count": len(df)}


def price_silver_to_gold(watcher_id: int, run_ts: str) -> dict:
    """Price silver holds one observation per run - accumulate every historical
    observation for this watcher into the cumulative timeseries/summary."""
    client = get_client()
    ensure_bucket(client, GOLD_BUCKET)

    silver_keys = sorted(list_keys(client, SILVER_BUCKET, prefix=f"price/{watcher_id}/"))
    frames = [read_parquet_bytes(get_bytes(client, SILVER_BUCKET, key)) for key in silver_keys]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df = df.sort_values("timestamp").reset_index(drop=True)

    timeseries_key = f"price/{watcher_id}/{run_ts}_timeseries.parquet"
    put_bytes(client, GOLD_BUCKET, timeseries_key, write_parquet_bytes(df))

    summary_df = build_summary_single_series(df)
    summary_key = f"price/{watcher_id}/{run_ts}_summary.parquet"
    put_bytes(client, GOLD_BUCKET, summary_key, write_parquet_bytes(summary_df))

    summary_row = summary_df.iloc[0].to_dict() if not summary_df.empty else None
    return {
        "timeseries_key": timeseries_key,
        "summary_key": summary_key,
        "records_count": len(df),
        "summary_row": summary_row,
    }


def transform_silver_to_gold(watcher: dict, silver_key: str, run_ts: str) -> dict:
    """Dispatch silver-to-gold transformation based on `watcher["watcher_type"]`, then record metadata."""
    watcher_id = watcher["id"]
    watcher_type = watcher["watcher_type"]

    if watcher_type == "eurostat":
        result = eurostat_silver_to_gold(watcher_id, silver_key, run_ts)
    elif watcher_type == "price":
        result = price_silver_to_gold(watcher_id, run_ts)
    else:
        raise ValueError(f"Unsupported watcher_type for gold transformation: {watcher_type!r}")

    _record_metadata(
        watcher_id=watcher_id,
        run_ts=run_ts,
        timeseries_key=result["timeseries_key"],
        summary_key=result["summary_key"],
        records_count=result["records_count"],
    )

    if result.get("summary_row") is not None:
        evaluate_and_notify(watcher, result["summary_row"])

    return result


def _record_metadata(
    watcher_id: int,
    run_ts: str,
    timeseries_key: str,
    summary_key: str,
    records_count: int,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    engine = get_app_db_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO watcher_state (watcher_id, latest_gold_timeseries_key, latest_gold_summary_key, updated_at)
                VALUES (:watcher_id, :timeseries_key, :summary_key, now())
                ON CONFLICT (watcher_id) DO UPDATE SET
                    latest_gold_timeseries_key = EXCLUDED.latest_gold_timeseries_key,
                    latest_gold_summary_key = EXCLUDED.latest_gold_summary_key,
                    updated_at = now()
                """
            ),
            {"watcher_id": watcher_id, "timeseries_key": timeseries_key, "summary_key": summary_key},
        )
        conn.execute(
            text(
                """
                INSERT INTO runs (watcher_id, run_ts, status, error_message, records_count, gold_key)
                VALUES (:watcher_id, :run_ts, :status, :error_message, :records_count, :summary_key)
                """
            ),
            {
                "watcher_id": watcher_id,
                "run_ts": run_ts,
                "status": status,
                "error_message": error_message,
                "records_count": records_count,
                "summary_key": summary_key,
            },
        )


def record_failed_run(watcher_id: int, run_ts: str, error_message: str) -> None:
    """Record a failed run without touching watcher_state (no new gold output produced)."""
    engine = get_app_db_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO runs (watcher_id, run_ts, status, error_message)
                VALUES (:watcher_id, :run_ts, 'failed', :error_message)
                """
            ),
            {"watcher_id": watcher_id, "run_ts": run_ts, "error_message": error_message},
        )
