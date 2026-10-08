from pydantic import BaseModel
from typing import Literal


class ServiceCreate(BaseModel):
    name: str
    provider: str
    category: str
    description: str
    input_type: str
    output_type: str
    version: str = "0.1.0"

    container_name: str = ""
    image: str = ""
    proto_uri: str = ""
    node_type: str = "MLModel"
    operation_name: str = ""
    input_message_name: str = "Request"
    output_message_name: str = "Response"
    internal_host: str = ""
    internal_port: str = "8080"
    lifecycle_status: str = "active"

    repository_url: str | None = None
    repository_branch: str | None = None
    manifest_path: str | None = None
    interface_type: str | None = "control"
    interface_contract: dict | None = None
    orchestration_mode: str | None = "native"
    adapter_type: str | None = None
    health_path: str | None = "/health"
    contract_uri: str | None = None


class ServiceRead(ServiceCreate):
    id: str
    status: str
    trust_badge: str
    description: str | None = None
    lifecycle_status: str = "active"
    repository_url: str | None = None
    repository_branch: str | None = None
    manifest_path: str | None = None

    interface_type: str | None = "control"
    interface_contract: dict | None = None
    orchestration_mode: str | None = "native"
    adapter_type: str | None = None

    health_path: str | None = "/health"
    contract_uri: str | None = None
    owner_node: str | None = None
    created_by_user_id: str | None = None


class ServiceTechnicalMetadataUpdate(BaseModel):
    internal_host: str
    internal_port: str
    health_path: str
    operation_name: str
    input_message_name: str
    output_message_name: str
    contract_uri: str | None = None
    proto_uri: str


class RuntimeVerificationRead(BaseModel):
    status: Literal["verified", "failed", "not_verified"]
    checked_at: str | None = None
    invalidated_at: str | None = None
    runtime_url: str | None = None
    http_status: int | None = None
    failure_reason: str | None = None
    message: str
