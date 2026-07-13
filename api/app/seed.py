"""Seeds a demo account on startup so a fresh clone/deploy has default credentials to log
in with immediately - controlled by SEED_DEMO_USER (default "true"), meant for local/demo
environments only.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"


def ensure_demo_user(db: Session) -> None:
    if os.environ.get("SEED_DEMO_USER", "true").lower() != "true":
        return

    existing = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
    if existing is not None:
        return

    db.add(
        User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
