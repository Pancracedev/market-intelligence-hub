from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    accepted_scraping_terms_at = Column(DateTime(timezone=True))
    slack_webhook_url = Column(String)
    created_at = Column(DateTime(timezone=True))

    watchers = relationship("Watcher", back_populates="user", cascade="all, delete-orphan")


class Watcher(Base):
    __tablename__ = "watchers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    watcher_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    schedule = Column(String, nullable=False, default="@daily")
    alert_price_drop_pct = Column(Float)
    alert_on_stock_out = Column(Boolean, nullable=False, default=True)
    alert_on_promo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="watchers")
    state = relationship(
        "WatcherState", back_populates="watcher", uselist=False, cascade="all, delete-orphan"
    )
    runs = relationship("Run", back_populates="watcher", cascade="all, delete-orphan")


class WatcherState(Base):
    __tablename__ = "watcher_state"

    watcher_id = Column(Integer, ForeignKey("watchers.id", ondelete="CASCADE"), primary_key=True)
    latest_gold_timeseries_key = Column(String)
    latest_gold_summary_key = Column(String)
    updated_at = Column(DateTime(timezone=True))

    watcher = relationship("Watcher", back_populates="state")


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    watcher_id = Column(Integer, ForeignKey("watchers.id", ondelete="CASCADE"), nullable=False)
    run_ts = Column(String, nullable=False)
    status = Column(String, nullable=False)
    error_message = Column(Text)
    records_count = Column(Integer)
    gold_key = Column(String)
    created_at = Column(DateTime(timezone=True))

    watcher = relationship("Watcher", back_populates="runs")


class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(Integer, primary_key=True)
    watcher_id = Column(Integer, ForeignKey("watchers.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True))
