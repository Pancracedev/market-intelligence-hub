"""Streamlit dashboard for the Market Intelligence Hub.

Reads the latest Gold-zone Parquet files directly from MinIO and displays:
- a trend chart of the tracked indicator over time, per country
- a "biggest movers" table (largest period-over-period change)
- recent pipeline run history, via the metadata API
"""

import io
import os

import boto3
import pandas as pd
import requests
import streamlit as st
from botocore.client import Config

DATASET_CODE = os.environ.get("EUROSTAT_DATASET_CODE", "prc_hicp_manr")
GOLD_BUCKET = os.environ.get("MINIO_BUCKET_GOLD", "gold")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Market Intelligence Hub", layout="wide")


@st.cache_resource
def get_minio_client():
    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
    return boto3.client(
        "s3",
        endpoint_url=f"http://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )


def latest_gold_key(client, dataset_code: str, suffix: str) -> str | None:
    paginator = client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=GOLD_BUCKET, Prefix=f"eurostat/{dataset_code}/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(suffix):
                keys.append(obj["Key"])
    return max(keys) if keys else None


def read_parquet(client, key: str) -> pd.DataFrame:
    obj = client.get_object(Bucket=GOLD_BUCKET, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


st.title("📊 Market Intelligence Hub")
st.caption("Veille concurrentielle automatisée — pipeline Bronze / Silver / Gold sur données Eurostat")

client = get_minio_client()

try:
    timeseries_key = latest_gold_key(client, DATASET_CODE, "_timeseries.parquet")
    summary_key = latest_gold_key(client, DATASET_CODE, "_summary.parquet")
except Exception as exc:  # noqa: BLE001 - surface connectivity issues to the user
    st.error(f"Impossible de contacter MinIO : {exc}")
    st.stop()

if not timeseries_key or not summary_key:
    st.warning(
        "Aucune donnée Gold disponible pour le moment. "
        "Déclenchez le DAG `market_intelligence_pipeline` dans Airflow pour générer la première run."
    )
    st.stop()

timeseries_df = read_parquet(client, timeseries_key)
summary_df = read_parquet(client, summary_key)

st.subheader(f"Indicateur suivi : `{DATASET_CODE}`")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**Évolution par pays**")
    geo_options = sorted(timeseries_df["geo"].unique())
    default_selection = geo_options[:5] if len(geo_options) > 5 else geo_options
    selected_geos = st.multiselect("Pays", geo_options, default=default_selection)
    filtered = timeseries_df[timeseries_df["geo"].isin(selected_geos)]
    pivot = filtered.pivot_table(index="time_period", columns="geo", values="value")
    st.line_chart(pivot)

with col2:
    st.markdown("**Plus fortes variations (dernière période)**")
    st.dataframe(
        summary_df[["geo", "latest_period", "latest_value", "previous_value", "delta"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Historique des exécutions du pipeline")
try:
    runs = requests.get(f"{API_BASE_URL}/runs", params={"dataset_code": DATASET_CODE}, timeout=5).json()
    if runs:
        st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune exécution enregistrée pour ce dataset.")
except requests.RequestException as exc:
    st.warning(f"API indisponible : {exc}")
