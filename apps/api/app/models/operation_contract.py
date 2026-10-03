from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationContract(Base):
    __tablename__ = "operation_contracts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'deprecated', 'withdrawn')",
            name="ck_operation_contracts_status",
        ),
        CheckConstraint(
            "source_kind IN ('manual', 'manifest', 'wp3_package', 'demo')",
            name="ck_operation_contracts_source_kind",
        ),
        CheckConstraint(
            "schema_version = '1.0'",
            name="ck_operation_contracts_schema_version",
        ),
        UniqueConstraint(
            "service_id",
            "operation_identity",
            "contract_version",
            name="uq_operation_contracts_service_identity_version",
        ),
        Index("ix_operation_contracts_service_id", "service_id"),
        Index("ix_operation_contracts_service_status", "service_id", "status"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    service_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("services.id"),
        nullable=False,
    )
    operation_identity: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_operation_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
