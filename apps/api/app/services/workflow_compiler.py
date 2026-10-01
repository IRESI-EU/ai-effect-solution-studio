import base64
import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.service import Service
from app.schemas.workflow_submit import WorkflowSubmitRequest


def compile_to_wp3_payload(workflow: WorkflowSubmitRequest, db: Session | None = None):
    connected_by_source = {}

    for edge in workflow.edges:
        connected_by_source.setdefault(edge.source, []).append(edge.target)

    resolved_nodes = {}

    for node in workflow.nodes:
        resolved_nodes[node.node_id] = resolve_node_runtime_metadata(node, db)

    blueprint_nodes = []

    for node in workflow.nodes:
        resolved_node = resolved_nodes[node.node_id]
        connected_to = []

        for target_id in connected_by_source.get(node.node_id, []):
            target = resolved_nodes.get(target_id)

            if not target:
                continue

            connected_to.append(
                {
                    "container_name": target["container_name"],
                    "operation_signature": {
                        "operation_name": target["operation_name"],
                    },
                }
            )

        blueprint_nodes.append(
            {
                "container_name": resolved_node["container_name"],
                "proto_uri": resolved_node["proto_uri"],
                "image": resolved_node["image"],
                "node_type": resolved_node["node_type"],
                "operation_signature_list": [
                    {
                        "operation_signature": {
                            "operation_name": resolved_node["operation_name"],
                            "input_message_name": resolved_node["input_message_name"],
                            "output_message_name": resolved_node["output_message_name"],
                        },
                        "connected_to": connected_to,
                    }
                ],
            }
        )

    docker_info_list = [
        {
            "container_name": resolved_node["container_name"],
            "ip_address": resolved_node["internal_host"] or resolved_node["container_name"],
            "port": resolved_node["internal_port"],
        }
        for resolved_node in resolved_nodes.values()
    ]

    onboarding_nodes = [
        {
            "node_id": resolved_node["node_id"],
            "service_id": resolved_node["service_id"],
            "service_name": resolved_node["service_name"],
            "container_name": resolved_node["container_name"],
            "interface_type": resolved_node["interface_type"],
            "orchestration_mode": resolved_node["orchestration_mode"],
            "adapter_type": resolved_node["adapter_type"],
            "contract_uri": resolved_node["contract_uri"],
            "proto_uri": resolved_node["proto_uri"],
            "health_path": resolved_node["health_path"],
            "repository_url": resolved_node["repository_url"],
            "repository_branch": resolved_node["repository_branch"],
            "manifest_path": resolved_node["manifest_path"],
            "compatibility_mode": resolved_node["compatibility_mode"],
        }
        for resolved_node in resolved_nodes.values()
    ]

    warnings = build_compile_warnings(resolved_nodes)

    result = {
        "blueprint": {
            "name": workflow.name,
            "pipeline_id": "solution-studio-generated",
            "creation_date": "2026-01-01",
            "type": "pipeline-topology/v2",
            "version": "2.0",
            "nodes": blueprint_nodes,
        },
        "dockerinfo": {
            "docker_info_list": docker_info_list,
        },
        "solution_studio_metadata": {
            "compatibility_target": "wp3-orchestrator-blueprint-v2",
            "notes": [
                "The blueprint and dockerinfo sections remain compatible with the current WP3 orchestrator schema.",
                "The solution_studio_metadata section is used by Solution Studio for onboarding traceability and future orchestrator schema refinement.",
            ],
            "nodes": onboarding_nodes,
            "warnings": warnings,
        },
    }
    if workflow.run_input is not None:
        encoded = json.dumps(workflow.run_input, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > 65536:
            raise HTTPException(status_code=422, detail="Run input must be at most 64 KiB of JSON.")
        result["inputs"] = [{
            "protocol": "inline",
            "uri": base64.b64encode(encoded).decode("ascii"),
            "format": "json",
        }]
    return result


def resolve_node_runtime_metadata(node, db: Session | None):
    service = None

    service_id = getattr(node, "service_id", None)

    if db is not None and service_id:
        service = db.query(Service).filter(Service.id == service_id).first()

    interface_type = first_non_empty(
        service.interface_type if service else None,
        getattr(node, "interface_type", None),
        "control",
    )

    orchestration_mode = first_non_empty(
        service.orchestration_mode if service else None,
        getattr(node, "orchestration_mode", None),
        "native",
    )

    contract_uri = first_non_empty(
        service.contract_uri if service else None,
        getattr(node, "contract_uri", None),
    )

    proto_uri = first_non_empty(
        service.proto_uri if service else None,
        getattr(node, "proto_uri", None),
        contract_uri,
    )

    compatibility_mode = determine_compatibility_mode(
        interface_type=interface_type,
        orchestration_mode=orchestration_mode,
        contract_uri=contract_uri,
        proto_uri=proto_uri,
    )

    return {
        "node_id": getattr(node, "node_id", None),
        "service_id": service.id if service else service_id,
        "service_name": service.name if service else getattr(node, "name", None),
        "container_name": first_non_empty(
            getattr(node, "container_name", None),
            service.container_name if service else None,
            getattr(node, "operation_name", None),
            getattr(node, "node_id", None),
        ),
        "proto_uri": proto_uri,
        "contract_uri": contract_uri,
        "image": first_non_empty(
            service.image if service else None,
            getattr(node, "image", None),
        ),
        "node_type": first_non_empty(
            service.node_type if service else None,
            getattr(node, "node_type", None),
            "service",
        ),
        "operation_name": first_non_empty(
            service.operation_name if service else None,
            getattr(node, "operation_name", None),
        ),
        "input_message_name": first_non_empty(
            service.input_message_name if service else None,
            getattr(node, "input_message_name", None),
            "Request",
        ),
        "output_message_name": first_non_empty(
            service.output_message_name if service else None,
            getattr(node, "output_message_name", None),
            "Response",
        ),
        "internal_host": first_non_empty(
            service.internal_host if service else None,
            getattr(node, "internal_host", None),
        ),
        "internal_port": first_non_empty(
            service.internal_port if service else None,
            getattr(node, "internal_port", None),
            "8080",
        ),
        "interface_type": interface_type,
        "orchestration_mode": orchestration_mode,
        "adapter_type": first_non_empty(
            service.adapter_type if service else None,
            getattr(node, "adapter_type", None),
        ),
        "health_path": first_non_empty(
            service.health_path if service else None,
            getattr(node, "health_path", None),
            "/health",
        ),
        "repository_url": service.repository_url if service else None,
        "repository_branch": service.repository_branch if service else None,
        "manifest_path": service.manifest_path if service else None,
        "compatibility_mode": compatibility_mode,
    }


def determine_compatibility_mode(
    interface_type: str | None,
    orchestration_mode: str | None,
    contract_uri: str | None,
    proto_uri: str | None,
):
    normalized_interface = interface_type or "control"
    normalized_orchestration = orchestration_mode or "native"

    if normalized_interface == "grpc":
        return "native_grpc"

    if normalized_interface == "control" and normalized_orchestration == "native":
        return "native_control_interface"

    if normalized_orchestration == "sidecar":
        return "control_interface_sidecar_adapter"

    if normalized_interface in {"http", "container_job", "legacy_sidecar"}:
        if proto_uri and contract_uri and proto_uri == contract_uri:
            return "contract_uri_mapped_to_proto_uri"

        return "non_grpc_control_interface_compatibility"

    return "wp3_blueprint_compatibility"


def build_compile_warnings(resolved_nodes: dict):
    warnings = []

    for resolved_node in resolved_nodes.values():
        service_name = first_non_empty(
            resolved_node.get("service_name"),
            resolved_node.get("service_id"),
            resolved_node.get("container_name"),
            resolved_node.get("node_id"),
            "Unknown service",
        )

        interface_type = resolved_node.get("interface_type") or "control"
        orchestration_mode = resolved_node.get("orchestration_mode") or "native"
        compatibility_mode = resolved_node.get("compatibility_mode")

        if interface_type != "grpc":
            warnings.append(
                {
                    "level": "info",
                    "node_id": resolved_node.get("node_id"),
                    "service_id": resolved_node.get("service_id"),
                    "message": (
                        f"{service_name} uses interface_type='{interface_type}'. "
                        "The current WP3 blueprint still receives a proto_uri-compatible field."
                    ),
                }
            )

        if orchestration_mode == "sidecar":
            warnings.append(
                {
                    "level": "warning",
                    "node_id": resolved_node.get("node_id"),
                    "service_id": resolved_node.get("service_id"),
                    "message": (
                        f"{service_name} uses sidecar orchestration. "
                        "Solution Studio will route this through the AI-EFFECT Control Interface "
                        "compatibility pattern."
                    ),
                }
            )

        if compatibility_mode == "contract_uri_mapped_to_proto_uri":
            warnings.append(
                {
                    "level": "warning",
                    "node_id": resolved_node.get("node_id"),
                    "service_id": resolved_node.get("service_id"),
                    "message": (
                        f"{service_name} maps contract_uri to proto_uri for short-term WP3 "
                        "orchestrator compatibility."
                    ),
                }
            )

        if not resolved_node.get("proto_uri"):
            warnings.append(
                {
                    "level": "error",
                    "node_id": resolved_node.get("node_id"),
                    "service_id": resolved_node.get("service_id"),
                    "message": (
                        f"{service_name} does not have a proto_uri or contract_uri compatibility "
                        "value. The current WP3 blueprint parser may reject this node."
                    ),
                }
            )

    return warnings


def first_non_empty(*values):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None
