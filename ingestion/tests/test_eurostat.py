import pytest
import responses

from ingestion.sources.eurostat import (
    EurostatAPIError,
    fetch_dataset,
    parse_jsonstat,
)

SAMPLE_JSONSTAT = {
    "id": ["geo", "time"],
    "size": [2, 2],
    "dimension": {
        "geo": {
            "category": {
                "index": {"FR": 0, "DE": 1},
                "label": {"FR": "France", "DE": "Germany"},
            }
        },
        "time": {
            "category": {
                "index": {"2024-01": 0, "2024-02": 1},
                "label": {"2024-01": "January 2024", "2024-02": "February 2024"},
            }
        },
    },
    "value": {"0": 2.1, "1": 2.3, "2": 1.9, "3": 2.0},
}


def test_parse_jsonstat_flattens_all_observations():
    records = parse_jsonstat(SAMPLE_JSONSTAT, dataset_code="prc_hicp_manr")

    assert len(records) == 4
    by_key = {(r.geo, r.time_period): r.value for r in records}
    assert by_key[("FR", "2024-01")] == 2.1
    assert by_key[("FR", "2024-02")] == 2.3
    assert by_key[("DE", "2024-01")] == 1.9
    assert by_key[("DE", "2024-02")] == 2.0
    assert all(r.dataset_code == "prc_hicp_manr" for r in records)


def test_parse_jsonstat_skips_null_values():
    payload = dict(SAMPLE_JSONSTAT, value={"0": 2.1, "1": None})
    records = parse_jsonstat(payload, dataset_code="prc_hicp_manr")
    assert len(records) == 1


def test_parse_jsonstat_empty_payload_returns_empty_list():
    assert parse_jsonstat({}, dataset_code="x") == []


@responses.activate
def test_fetch_dataset_success():
    responses.add(
        responses.GET,
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr",
        json=SAMPLE_JSONSTAT,
        status=200,
    )
    payload = fetch_dataset("prc_hicp_manr")
    assert payload == SAMPLE_JSONSTAT


@responses.activate
def test_fetch_dataset_retries_then_succeeds():
    url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr"
    responses.add(responses.GET, url, status=429)
    responses.add(responses.GET, url, json=SAMPLE_JSONSTAT, status=200)

    payload = fetch_dataset("prc_hicp_manr", max_retries=2, backoff_seconds=0)
    assert payload == SAMPLE_JSONSTAT


@responses.activate
def test_fetch_dataset_raises_after_exhausting_retries():
    url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr"
    responses.add(responses.GET, url, status=500)
    responses.add(responses.GET, url, status=500)

    with pytest.raises(EurostatAPIError):
        fetch_dataset("prc_hicp_manr", max_retries=2, backoff_seconds=0)
