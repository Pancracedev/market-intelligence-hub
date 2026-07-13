import pandas as pd

from ingestion.gold import build_summary_by_geo, build_summary_single_series


def test_build_summary_by_geo_computes_delta_per_geo():
    df = pd.DataFrame(
        [
            {"geo": "FR", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-01", "value": 2.0},
            {"geo": "FR", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-02", "value": 2.5},
            {"geo": "DE", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-01", "value": 1.0},
        ]
    )

    summary = build_summary_by_geo(df)

    fr = summary[summary["geo"] == "FR"].iloc[0]
    assert fr["latest_value"] == 2.5
    assert fr["previous_value"] == 2.0
    assert fr["delta"] == 0.5

    de = summary[summary["geo"] == "DE"].iloc[0]
    assert de["previous_value"] is None or pd.isna(de["previous_value"])
    assert pd.isna(de["delta"])

    # sorted descending by delta: FR (0.5) should rank above DE (NaN, placed last)
    assert summary.iloc[0]["geo"] == "FR"


def test_build_summary_by_geo_empty_input():
    df = pd.DataFrame()
    assert build_summary_by_geo(df).empty


def test_build_summary_single_series_computes_delta():
    df = pd.DataFrame(
        [
            {"timestamp": "2026-01-01T00:00:00", "value": 19.99},
            {"timestamp": "2026-01-02T00:00:00", "value": 17.50},
        ]
    )

    summary = build_summary_single_series(df)

    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["latest_value"] == 17.50
    assert row["previous_value"] == 19.99
    assert row["delta"] == 17.50 - 19.99


def test_build_summary_single_series_single_observation_has_no_delta():
    df = pd.DataFrame([{"timestamp": "2026-01-01T00:00:00", "value": 19.99}])
    summary = build_summary_single_series(df)
    assert summary.iloc[0]["previous_value"] is None
    assert pd.isna(summary.iloc[0]["delta"])


def test_build_summary_single_series_empty_input():
    df = pd.DataFrame()
    assert build_summary_single_series(df).empty


def test_build_summary_single_series_passes_through_stock_and_promo():
    df = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01T00:00:00",
                "value": 29.99,
                "currency": "EUR",
                "in_stock": True,
                "is_promo": False,
                "discount_pct": None,
            },
            {
                "timestamp": "2026-01-02T00:00:00",
                "value": 19.99,
                "currency": "EUR",
                "in_stock": False,
                "is_promo": True,
                "discount_pct": 33.3,
            },
        ]
    )

    summary = build_summary_single_series(df)
    row = summary.iloc[0]

    assert bool(row["in_stock"]) is False
    assert bool(row["is_promo"]) is True
    assert row["discount_pct"] == 33.3
    assert row["currency"] == "EUR"
