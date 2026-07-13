"""Bronze zone: dump raw source payloads to the data lake, untouched, timestamped."""

from __future__ import annotations

import os

from .sources.eurostat import fetch_dataset
from .storage import ensure_bucket, get_client, put_json

BRONZE_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")


def ingest_eurostat_to_bronze(dataset_code: str, run_ts: str, filters: dict | None = None) -> str:
    """Fetch a Eurostat dataset and store the raw JSON-stat payload in the bronze zone.

    Args:
        dataset_code: Eurostat dataset identifier (e.g. "prc_hicp_manr").
        run_ts: ISO-8601-safe timestamp string identifying this pipeline run (e.g. "20260713T120000").
        filters: Optional Eurostat query filters (e.g. {"geo": "FR"}).

    Returns:
        The object key written in the bronze bucket.
    """
    payload = fetch_dataset(dataset_code, filters=filters)

    client = get_client()
    ensure_bucket(client, BRONZE_BUCKET)

    key = f"eurostat/{dataset_code}/{run_ts}.json"
    put_json(client, BRONZE_BUCKET, key, payload)
    return key
