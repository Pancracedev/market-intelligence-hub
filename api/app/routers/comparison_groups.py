from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..db import get_db
from ..models import ComparisonGroup, User
from ..routers.watchers import _to_response
from ..schemas import ComparisonGroupCreate, ComparisonGroupResponse, ComparisonGroupUpdate

router = APIRouter(prefix="/comparison-groups", tags=["comparison-groups"])


def _to_group_response(group: ComparisonGroup) -> ComparisonGroupResponse:
    return ComparisonGroupResponse(
        id=group.id,
        name=group.name,
        created_at=group.created_at,
        watchers=[_to_response(w) for w in group.watchers],
    )


def _get_owned_group(group_id: int, current_user: User, db: Session) -> ComparisonGroup:
    group = db.execute(
        select(ComparisonGroup)
        .options(selectinload(ComparisonGroup.watchers))
        .where(ComparisonGroup.id == group_id, ComparisonGroup.user_id == current_user.id)
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison group not found")
    return group


@router.get("", response_model=list[ComparisonGroupResponse])
def list_comparison_groups(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ComparisonGroupResponse]:
    groups = db.execute(
        select(ComparisonGroup)
        .options(selectinload(ComparisonGroup.watchers))
        .where(ComparisonGroup.user_id == current_user.id)
        .order_by(ComparisonGroup.created_at.desc())
    ).scalars().all()
    return [_to_group_response(g) for g in groups]


@router.post("", response_model=ComparisonGroupResponse, status_code=status.HTTP_201_CREATED)
def create_comparison_group(
    payload: ComparisonGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComparisonGroupResponse:
    group = ComparisonGroup(user_id=current_user.id, name=payload.name, created_at=datetime.now(timezone.utc))
    db.add(group)
    db.commit()
    db.refresh(group)
    return _to_group_response(group)


@router.get("/{group_id}", response_model=ComparisonGroupResponse)
def get_comparison_group(
    group_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ComparisonGroupResponse:
    return _to_group_response(_get_owned_group(group_id, current_user, db))


@router.patch("/{group_id}", response_model=ComparisonGroupResponse)
def update_comparison_group(
    group_id: int,
    payload: ComparisonGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComparisonGroupResponse:
    group = _get_owned_group(group_id, current_user, db)
    group.name = payload.name
    db.commit()
    db.refresh(group)
    return _to_group_response(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comparison_group(
    group_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    group = _get_owned_group(group_id, current_user, db)
    db.delete(group)
    db.commit()
