from sqlalchemy.orm import Session

from app.models.service import Service
from app.schemas.workflow_submit import WorkflowSubmitRequest


def compile_to_wp3_payload(workflow: WorkflowSubmitRequest, db: Session | None = None):
    connected_by_source = {}

    for edge in workflow.edges:
        connected_by_source.setdefault(edge.source, []).append(edge.target)

    nodes_by_id = {node.node_id: node for node in workflow.nodes}

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
                            "input_message_name": resolved_node[
                                "input_message_name"
                            ],
                            "output_message_name": resolved_node[
                                "output_message_name"
                            ],
                        },
                        "connected_to": connected_to,
                    }
                ],
            }
        )

    docker_info_list = [
        {
            "container_name": resolved_node["container_name"],
            "ip_address": resolved_node["internal_host"]
            or resolved_node["container_name"],
            "port": resolved_node["internal_port"],
        }
        for resolved_node in resolved_nodes.values()
    ]

    return {
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
    }


def resolve_node_runtime_metadata(node, db: Session | None):
    service = None

    service_id = getattr(node, "service_id", None)

    if db is not None and service_id:
        service = db.query(Service).filter(Service.id == service_id).first()

    return {
        "service_id": service.id if service else service_id,
        "container_name": first_non_empty(
            getattr(node, "container_name", None),
            service.container_name if service else None,
            getattr(node, "operation_name", None),
            getattr(node, "node_id", None),
        ),
        "proto_uri": first_non_empty(
            service.proto_uri if service else None,
            getattr(node, "proto_uri", None),
        ),
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
        ),
        "output_message_name": first_non_empty(
            service.output_message_name if service else None,
            getattr(node, "output_message_name", None),
        ),
        "internal_host": first_non_empty(
            service.internal_host if service else None,
            getattr(node, "internal_host", None),
        ),
        "internal_port": first_non_empty(
            service.internal_port if service else None,
            getattr(node, "internal_port", None),
        ),
    }


def first_non_empty(*values):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None     