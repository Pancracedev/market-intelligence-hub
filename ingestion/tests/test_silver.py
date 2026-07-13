from ingestion.silver import bronze_records_to_dataframe
from ingestion.sources.eurostat import EurostatRecord


def test_bronze_records_to_dataframe_cleans_and_sorts():
    records = [
        EurostatRecord("ds", "FR", "2024-02", 2.3, unit="PCH", indicator="CP00"),
        EurostatRecord("ds", "FR", "2024-01", 2.1, unit="PCH", indicator="CP00"),
        EurostatRecord("ds", "UNKNOWN", "2024-01", 9.9),
        EurostatRecord("ds", "DE", "UNKNOWN", 9.9),
    ]

    df = bronze_records_to_dataframe(records)

    assert len(df) == 2
    assert list(df["time_period"]) == ["2024-01", "2024-02"]
    assert set(df["geo"]) == {"FR"}


def test_bronze_records_to_dataframe_drops_duplicates():
    records = [
        EurostatRecord("ds", "FR", "2024-01", 2.1, unit="PCH", indicator="CP00"),
        EurostatRecord("ds", "FR", "2024-01", 2.1, unit="PCH", indicator="CP00"),
    ]
    df = bronze_records_to_dataframe(records)
    assert len(df) == 1


def test_bronze_records_to_dataframe_empty_input():
    df = bronze_records_to_dataframe([])
    assert df.empty
