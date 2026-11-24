import base64
import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.service import Service
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.service_settings import get_definition, resolve_values

MAX_INLINE_JSON_BYTES = 65536


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
    parameters, node_inputs, effective_settings = compile_node_settings(
        workflow, resolved_nodes, warnings
    )
    for onboarding_node in onboarding_nodes:
        if onboarding_node["node_id"] in effective_settings:
            onboarding_node["settings"] = effective_settings[onboarding_node["node_id"]]

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
        result["inputs"] = [inline_json_reference(workflow.run_input, "Run input")]
    if parameters:
        result["parameters"] = parameters
    if node_inputs:
        result["node_inputs"] = node_inputs
    return result


def inline_json_reference(value: dict, label: str) -> dict:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_INLINE_JSON_BYTES:
        raise HTTPException(status_code=422, detail=f"{label} must be at most 64 KiB of JSON.")
    return {
        "protocol": "inline",
        "uri": base64.b64encode(encoded).decode("ascii"),
        "format": "json",
    }


def compile_node_settings(workflow: WorkflowSubmitRequest, resolved_nodes: dict, warnings: list):
    """Validate each node's settings and map them onto orchestrator fields.

    Returns (parameters, node_inputs, effective settings by node_id).
    ``parameters`` settings go to the orchestrator's per-node ``parameters``;
    ``run_input`` settings become the inline input of that start node, with
    any run input typed for this run taking precedence.
    """
    targets = {edge.target for edge in workflow.edges}
    parameters: dict[str, dict] = {}
    node_inputs: dict[str, list] = {}
    effective_by_node: dict[str, dict] = {}
    errors: list[str] = []

    for node in workflow.nodes:
        resolved = resolved_nodes[node.node_id]
        label = resolved.get("service_name") or resolved.get("container_name") or node.node_id
        definition = resolved.get("settings_definition")
        if not definition:
            if node.settings:
                warnings.append({
                    "level": "warning",
                    "node_id": node.node_id,
                    "service_id": resolved.get("service_id"),
                    "message": f"{label} has fixed settings; the saved values were not sent.",
                })
            continue

        effective, node_errors = resolve_values(definition, node.settings)
        errors.extend(f"{label}: {message}" for message in node_errors)
        if node_errors or not effective:
            continue

        node_key = f"{resolved['container_name']}:{resolved['operation_name']}"
        effective_by_node[node.node_id] = {"channel": definition["channel"], "values": effective}
        if definition["channel"] == "parameters":
            parameters[node_key] = effective
        elif node.node_id in targets:
            errors.append(
                f"{label}: its settings are read from the workflow input, so it must be a first step "
                "(no incoming connection)."
            )
        else:
            node_inputs[node_key] = [
                inline_json_reference({**effective, **(workflow.run_input or {})}, f"{label} input")
            ]

    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Some service settings are invalid.", "errors": errors},
        )
    return parameters, node_inputs, effective_by_node


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
            service.container_name if service else None,
            getattr(node, "container_name", None),
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
        "settings_definition": get_definition(service) if service else None,
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
