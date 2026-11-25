from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dependencies.auth import can_manage_service
from app.models.service import Service
from app.models.user import User


SERVICE_NODE_KIND = "service"
WORKFLOW_INPUT_KIND = "workflow_input"
WORKFLOW_OUTPUT_KIND = "workflow_output"
SERVICE_CONNECTION_KIND = "service_connection"
WORKFLOW_BOUNDARY_KIND = "workflow_boundary"


def service_to_builder_data(service: Service) -> dict:
    """Return the service shape stored by Builder-created React Flow nodes."""
    return {
        "id": service.id,
        "name": service.name,
        "provider": service.provider,
        "category": service.category,
        "version": service.version,
        "description": service.description,
        "status": service.status,
        "trust_badge": service.trust_badge,
        "lifecycle_status": service.lifecycle_status,
        "input_type": service.input_type,
        "output_type": service.output_type,
        "container_name": service.container_name,
        "image": service.image,
        "proto_uri": service.proto_uri,
        "node_type": service.node_type,
        "operation_name": service.operation_name,
        "input_message_name": service.input_message_name,
        "output_message_name": service.output_message_name,
        "internal_host": service.internal_host,
        "internal_port": service.internal_port,
        "repository_url": service.repository_url,
        "repository_branch": service.repository_branch,
        "manifest_path": service.manifest_path,
        "interface_type": service.interface_type,
        "orchestration_mode": service.orchestration_mode,
        "adapter_type": service.adapter_type,
        "health_path": service.health_path,
        "contract_uri": service.contract_uri,
        "owner_node": service.owner_node,
        "created_by_user_id": service.created_by_user_id,
    }


def can_reference_service(user: User, service: Service) -> bool:
    if service.status == "approved":
        return service.lifecycle_status != "archived"
    if user.role == "platform_admin":
        return True
    if service.created_by_user_id == user.id:
        return True
    return can_manage_service(user, service.owner_node)


def resolve_services_for_builder(
    db: Session,
    service_ids: list[str],
    user: User,
) -> dict[str, Service]:
    unique_ids = list(dict.fromkeys(service_ids))
    services = db.query(Service).filter(Service.id.in_(unique_ids)).all() if unique_ids else []
    by_id = {service.id: service for service in services}
    missing = [service_id for service_id in unique_ids if service_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "solution_service_missing",
                "message": "This solution references services that no longer exist.",
                "service_ids": missing,
                "recommended_action": "Restore the missing catalogue records or remove their nodes from the solution before editing.",
            },
        )
    forbidden = [service_id for service_id in unique_ids if not can_reference_service(user, by_id[service_id])]
    if forbidden:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "solution_service_forbidden",
                "message": "You do not have access to one or more services referenced by this solution.",
                "service_ids": forbidden,
            },
        )
    return by_id


def service_id_from_builder_node(node: dict) -> str | None:
    data = node.get("data") if isinstance(node, dict) else None
    service = data.get("service") if isinstance(data, dict) else None
    if isinstance(service, dict) and service.get("id"):
        return str(service["id"])
    if isinstance(node, dict) and node.get("service_id"):
        return str(node["service_id"])
    return None


def is_service_node(node: dict) -> bool:
    if not isinstance(node, dict):
        return False
    data = node.get("data")
    if isinstance(data, dict):
        if data.get("node_kind") == SERVICE_NODE_KIND:
            return True
        if isinstance(data.get("service"), dict) and data["service"].get("id"):
            return True
    return bool(node.get("service_id"))


def count_service_nodes(nodes: list[dict] | None) -> int:
    return sum(1 for node in (nodes or []) if is_service_node(node))


def count_service_connections(nodes: list[dict] | None, edges: list[dict] | None) -> int:
    service_node_ids = {
        str(node.get("id")) for node in (nodes or []) if is_service_node(node) and node.get("id")
    }
    return sum(
        1 for edge in (edges or [])
        if edge.get("source") in service_node_ids and edge.get("target") in service_node_ids
    )


def validate_solution_service_references(db: Session, nodes: list[dict] | None, user: User) -> None:
    service_ids = [service_id_from_builder_node(node) for node in (nodes or []) if is_service_node(node)]
    resolve_services_for_builder(db, [item for item in service_ids if item], user)


def hydrate_solution_service_references(db: Session, nodes: list[dict] | None, user: User) -> list[dict]:
    hydrated = deepcopy(nodes or [])
    service_nodes = [node for node in hydrated if is_service_node(node)]
    service_ids = [service_id_from_builder_node(node) for node in service_nodes]
    by_id = resolve_services_for_builder(db, [item for item in service_ids if item], user)
    for node, service_id in zip(service_nodes, service_ids, strict=True):
        if not service_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "solution_service_reference_invalid",
                    "message": "A service node does not contain a catalogue service ID.",
                    "recommended_action": "Remove and add the service node again in Builder.",
                },
            )
        data = node.setdefault("data", {})
        data["node_kind"] = SERVICE_NODE_KIND
        data["service"] = service_to_builder_data(by_id[service_id])
        data.setdefault("label", by_id[service_id].name)
    return hydrated


def build_linear_builder_design(
    services_by_key: dict[str, Service],
    connections: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Serialize a non-ambiguous package pipeline in Builder's supported shape."""
    keys = set(services_by_key)
    if not keys:
        raise ValueError("A draft solution needs at least one selected service.")

    successors: dict[str, list[str]] = defaultdict(list)
    predecessors: dict[str, list[str]] = defaultdict(list)
    seen_edges: set[tuple[str, str]] = set()
    for connection in connections:
        source = str(connection.get("source_service") or "")
        target = str(connection.get("target_service") or "")
        if source not in keys or target not in keys:
            raise ValueError(f"Package connection '{source}' to '{target}' does not resolve to selected services.")
        if source == target:
            raise ValueError(f"Package service '{source}' cannot connect to itself in a linear draft.")
        pair = (source, target)
        if pair in seen_edges:
            continue
        seen_edges.add(pair)
        successors[source].append(target)
        predecessors[target].append(source)

    ambiguous = sorted(
        key for key in keys if len(successors[key]) > 1 or len(predecessors[key]) > 1
    )
    if ambiguous:
        raise ValueError(
            "The package contains ambiguous branching or merging. Create the services without a draft and route them explicitly in Builder: "
            + ", ".join(ambiguous)
        )
    if len(keys) > 1 and len(seen_edges) != len(keys) - 1:
        raise ValueError("The selected package services do not form one complete linear pipeline.")

    starts = sorted(key for key in keys if not predecessors[key])
    if len(starts) != 1:
        raise ValueError("The selected package services do not have one unambiguous pipeline entry point.")
    ordered: list[str] = []
    queue = deque(starts)
    while queue:
        key = queue.popleft()
        if key in ordered:
            raise ValueError("The selected package pipeline contains a cycle.")
        ordered.append(key)
        queue.extend(successors[key])
    if len(ordered) != len(keys):
        raise ValueError("The selected package services are disconnected or cyclic.")

    canvas_ids = {key: f"service-{services_by_key[key].id}" for key in ordered}
    nodes = [
        {
            "id": "input",
            "position": {"x": 80, "y": 180},
            "data": {"label": "Workflow Input", "node_kind": WORKFLOW_INPUT_KIND},
            "type": "input",
        }
    ]
    for index, key in enumerate(ordered):
        service = services_by_key[key]
        nodes.append(
            {
                "id": canvas_ids[key],
                "position": {"x": 300 + index * 250, "y": 180},
                "data": {
                    "label": service.name,
                    "node_kind": SERVICE_NODE_KIND,
                    "service": service_to_builder_data(service),
                },
                "type": "default",
            }
        )
    nodes.append(
        {
            "id": "output",
            "position": {"x": 300 + len(ordered) * 250, "y": 180},
            "data": {"label": "Workflow Output", "node_kind": WORKFLOW_OUTPUT_KIND},
            "type": "output",
        }
    )

    edges = [
        {
            "id": f"edge-input-{canvas_ids[ordered[0]]}",
            "source": "input",
            "target": canvas_ids[ordered[0]],
            "data": {"connection_kind": WORKFLOW_BOUNDARY_KIND},
        }
    ]
    for source, target in sorted(seen_edges, key=lambda pair: ordered.index(pair[0])):
        edges.append(
            {
                "id": f"edge-{canvas_ids[source]}-{canvas_ids[target]}",
                "source": canvas_ids[source],
                "target": canvas_ids[target],
                "data": {"connection_kind": SERVICE_CONNECTION_KIND},
            }
        )
    edges.append(
        {
            "id": f"edge-{canvas_ids[ordered[-1]]}-output",
            "source": canvas_ids[ordered[-1]],
            "target": "output",
            "data": {"connection_kind": WORKFLOW_BOUNDARY_KIND},
        }
    )
    return nodes, edges
