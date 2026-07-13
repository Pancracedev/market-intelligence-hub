from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import DigestLog, User
from ..schemas import DigestResponse

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=list[DigestResponse])
def list_digests(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DigestResponse]:
    stmt = (
        select(DigestLog)
        .where(DigestLog.user_id == current_user.id)
        .order_by(DigestLog.generated_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/generate", response_model=DigestResponse, status_code=status.HTTP_201_CREATED)
def generate_digest_now(current_user: User = Depends(get_current_user)) -> DigestResponse:
    from ingestion.digest import generate_weekly_digest

    result = generate_weekly_digest(current_user.id, current_user.email)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun produit actif à résumer - ajoutez au moins un watcher avant de générer un digest.",
        )

    return DigestResponse(id=result["id"], content=result["content"], generated_at=result["generated_at"])
