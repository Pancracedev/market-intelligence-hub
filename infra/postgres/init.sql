-- Metadata schema for the app-db (isolated from Airflow's own metadata database).

CREATE TABLE IF NOT EXISTS datasets (
    dataset_code                TEXT PRIMARY KEY,
    latest_gold_timeseries_key  TEXT,
    latest_gold_summary_key     TEXT,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    id             SERIAL PRIMARY KEY,
    run_ts         TEXT NOT NULL,
    dataset_code   TEXT NOT NULL,
    status         TEXT NOT NULL,
    records_count  INTEGER,
    gold_key       TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runs_dataset_code ON runs (dataset_code);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC);
