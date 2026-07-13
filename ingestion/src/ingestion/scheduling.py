"""Determines which active watchers are "due" for a new pipeline run, based on their own
per-watcher `schedule` cron string and the last time they produced gold output.

Used by the Airflow dynamic-mapping DAG (`airflow/dags/watcher_pipeline.py`) to fan out
one run per due watcher on a single fixed-cadence DAG, instead of one DAG per watcher.
"""

from __future__ import annotations

from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import text

from .db import get_app_db_engine

# Airflow-style cron presets, since `schedule` is meant to be user-friendly - croniter
# itself only understands raw 5-field cron expressions.
_CRON_PRESETS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}


def _to_cron_expression(schedule: str) -> str:
    return _CRON_PRESETS.get(schedule, schedule)


def _is_due(schedule: str, last_run_at: datetime | None, now: datetime) -> bool:
    if last_run_at is None:
        return True

    cron_expr = _to_cron_expression(schedule)
    next_due = croniter(cron_expr, last_run_at).get_next(datetime)
    if next_due.tzinfo is None:
        next_due = next_due.replace(tzinfo=timezone.utc)
    return next_due <= now


def get_due_watchers(now: datetime | None = None) -> list[dict]:
    """Return active watchers whose per-watcher schedule says they're due for a run now."""
    now = now or datetime.now(timezone.utc)

    engine = get_app_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT w.id, w.watcher_type, w.name, w.config, w.schedule, ws.updated_at
                FROM watchers w
                LEFT JOIN watcher_state ws ON ws.watcher_id = w.id
                WHERE w.is_active
                """
            )
        ).fetchall()

    due = []
    for row in rows:
        watcher_id, watcher_type, name, config, schedule, last_run_at = row
        if _is_due(schedule, last_run_at, now):
            due.append(
                {
                    "id": watcher_id,
                    "watcher_type": watcher_type,
                    "name": name,
                    "config": config,
                    "schedule": schedule,
                }
            )
    return due
