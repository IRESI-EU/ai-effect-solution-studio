"""Opt-in local submission snapshot. Existing deployment/solution schemas unchanged."""
from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from app.db import Base


class LocalDutchExecution(Base):
    __tablename__ = "local_dutch_executions"
    id = Column(String, primary_key=True)
    workflow_id = Column(String, unique=True, index=True, nullable=True)
    solution_id = Column(String, nullable=False)
    owner_user_id = Column(String, nullable=False, index=True)
    submitted = Column(JSONB, nullable=False)
    collection = Column(JSONB, nullable=True)
    phase = Column(String, nullable=False, default="prepared")
    created_at = Column(DateTime, default=datetime.utcnow)
