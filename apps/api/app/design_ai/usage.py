from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from app.db import Base


class DesignAIUsage(Base):
    """One row per Design with AI request, for the daily limit and cost tracking."""

    __tablename__ = "design_ai_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    attempts = Column(Integer, nullable=False, default=1)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    valid = Column(Boolean, nullable=False, default=False)


def requests_last_24h(db: Session, user_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    return db.query(DesignAIUsage).filter(DesignAIUsage.user_id == user_id, DesignAIUsage.created_at >= since).count()
