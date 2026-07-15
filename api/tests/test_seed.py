import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, User
from app.seed import ensure_demo_user

DEMO_EMAIL = "demo@example.com"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_ensure_demo_user_creates_account_when_missing(db_session, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_USER", "true")
    ensure_demo_user(db_session)

    user = db_session.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
    assert user is not None


def test_ensure_demo_user_is_idempotent(db_session, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_USER", "true")
    ensure_demo_user(db_session)
    ensure_demo_user(db_session)

    users = db_session.execute(select(User).where(User.email == DEMO_EMAIL)).scalars().all()
    assert len(users) == 1


def test_ensure_demo_user_skipped_when_disabled(db_session, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_USER", "false")
    ensure_demo_user(db_session)

    user = db_session.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
    assert user is None


def test_ensure_demo_user_respects_email_override(db_session, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_USER", "true")
    monkeypatch.setenv("DEMO_USER_EMAIL", "showcase@example.com")
    ensure_demo_user(db_session)

    user = db_session.execute(
        select(User).where(User.email == "showcase@example.com")
    ).scalar_one_or_none()
    assert user is not None
