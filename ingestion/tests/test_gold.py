import pandas as pd

from ingestion.gold import build_summary


def test_build_summary_computes_delta_per_geo():
    df = pd.DataFrame(
        [
            {"geo": "FR", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-01", "value": 2.0},
            {"geo": "FR", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-02", "value": 2.5},
            {"geo": "DE", "dataset_code": "ds", "indicator": "CP00", "unit": "PCH", "time_period": "2024-01", "value": 1.0},
        ]
    )

    summary = build_summary(df)

    fr = summary[summary["geo"] == "FR"].iloc[0]
    assert fr["latest_value"] == 2.5
    assert fr["previous_value"] == 2.0
    assert fr["delta"] == 0.5

    de = summary[summary["geo"] == "DE"].iloc[0]
    assert de["previous_value"] is None or pd.isna(de["previous_value"])
    assert pd.isna(de["delta"])

    # sorted descending by delta: FR (0.5) should rank above DE (NaN, placed last)
    assert summary.iloc[0]["geo"] == "FR"


def test_build_summary_empty_input():
    df = pd.DataFrame()
    assert build_summary(df).empty
