"""Client for the Eurostat statistics API (JSON-stat 2.0 format, no API key required).

Docs: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# Sane defaults for retrying against a public, rate-limited API.
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2.0


class EurostatAPIError(RuntimeError):
    """Raised when the Eurostat API returns an unusable response."""


@dataclass(frozen=True)
class EurostatRecord:
    """One observation from a Eurostat JSON-stat dataset, flattened for downstream use."""

    dataset_code: str
    geo: str
    time_period: str
    value: float
    unit: str | None = None
    indicator: str | None = None


def fetch_dataset(
    dataset_code: str,
    filters: dict[str, str] | None = None,
    session: requests.Session | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Fetch a raw JSON-stat payload for a Eurostat dataset, with retries on transient errors."""
    session = session or requests.Session()
    params = {"format": "JSON", "lang": "EN"}
    if filters:
        params.update(filters)

    url = f"{EUROSTAT_BASE_URL}/{dataset_code}"
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 429:
                raise EurostatAPIError(f"Rate limited by Eurostat API (attempt {attempt})")
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, EurostatAPIError) as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)

    raise EurostatAPIError(
        f"Failed to fetch dataset '{dataset_code}' after {max_retries} attempts"
    ) from last_error


def parse_jsonstat(payload: dict, dataset_code: str) -> list[EurostatRecord]:
    """Flatten a JSON-stat 2.0 payload into a list of EurostatRecord.

    JSON-stat encodes observations as a sparse map keyed by a flat "mixed-radix" index
    computed from the size of each dimension, in the order given by `payload["id"]`.
    """
    dim_ids: list[str] = payload.get("id", [])
    sizes: list[int] = payload.get("size", [])
    dimensions: dict = payload.get("dimension", {})
    values: dict[str, float] = payload.get("value", {}) or {}

    if not dim_ids or not sizes:
        return []

    # Build, for each dimension, an ordered list of category codes (not human labels,
    # so downstream joins/aggregations key on stable codes like "FR" rather than "France").
    dim_labels: dict[str, list[str]] = {}
    for dim_id in dim_ids:
        category = dimensions.get(dim_id, {}).get("category", {})
        index = category.get("index", {})
        # index maps category_key -> position; invert to get position -> key
        ordered_keys = [None] * len(index)
        for key, position in index.items():
            ordered_keys[position] = key
        dim_labels[dim_id] = ordered_keys

    records: list[EurostatRecord] = []
    for flat_key, value in values.items():
        if value is None:
            continue
        flat_index = int(flat_key)
        # Decompose flat_index into per-dimension indices (mixed-radix, last dim fastest).
        coords = [0] * len(sizes)
        remainder = flat_index
        for i in range(len(sizes) - 1, -1, -1):
            coords[i] = remainder % sizes[i]
            remainder //= sizes[i]

        dim_values = {
            dim_id: dim_labels[dim_id][coord] for dim_id, coord in zip(dim_ids, coords)
        }

        records.append(
            EurostatRecord(
                dataset_code=dataset_code,
                geo=dim_values.get("geo", "UNKNOWN"),
                time_period=dim_values.get("time", "UNKNOWN"),
                value=float(value),
                unit=dim_values.get("unit"),
                indicator=dim_values.get("indic") or dim_values.get("coicop"),
            )
        )

    return records


def fetch_records(
    dataset_code: str,
    filters: dict[str, str] | None = None,
    session: requests.Session | None = None,
) -> list[EurostatRecord]:
    """Fetch and flatten a Eurostat dataset in one call."""
    payload = fetch_dataset(dataset_code, filters=filters, session=session)
    return parse_jsonstat(payload, dataset_code)
