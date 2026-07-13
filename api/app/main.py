from fastapi import Depends, FastAPI, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Dataset, Run

app = FastAPI(
    title="Market Intelligence Hub API",
    description="Metadata API for the automated competitive intelligence pipeline.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/datasets")
def list_datasets(db: Session = Depends(get_db)) -> list[dict]:
    datasets = db.execute(select(Dataset)).scalars().all()
    return [
        {
            "dataset_code": d.dataset_code,
            "latest_gold_timeseries_key": d.latest_gold_timeseries_key,
            "latest_gold_summary_key": d.latest_gold_summary_key,
            "updated_at": d.updated_at,
        }
        for d in datasets
    ]


@app.get("/runs")
def list_runs(
    dataset_code: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit)
    if dataset_code:
        stmt = stmt.where(Run.dataset_code == dataset_code)

    runs = db.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "run_ts": r.run_ts,
            "dataset_code": r.dataset_code,
            "status": r.status,
            "records_count": r.records_count,
            "gold_key": r.gold_key,
            "created_at": r.created_at,
        }
        for r in runs
    ]
