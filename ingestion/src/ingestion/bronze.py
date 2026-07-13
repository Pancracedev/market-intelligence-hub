"""Bronze zone: dump raw source payloads to the data lake, untouched, timestamped.

Object keys are partitioned by `{watcher_type}/{watcher_id}/{run_ts}...` rather than a
hardcoded dataset code - this naturally isolates each user's watcher data (watcher_id is
never guessable/shared across users) while keeping the existing zone-prefix pattern that
`storage.list_keys`/`latest_key` already rely on.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from .sources.eurostat import fetch_dataset
from .sources.price_scraper import fetch_price
from .sources.product_detector import detect_product
from .storage import ensure_bucket, get_client, put_json

BRONZE_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")


def ingest_eurostat_to_bronze(
    watcher_id: int, dataset_code: str, run_ts: str, filters: dict | None = None
) -> str:
    """Fetch a Eurostat dataset and store the raw JSON-stat payload in the bronze zone."""
    payload = fetch_dataset(dataset_code, filters=filters)

    client = get_client()
    ensure_bucket(client, BRONZE_BUCKET)

    key = f"eurostat/{watcher_id}/{run_ts}.json"
    put_json(client, BRONZE_BUCKET, key, payload)
    return key


def ingest_price_auto_to_bronze(watcher_id: int, url: str, run_ts: str) -> str:
    """Auto-detect price/stock from structured data (JSON-LD/Open Graph/microdata) - no
    CSS selector required, for users who don't know what one is."""
    detected = detect_product(url)

    client = get_client()
    ensure_bucket(client, BRONZE_BUCKET)

    payload = {
        "url": url,
        "value": detected["value"],
        "currency": detected["currency"],
        "in_stock": detected["in_stock"],
        "detection_method": detected["method"],
        "original_value": None,
        "is_promo": False,
        "discount_pct": None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    key = f"price/{watcher_id}/{run_ts}.json"
    put_json(client, BRONZE_BUCKET, key, payload)
    return key


def ingest_price_manual_to_bronze(
    watcher_id: int,
    url: str,
    css_selector: str,
    run_ts: str,
    currency: str = "EUR",
    stock_selector: str | None = None,
    promo_selector: str | None = None,
) -> str:
    """Scrape a user-supplied product page via an explicit CSS selector (advanced mode) and
    store the raw extracted values in the bronze zone."""
    record = fetch_price(
        url,
        css_selector,
        currency=currency,
        stock_selector=stock_selector,
        promo_selector=promo_selector,
    )

    client = get_client()
    ensure_bucket(client, BRONZE_BUCKET)

    payload = {
        "url": record.url,
        "css_selector": record.css_selector,
        "raw_text": record.raw_text,
        "value": record.value,
        "currency": record.currency,
        "in_stock": record.in_stock,
        "stock_text": record.stock_text,
        "original_value": record.original_value,
        "is_promo": record.is_promo,
        "discount_pct": record.discount_pct,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    key = f"price/{watcher_id}/{run_ts}.json"
    put_json(client, BRONZE_BUCKET, key, payload)
    return key


def ingest_watcher_to_bronze(watcher: dict, run_ts: str) -> str:
    """Dispatch bronze ingestion based on `watcher["watcher_type"]`."""
    watcher_id = watcher["id"]
    config = watcher["config"]
    watcher_type = watcher["watcher_type"]

    if watcher_type == "eurostat":
        return ingest_eurostat_to_bronze(
            watcher_id, config["dataset_code"], run_ts, filters=config.get("filters")
        )
    if watcher_type == "price":
        if config.get("mode", "auto") == "manual":
            return ingest_price_manual_to_bronze(
                watcher_id,
                config["url"],
                config["css_selector"],
                run_ts,
                currency=config.get("currency", "EUR"),
                stock_selector=config.get("stock_selector"),
                promo_selector=config.get("promo_selector"),
            )
        return ingest_price_auto_to_bronze(watcher_id, config["url"], run_ts)
    raise ValueError(f"Unsupported watcher_type for bronze ingestion: {watcher_type!r}")
