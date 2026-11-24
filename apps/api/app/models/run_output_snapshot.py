from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class RunOutputSnapshot(Base):
    """A copy of one task's output, saved as soon as the task completed.

    WP3 services that pass results over gRPC keep only their latest result,
    so later runs would overwrite what a run produced. Saving a decoded copy
    keeps every run's results viewable.
    """

    __tablename__ = "run_output_snapshots"
    __table_args__ = (
        UniqueConstraint("workflow_id", "task_id", "uri", name="uq_run_output_snapshot"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False)
    node_key = Column(String, nullable=True)
    protocol = Column(String, nullable=False)
    uri = Column(Text, nullable=False)
    format = Column(String, nullable=True)
    preview = Column(JSONB, nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
