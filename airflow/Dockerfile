FROM apache/airflow:2.9.3-python3.11

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Install the shared ingestion package (bronze/silver/gold + Eurostat client) in editable mode
# so the DAG can import it directly. Its pyproject.toml is the single source of truth for
# dependencies (requests, boto3, pandas, pyarrow, sqlalchemy, psycopg2-binary).
# Build context is the repo root (see docker-compose.yml).
COPY --chown=airflow:root ingestion /opt/ingestion

# The base image's Python is a pseudo-venv rooted at /home/airflow/.local (see
# /home/airflow/.local/pyvenv.cfg) - that's the interpreter Airflow actually runs, so it must be
# targeted explicitly rather than the real /usr/local prefix uv would pick by default.
# The Airflow constraints file pins versions (notably SQLAlchemy < 2.0) that Airflow 2.9.3 itself
# requires - without it, installing `ingestion`'s deps would upgrade SQLAlchemy/pandas and break
# Airflow's own ORM models.
RUN uv pip install --python /home/airflow/.local/bin/python3 --no-cache -e /opt/ingestion \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.11.txt"
