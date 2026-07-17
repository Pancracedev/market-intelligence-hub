"""Thin wrapper around boto3 S3 client, configured for MinIO."""

from __future__ import annotations

import io
import json
import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def get_client():
    # .strip() guards against a stray trailing newline/space from copy-pasting a value into
    # a dashboard env var field - otherwise it ends up inside the signed auth header and
    # every request fails with a cryptic "Invalid header value" error.
    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000").strip()
    access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin").strip()
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123").strip()
    scheme = "https" if os.environ.get("MINIO_SECURE", "false").strip().lower() == "true" else "http"
    # Cloudflare R2 (and other non-MinIO S3-compatible providers) require a region even
    # though they don't use it for routing; R2 itself expects the literal value "auto".
    region = os.environ.get("STORAGE_REGION", "us-east-1").strip()

    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(client, bucket: str) -> None:
    # head_bucket (not list_buckets) so this works with an S3 token scoped to a single
    # bucket (e.g. Cloudflare R2's per-bucket API tokens) - list_buckets is an
    # account-wide operation such tokens are typically denied.
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        status = exc.response.get("Error", {}).get("Code")
        if status not in ("404", "NoSuchBucket"):
            raise
        client.create_bucket(Bucket=bucket)


def put_json(client, bucket: str, key: str, payload: dict | list) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")


def get_json(client, bucket: str, key: str) -> dict | list:
    obj = client.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def put_bytes(client, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def get_bytes(client, bucket: str, key: str) -> bytes:
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def list_keys(client, bucket: str, prefix: str = "") -> list[str]:
    paginator = client.get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def latest_key(client, bucket: str, prefix: str = "") -> str | None:
    keys = list_keys(client, bucket, prefix=prefix)
    return max(keys) if keys else None


def read_parquet_bytes(data: bytes):
    import pandas as pd

    return pd.read_parquet(io.BytesIO(data))


def write_parquet_bytes(df) -> bytes:
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    return buffer.getvalue()
