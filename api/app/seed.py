"""Seeds a demo account on startup so a fresh clone/deploy has default credentials to log
in with immediately - controlled by SEED_DEMO_USER (default "true"). Email/password default
to demo@example.com / demo12345 (fine for local dev) but can be overridden via
DEMO_USER_EMAIL / DEMO_USER_PASSWORD - do this for any public demo deployment.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import User


def ensure_demo_user(db: Session) -> None:
    if os.environ.get("SEED_DEMO_USER", "true").lower() != "true":
        return

    demo_email = os.environ.get("DEMO_USER_EMAIL", "demo@example.com")
    demo_password = os.environ.get("DEMO_USER_PASSWORD", "demo12345")

    existing = db.execute(select(User).where(User.email == demo_email)).scalar_one_or_none()
    if existing is not None:
        return

    db.add(
        User(
            email=demo_email,
            hashed_password=hash_password(demo_password),
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
