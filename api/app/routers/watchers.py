from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import NotificationLog, Run, User, Watcher
from ..schemas import NotificationResponse, RunResponse, WatcherCreate, WatcherResponse, WatcherUpdate
from ..storage_reader import read_gold_parquet_records

router = APIRouter(prefix="/watchers", tags=["watchers"])


def _to_response(watcher: Watcher) -> WatcherResponse:
    state = watcher.state
    return WatcherResponse(
        id=watcher.id,
        watcher_type=watcher.watcher_type,
        name=watcher.name,
        config=watcher.config,
        is_active=watcher.is_active,
        schedule=watcher.schedule,
        alert_price_drop_pct=watcher.alert_price_drop_pct,
        alert_on_stock_out=watcher.alert_on_stock_out,
        alert_on_promo=watcher.alert_on_promo,
        created_at=watcher.created_at,
        updated_at=watcher.updated_at,
        latest_gold_timeseries_key=state.latest_gold_timeseries_key if state else None,
        latest_gold_summary_key=state.latest_gold_summary_key if state else None,
    )


def _get_owned_watcher(watcher_id: int, current_user: User, db: Session) -> Watcher:
    watcher = db.execute(
        select(Watcher).where(Watcher.id == watcher_id, Watcher.user_id == current_user.id)
    ).scalar_one_or_none()
    if watcher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watcher not found")
    return watcher


@router.get("", response_model=list[WatcherResponse])
def list_watchers(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WatcherResponse]:
    watchers = db.execute(select(Watcher).where(Watcher.user_id == current_user.id)).scalars().all()
    return [_to_response(w) for w in watchers]


@router.post("", response_model=WatcherResponse, status_code=status.HTTP_201_CREATED)
def create_watcher(
    payload: WatcherCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatcherResponse:
    now = datetime.now(timezone.utc)
    watcher = Watcher(
        user_id=current_user.id,
        watcher_type=payload.watcher_type,
        name=payload.name,
        config=payload.config.model_dump(),
        schedule=payload.schedule,
        alert_price_drop_pct=payload.alert_price_drop_pct,
        alert_on_stock_out=payload.alert_on_stock_out,
        alert_on_promo=payload.alert_on_promo,
        created_at=now,
        updated_at=now,
    )
    db.add(watcher)
    db.commit()
    db.refresh(watcher)
    return _to_response(watcher)


@router.get("/{watcher_id}", response_model=WatcherResponse)
def get_watcher(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatcherResponse:
    return _to_response(_get_owned_watcher(watcher_id, current_user, db))


@router.patch("/{watcher_id}", response_model=WatcherResponse)
def update_watcher(
    watcher_id: int,
    payload: WatcherUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatcherResponse:
    watcher = _get_owned_watcher(watcher_id, current_user, db)
    if payload.name is not None:
        watcher.name = payload.name
    if payload.config is not None:
        watcher.config = payload.config.model_dump()
    if payload.schedule is not None:
        watcher.schedule = payload.schedule
    if payload.is_active is not None:
        watcher.is_active = payload.is_active
    if payload.alert_price_drop_pct is not None:
        watcher.alert_price_drop_pct = payload.alert_price_drop_pct
    if payload.alert_on_stock_out is not None:
        watcher.alert_on_stock_out = payload.alert_on_stock_out
    if payload.alert_on_promo is not None:
        watcher.alert_on_promo = payload.alert_on_promo
    watcher.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(watcher)
    return _to_response(watcher)


@router.delete("/{watcher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watcher(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    watcher = _get_owned_watcher(watcher_id, current_user, db)
    db.delete(watcher)
    db.commit()


@router.get("/{watcher_id}/timeseries")
def get_watcher_timeseries(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    watcher = _get_owned_watcher(watcher_id, current_user, db)
    state = watcher.state
    if state is None or not state.latest_gold_timeseries_key:
        return []
    return read_gold_parquet_records(state.latest_gold_timeseries_key)


@router.get("/{watcher_id}/summary")
def get_watcher_summary(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    watcher = _get_owned_watcher(watcher_id, current_user, db)
    state = watcher.state
    if state is None or not state.latest_gold_summary_key:
        return []
    return read_gold_parquet_records(state.latest_gold_summary_key)


@router.get("/{watcher_id}/alerts", response_model=list[NotificationResponse])
def list_watcher_alerts(
    watcher_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    _get_owned_watcher(watcher_id, current_user, db)
    stmt = (
        select(NotificationLog)
        .where(NotificationLog.watcher_id == watcher_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


runs_router = APIRouter(prefix="/runs", tags=["runs"])


@runs_router.get("", response_model=list[RunResponse])
def list_runs(
    watcher_id: int | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RunResponse]:
    stmt = (
        select(Run)
        .join(Watcher, Run.watcher_id == Watcher.id)
        .where(Watcher.user_id == current_user.id)
        .order_by(Run.created_at.desc())
        .limit(limit)
    )
    if watcher_id is not None:
        stmt = stmt.where(Run.watcher_id == watcher_id)

    runs = db.execute(stmt).scalars().all()
    return list(runs)
