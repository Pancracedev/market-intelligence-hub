"""Standalone entrypoints for running the pipeline without Airflow.

Used by GitLab CI scheduled pipelines (see .gitlab-ci.yml) as a serverless
alternative to the Airflow scheduler: each command runs once and exits,
instead of Airflow's long-running scheduler process.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone


def run_watchers() -> int:
    """Fan out ingest -> silver -> gold across all watchers currently due."""
    from ingestion.bronze import ingest_watcher_to_bronze
    from ingestion.gold import record_failed_run, transform_silver_to_gold
    from ingestion.scheduling import get_due_watchers
    from ingestion.silver import transform_bronze_to_silver

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    watchers = get_due_watchers()
    print(f"[{run_ts}] {len(watchers)} watcher(s) due")

    failures = 0
    for watcher in watchers:
        watcher_id = watcher["id"]
        try:
            bronze_key = ingest_watcher_to_bronze(watcher, run_ts=run_ts)
            silver_key = transform_bronze_to_silver(watcher, bronze_key, run_ts)
            transform_silver_to_gold(watcher, silver_key, run_ts)
            print(f"  watcher {watcher_id}: ok")
        except Exception as exc:  # noqa: BLE001 - one watcher's failure must not stop the rest
            record_failed_run(watcher_id, run_ts, str(exc))
            print(f"  watcher {watcher_id}: FAILED - {exc}", file=sys.stderr)
            failures += 1

    return 1 if failures else 0


def run_digest() -> int:
    """Generate and send the weekly AI digest to every user with active watchers."""
    from ingestion.digest import generate_weekly_digest, get_users_with_active_watchers

    users = get_users_with_active_watchers()
    print(f"{len(users)} recipient(s)")

    failures = 0
    for user in users:
        try:
            generate_weekly_digest(user["id"], user["email"])
            print(f"  user {user['id']}: ok")
        except Exception as exc:  # noqa: BLE001 - one user's failure must not stop the rest
            print(f"  user {user['id']}: FAILED - {exc}", file=sys.stderr)
            failures += 1

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run-watchers", "run-digest"])
    args = parser.parse_args()

    if args.command == "run-watchers":
        return run_watchers()
    return run_digest()


if __name__ == "__main__":
    sys.exit(main())
