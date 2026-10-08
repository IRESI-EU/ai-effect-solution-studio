from typing import Any, Literal

from pydantic import BaseModel, Field


InterfaceType = Literal["control", "grpc", "http", "container_job", "legacy_sidecar"]
OrchestrationMode = Literal["native", "sidecar", "external", "manual_review"]


class RuntimeOnboardingEvidence(BaseModel):
    source_type: Literal["public_git", "manual_manifest"]
    source_revision: str | None = None
    runtime_status: Literal["needs_deployment", "already_running"]
    revision_pinned: bool = False
    image_reviewed: bool = False
    secrets_external: bool = False
    health_verified: bool = False
    registration_only_acknowledged: bool = False


class ServiceImportPreviewRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    manifest_path: str = "ai-effect.service.json"

class ServiceImportManualPreviewRequest(BaseModel):
    repo_url: str = "manual-upload"
    branch: str = "main"
    manifest_path: str = "ai-effect.service.json"
    manifest: dict[str, Any]

class ServiceImportManualConfirmRequest(BaseModel):
    repo_url: str = "manual-upload"
    branch: str = "main"
    manifest_path: str = "ai-effect.service.json"
    manifest: dict[str, Any]
    onboarding: RuntimeOnboardingEvidence | None = None

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
    internal_host: str
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


class PackageOperation(BaseModel):
    operation_name: str
    input_message_name: str
    output_message_name: str
    compatible_with_proto: bool
    compatibility_message: str


class PackageServicePreview(BaseModel):
    key: str
    proposed_id: str
    name: str
    description: str
    category: str
    version: str
    container_name: str
    image: str
    internal_host: str | None = None
    internal_port: str | None = None
    node_type: str
    proto_path: str
    operations: list[PackageOperation]
    selected_operation: str | None = None
    duplicate_conflicts: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class PackageConnection(BaseModel):
    source_service: str
    source_operation: str
    target_service: str
    target_operation: str


class PackageImportPreviewResponse(BaseModel):
    upload_token: str
    package_name: str
    archive_name: str
    services: list[PackageServicePreview]
    connections: list[PackageConnection]
    warnings: list[str] = Field(default_factory=list)
    registration_status: Literal["preview", "blocked"] = "preview"
    runtime_status: Literal["unverified"] = "unverified"
    operation_compatibility: Literal["verified", "needs_selection", "blocked"]


class PackageServiceSelection(BaseModel):
    key: str
    selected: bool = True
    service_id: str
    name: str
    description: str
    category: str
    operation_name: str
    internal_host: str | None = None
    internal_port: str | None = None
    health_path: str = "/health"
    register_incomplete_draft: bool = False


class PackageImportConfirmRequest(BaseModel):
    upload_token: str
    services: list[PackageServiceSelection]
    create_solution: bool = False
    solution_name: str | None = None
    registration_only_acknowledged: bool = False


class PackageImportConfirmResponse(BaseModel):
    services: list[dict[str, Any]]
    solution: dict[str, Any] | None = None
    message: str
