from typing import Any, Literal

from pydantic import BaseModel, Field


InterfaceType = Literal["control", "grpc", "http", "container_job", "legacy_sidecar"]
OrchestrationMode = Literal["native", "sidecar", "external", "manual_review"]


class ServiceImportPreviewRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    manifest_path: str = "ai-effect.service.json"


class ValidationMessage(BaseModel):
    level: Literal["success", "warning", "error"]
    message: str


class NormalizedImportedService(BaseModel):
    id: str | None = None
    name: str
    provider: str
    category: str
    version: str = "0.1.0"
    description: str | None = None
    trust_badge: str = "pending_review"
    lifecycle_status: str = "active"

    repository_url: str
    repository_branch: str = "main"
    manifest_path: str = "ai-effect.service.json"

    interface_type: str = "control"
    orchestration_mode: str = "native"
    adapter_type: str | None = None

    container_name: str
    image: str | None = None
    dockerfile: str | None = None
    internal_port: str = "8080"
    health_path: str = "/health"

    input_type: str | None = None
    output_type: str | None = None

    operation_name: str
    input_message_name: str | None = None
    output_message_name: str | None = None

    proto_uri: str | None = None
    contract_uri: str | None = None
    interface_contract: dict[str, Any] = Field(default_factory=dict)


class ServiceImportPreviewResponse(BaseModel):
    status: Literal["valid", "warning", "invalid"]
    raw_manifest: dict[str, Any]
    service: NormalizedImportedService | None = None
    validation: list[ValidationMessage]