FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

# Build context is the repo root (see docker-compose.yml) - the `ingestion` package is a
# uv path dependency (see api/pyproject.toml's [tool.uv.sources]), copied as a sibling
# directory so its "../ingestion" relative path resolves inside the image too.
COPY ingestion /ingestion
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api/app ./app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
