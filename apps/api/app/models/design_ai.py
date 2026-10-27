from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class DesignDraft(Base):
    __tablename__ = "design_ai_drafts"

    id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    revision = Column(Integer, nullable=False, default=0)
    state = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
