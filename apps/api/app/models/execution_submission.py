"""Additive submission record: historical settings never come from a draft."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class ExecutionSubmission(Base):
    __tablename__ = "execution_submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_user_id = Column(String, nullable=False, index=True)
    solution_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=True, unique=True, index=True)
    submitted = Column(JSONB, nullable=False)
    submitted_sha256 = Column(String, nullable=False)
    phase = Column(String, nullable=False, default="prepared")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class InstanceEvidenceReceipt(Base):
    __tablename__ = "instance_evidence_receipts"
    submission_id = Column(String, primary_key=True)
    task_id = Column(String, primary_key=True)
    manifest_sha256 = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
