from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.db import Base


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    version: Mapped[str] = mapped_column(String(50), default="0.1.0")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status = Column(String, default="active")

    input_type: Mapped[str] = mapped_column(String(100), nullable=False)
    output_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trust_badge: Mapped[str] = mapped_column(String(100), default="Experimental")

    container_name: Mapped[str] = mapped_column(String(150), default="")
    image: Mapped[str] = mapped_column(String(250), default="")
    proto_uri: Mapped[str] = mapped_column(String(250), default="")
    node_type: Mapped[str] = mapped_column(String(100), default="MLModel")
    operation_name: Mapped[str] = mapped_column(String(150), default="")
    input_message_name: Mapped[str] = mapped_column(String(150), default="Request")
    output_message_name: Mapped[str] = mapped_column(String(150), default="Response")
    internal_host: Mapped[str] = mapped_column(String(150), default="")
    internal_port: Mapped[str] = mapped_column(String(20), default="8080")

    repository_url = Column(Text, nullable=True)
    repository_branch = Column(String, nullable=True)
    manifest_path = Column(Text, nullable=True)

    interface_type = Column(String, default="control")
    interface_contract = Column(JSONB, nullable=True)
    orchestration_mode = Column(String, default="native")
    adapter_type = Column(String, nullable=True)

    health_path = Column(String, default="/health")
    contract_uri = Column(Text, nullable=True)
    owner_node = Column(String(40), nullable=True, index=True)
    created_by_user_id = Column(String, nullable=True, index=True)
