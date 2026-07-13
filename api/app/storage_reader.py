"""Read-only helper for the API to fetch Gold-zone Parquet files from MinIO.

Reuses ingestion.storage rather than duplicating the boto3/MinIO client setup.
"""

import os

from ingestion.storage import get_bytes, get_client, read_parquet_bytes

GOLD_BUCKET = os.environ.get("MINIO_BUCKET_GOLD", "gold")


def read_gold_parquet_records(key: str) -> list[dict]:
    client = get_client()
    df = read_parquet_bytes(get_bytes(client, GOLD_BUCKET, key))
    return df.to_dict(orient="records")
