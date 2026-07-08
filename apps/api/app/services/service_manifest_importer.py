import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.schemas.service_import import (
    NormalizedImportedService,
    ServiceImportPreviewResponse,
    ValidationMessage,
)


class ServiceManifestImportError(Exception):
    pass


def preview_service_manifest(
    repo_url: str,
    branch: str = "main",
    manifest_path: str = "ai-effect.service.json",
) -> ServiceImportPreviewResponse:
    validation: list[ValidationMessage] = []

    raw_url = build_raw_github_url(repo_url, branch, manifest_path)
    validation.append(
        ValidationMessage(
            level="success",
            message=f"Resolved manifest URL for branch '{branch}' and path '{manifest_path}'.",
        )
    )

    try:
        manifest = fetch_json(raw_url)
        validation.append(ValidationMessage(level="success", message="Manifest found and parsed as JSON."))
    except ServiceManifestImportError as exc:
        return ServiceImportPreviewResponse(
            status="invalid",
            raw_manifest={},
            service=None,
            validation=[
                ValidationMessage(level="error", message=str(exc)),
            ],
        )

    service = normalize_manifest(
        manifest=manifest,
        repo_url=repo_url,
        branch=branch,
        manifest_path=manifest_path,
        validation=validation,
    )

    has_errors = any(item.level == "error" for item in validation)
    has_warnings = any(item.level == "warning" for item in validation)

    if has_errors:
        status = "invalid"
    elif has_warnings:
        status = "warning"
    else:
        status = "valid"

    return ServiceImportPreviewResponse(
        status=status,
        raw_manifest=manifest,
        service=None if has_errors else service,
        validation=validation,
    )


def build_raw_github_url(repo_url: str, branch: str, manifest_path: str) -> str:
    repo_url = repo_url.strip().rstrip("/")
    branch = branch.strip() or "main"
    manifest_path = manifest_path.strip().lstrip("/") or "ai-effect.service.json"

    raw_match = re.match(
        r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)$",
        repo_url,
    )
    if raw_match:
        return repo_url

    github_match = re.match(r"^https://github\.com/([^/]+)/([^/]+)(?:\.git)?$", repo_url)
    if not github_match:
        raise ServiceManifestImportError(
            "Only public GitHub repository URLs are supported in this MVP. "
            "Use a URL like https://github.com/OWNER/REPO."
        )

    owner = github_match.group(1)
    repo = github_match.group(2).removesuffix(".git")
    encoded_path = "/".join(quote(part) for part in manifest_path.split("/"))

    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-EFFECT-Solution-Studio/0.1",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ServiceManifestImportError(
            f"Could not fetch manifest. HTTP {exc.code}. Check repository URL, branch, and manifest path."
        ) from exc
    except URLError as exc:
        raise ServiceManifestImportError(f"Could not fetch manifest: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ServiceManifestImportError("Timed out while fetching manifest.") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ServiceManifestImportError("Manifest was found, but it is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ServiceManifestImportError("Manifest must be a JSON object.")

    return parsed


def normalize_manifest(
    manifest: dict[str, Any],
    repo_url: str,
    branch: str,
    manifest_path: str,
    validation: list[ValidationMessage],
) -> NormalizedImportedService:
    schema_version = manifest.get("schema_version")
    if not schema_version:
        validation.append(ValidationMessage(level="warning", message="schema_version is missing."))

    service = get_object(manifest, "service", validation)
    runtime = get_object(manifest, "runtime", validation)
    interface = get_object(manifest, "interface", validation)
    orchestration = manifest.get("orchestration") if isinstance(manifest.get("orchestration"), dict) else {}

    interface_type = str(interface.get("type") or "control")
    orchestration_mode = str(orchestration.get("mode") or default_orchestration_mode(interface_type))
    adapter_type = orchestration.get("adapter") or orchestration.get("adapter_type")

    service_id = optional_str(service.get("id"))
    name = required_str(service, "name", validation)
    provider = required_str(service, "provider", validation)
    category = required_str(service, "category", validation)
    version = optional_str(service.get("version")) or "0.1.0"
    description = optional_str(service.get("description"))
    trust_badge = optional_str(service.get("trust_badge")) or "pending_review"

    container_name = required_str(runtime, "container_name", validation)
    image = optional_str(runtime.get("image"))
    dockerfile = optional_str(runtime.get("dockerfile"))
    internal_port = optional_str(runtime.get("internal_port")) or "8080"
    health_path = optional_str(runtime.get("health_path")) or "/health"

    if not image and not dockerfile:
        validation.append(
            ValidationMessage(
                level="error",
                message="runtime.image or runtime.dockerfile is required. AI-EFFECT accepts Dockerized services only.",
            )
        )
    elif image:
        validation.append(ValidationMessage(level="success", message="Docker image declared."))
    else:
        validation.append(
            ValidationMessage(
                level="warning",
                message="Dockerfile declared but no image declared. MVP onboarding prefers a pre-built image.",
            )
        )

    input_type = optional_str(interface.get("input_type"))
    output_type = optional_str(interface.get("output_type"))

    operation_name = optional_str(interface.get("operation_name"))
    if not operation_name:
        operation_name = get_operation_name_from_specific_contract(interface, interface_type)
    if not operation_name:
        validation.append(
            ValidationMessage(
                level="error",
                message="interface.operation_name is required. It maps to the orchestrator method field.",
            )
        )
        operation_name = "UnknownOperation"

    proto_uri = None
    contract_uri = optional_str(interface.get("contract_uri"))

    interface_contract = build_interface_contract(interface, interface_type)

    if interface_type == "grpc":
        grpc = interface.get("grpc") if isinstance(interface.get("grpc"), dict) else {}
        proto_uri = optional_str(grpc.get("proto_uri")) or optional_str(interface.get("proto_uri"))
        if not proto_uri:
            validation.append(
                ValidationMessage(level="error", message="gRPC services must declare grpc.proto_uri.")
            )
        else:
            validation.append(ValidationMessage(level="success", message="gRPC proto_uri declared."))

        input_message_name = optional_str(grpc.get("input_message_name")) or optional_str(
            interface.get("input_message_name")
        )
        output_message_name = optional_str(grpc.get("output_message_name")) or optional_str(
            interface.get("output_message_name")
        )

    else:
        input_message_name = optional_str(interface.get("input_message_name"))
        output_message_name = optional_str(interface.get("output_message_name"))

        if not contract_uri:
            contract_uri = manifest_path

        # Short-term compatibility for current orchestrator blueprint schema.
        # The current WP3 parser still requires proto_uri even when execution uses HTTP Control Interface.
        proto_uri = optional_str(interface.get("proto_uri")) or contract_uri

        validation.append(
            ValidationMessage(
                level="warning",
                message=(
                    f"interface.type='{interface_type}' will use AI-EFFECT Control Interface. "
                    "Short-term compiler compatibility will map contract_uri to proto_uri until the orchestrator schema is refined."
                ),
            )
        )

    validate_interface_specific_fields(interface, interface_type, validation)

    if interface_type in {"control", "http", "container_job", "legacy_sidecar"}:
        validation.append(
            ValidationMessage(
                level="success",
                message="Service can be onboarded through the AI-EFFECT Control Interface or adapter pattern.",
            )
        )

    return NormalizedImportedService(
        id=service_id,
        name=name,
        provider=provider,
        category=category,
        version=version,
        description=description,
        trust_badge=trust_badge,
        lifecycle_status="active",
        repository_url=repo_url,
        repository_branch=branch,
        manifest_path=manifest_path,
        interface_type=interface_type,
        orchestration_mode=orchestration_mode,
        adapter_type=optional_str(adapter_type),
        container_name=container_name,
        image=image,
        dockerfile=dockerfile,
        internal_port=internal_port,
        health_path=health_path,
        input_type=input_type,
        output_type=output_type,
        operation_name=operation_name,
        input_message_name=input_message_name,
        output_message_name=output_message_name,
        proto_uri=proto_uri,
        contract_uri=contract_uri,
        interface_contract=interface_contract,
    )


def get_object(parent: dict[str, Any], key: str, validation: list[ValidationMessage]) -> dict[str, Any]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value

    validation.append(ValidationMessage(level="error", message=f"'{key}' object is required."))
    return {}


def required_str(obj: dict[str, Any], key: str, validation: list[ValidationMessage]) -> str:
    value = optional_str(obj.get(key))
    if not value:
        validation.append(ValidationMessage(level="error", message=f"'{key}' is required."))
        return ""
    return value


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def default_orchestration_mode(interface_type: str) -> str:
    if interface_type in {"legacy_sidecar", "http", "container_job"}:
        return "sidecar"
    return "native"


def get_operation_name_from_specific_contract(interface: dict[str, Any], interface_type: str) -> str | None:
    specific = interface.get(interface_type)
    if isinstance(specific, dict):
        return optional_str(specific.get("operation_name"))
    return None


def build_interface_contract(interface: dict[str, Any], interface_type: str) -> dict[str, Any]:
    contract = {
        "type": interface_type,
        "input_type": interface.get("input_type"),
        "output_type": interface.get("output_type"),
    }

    specific = interface.get(interface_type)
    if isinstance(specific, dict):
        contract[interface_type] = specific

    for key in ["operation_name", "contract_uri", "proto_uri"]:
        if key in interface:
            contract[key] = interface[key]

    return contract


def validate_interface_specific_fields(
    interface: dict[str, Any],
    interface_type: str,
    validation: list[ValidationMessage],
) -> None:
    if interface_type == "grpc":
        grpc = interface.get("grpc") if isinstance(interface.get("grpc"), dict) else {}
        for field in ["proto_uri", "operation_name"]:
            if not grpc.get(field) and not interface.get(field):
                validation.append(ValidationMessage(level="error", message=f"gRPC field '{field}' is required."))
        return

    if interface_type == "http":
        http = interface.get("http") if isinstance(interface.get("http"), dict) else {}
        for field in ["method", "path"]:
            if not http.get(field):
                validation.append(ValidationMessage(level="error", message=f"HTTP field '{field}' is required."))
        return

    if interface_type == "container_job":
        job = interface.get("container_job") if isinstance(interface.get("container_job"), dict) else {}
        if not job.get("command"):
            validation.append(
                ValidationMessage(level="error", message="container_job.command is required.")
            )
        return

    if interface_type == "legacy_sidecar":
        sidecar = interface.get("legacy_sidecar") if isinstance(interface.get("legacy_sidecar"), dict) else {}
        if not sidecar.get("adapter_type"):
            validation.append(
                ValidationMessage(level="warning", message="legacy_sidecar.adapter_type is recommended.")
            )
        return

    if interface_type == "control":
        validation.append(
            ValidationMessage(
                level="success",
                message="Native AI-EFFECT Control Interface selected.",
            )
        )
        return

    validation.append(
        ValidationMessage(
            level="error",
            message=(
                "Unsupported interface.type. Use one of: "
                "control, grpc, http, container_job, legacy_sidecar."
            ),
        )
    )