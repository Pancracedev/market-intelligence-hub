"""Per-domain rate limiting for generic scraping, backed by Postgres.

Airflow's LocalExecutor runs each task in its own process, so an in-process rate
limiter would not be shared across concurrent scrape tasks - the limiter state is
persisted in the `domain_rate_limits` table instead.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

from sqlalchemy import text

from .db import get_app_db_engine

DEFAULT_MIN_INTERVAL_SECONDS = 5.0


def _domain_of(url: str) -> str:
    return urlparse(url).netloc


def wait_if_needed(url: str, min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS) -> None:
    """Block until at least `min_interval_seconds` have passed since the last request
    to this domain, then record this request's timestamp."""
    domain = _domain_of(url)
    engine = get_app_db_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT last_request_at FROM domain_rate_limits WHERE domain = :domain FOR UPDATE"),
            {"domain": domain},
        ).fetchone()

        if row is not None:
            elapsed = time.time() - row[0].timestamp()
            if elapsed < min_interval_seconds:
                time.sleep(min_interval_seconds - elapsed)

        conn.execute(
            text(
                """
                INSERT INTO domain_rate_limits (domain, last_request_at)
                VALUES (:domain, now())
                ON CONFLICT (domain) DO UPDATE SET last_request_at = now()
                """
            ),
            {"domain": domain},
        )
