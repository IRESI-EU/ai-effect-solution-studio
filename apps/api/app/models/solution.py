from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class Solution(Base):
    __tablename__ = "solutions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    nodes = Column(JSONB, nullable=False)
    edges = Column(JSONB, nullable=False)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
