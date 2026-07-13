FROM apache/airflow:2.9.3-python3.11

COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Install the shared ingestion package (bronze/silver/gold + Eurostat client) in editable mode
# so the DAG can import it directly. Build context is the repo root (see docker-compose.yml).
COPY --chown=airflow:root ingestion /opt/ingestion
RUN pip install --no-cache-dir -e /opt/ingestion
