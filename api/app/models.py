from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_code = Column(String, primary_key=True)
    latest_gold_timeseries_key = Column(String)
    latest_gold_summary_key = Column(String)
    updated_at = Column(DateTime(timezone=True))


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    run_ts = Column(String, nullable=False)
    dataset_code = Column(String, nullable=False)
    status = Column(String, nullable=False)
    records_count = Column(Integer)
    gold_key = Column(String)
    created_at = Column(DateTime(timezone=True))
