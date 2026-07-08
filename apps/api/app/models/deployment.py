from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, nullable=False, unique=True, index=True)
    solution_id = Column(String, ForeignKey("solutions.id"), nullable=True)
    name = Column(String, nullable=False)
    status = Column(String, default="submitted")
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    solution = relationship("Solution")