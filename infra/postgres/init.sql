-- Metadata schema for the app-db (isolated from Airflow's own metadata database).

CREATE TABLE IF NOT EXISTS users (
    id                        SERIAL PRIMARY KEY,
    email                     TEXT NOT NULL UNIQUE,
    hashed_password           TEXT NOT NULL,
    is_active                 BOOLEAN NOT NULL DEFAULT true,
    accepted_scraping_terms_at TIMESTAMPTZ,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Generic watcher: what a user wants tracked. `config` holds type-specific fields
-- (validated at the API layer via Pydantic, not DB constraints):
--   price:    {"url": "...", "css_selector": "...", "currency": "EUR"}
--   trend:    {"keyword": "...", "geo": "FR", "timeframe": "today 12-m"}
--   eurostat: {"dataset_code": "prc_hicp_manr", "filters": {"geo": "FR"}}
CREATE TABLE IF NOT EXISTS watchers (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    watcher_type    TEXT NOT NULL CHECK (watcher_type IN ('price', 'trend', 'eurostat')),
    name            TEXT NOT NULL,
    config          JSONB NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    schedule        TEXT NOT NULL DEFAULT '@daily',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_watchers_user_id ON watchers (user_id);
CREATE INDEX IF NOT EXISTS idx_watchers_active ON watchers (is_active) WHERE is_active;

-- Per-watcher latest-pointer, replaces the old per-dataset `datasets` table.
CREATE TABLE IF NOT EXISTS watcher_state (
    watcher_id                  INTEGER PRIMARY KEY REFERENCES watchers(id) ON DELETE CASCADE,
    latest_gold_timeseries_key  TEXT,
    latest_gold_summary_key     TEXT,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Run history, now scoped to a watcher rather than a hardcoded dataset_code.
CREATE TABLE IF NOT EXISTS runs (
    id             SERIAL PRIMARY KEY,
    watcher_id     INTEGER NOT NULL REFERENCES watchers(id) ON DELETE CASCADE,
    run_ts         TEXT NOT NULL,
    status         TEXT NOT NULL,
    error_message  TEXT,
    records_count  INTEGER,
    gold_key       TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runs_watcher_id ON runs (watcher_id);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC);

-- Per-domain rate limiting for generic scraping (Postgres-backed since Airflow's
-- LocalExecutor runs each task in its own process - an in-process limiter wouldn't
-- be shared across concurrent scrape tasks).
CREATE TABLE IF NOT EXISTS domain_rate_limits (
    domain          TEXT PRIMARY KEY,
    last_request_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
