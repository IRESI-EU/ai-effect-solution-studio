from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.solution import Solution
from app.models.user import AuditEvent, User
from app.services.audit import record_audit_event
from app.services.solution_design import build_linear_builder_design, count_service_nodes, is_service_node


class PackageSolutionRepairError(ValueError):
    pass


def repair_legacy_package_solution(db: Session, solution_id: str, *, apply: bool = False) -> dict:
    solution = db.get(Solution, solution_id)
    if not solution:
        raise PackageSolutionRepairError("Solution not found.")
    import_event = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.target_type == "solution",
            AuditEvent.target_id == solution.id,
            AuditEvent.action == "solution.package_imported",
        )
        .order_by(AuditEvent.created_at.asc())
        .first()
    )
    if not import_event:
        raise PackageSolutionRepairError("The solution was not created by the package importer.")
    edits = db.query(AuditEvent).filter(
        AuditEvent.target_type == "solution",
        AuditEvent.target_id == solution.id,
        AuditEvent.action == "solution.updated",
    ).count()
    if edits:
        raise PackageSolutionRepairError("The package draft has user edits and cannot be repaired automatically.")
    stored_service_nodes = [node for node in (solution.nodes or []) if is_service_node(node)]
    if stored_service_nodes and all(
        isinstance(node.get("data"), dict) and node["data"].get("service")
        for node in stored_service_nodes
    ):
        return {"status": "already_supported", "solution_id": solution.id}

    legacy_nodes = solution.nodes or []
    if not legacy_nodes or any(not node.get("service_id") or not node.get("id") for node in legacy_nodes):
        raise PackageSolutionRepairError("The stored design is not an untouched legacy package graph.")
    service_ids = [str(node["service_id"]) for node in legacy_nodes]
    services = db.query(Service).filter(Service.id.in_(service_ids)).all()
    by_id = {service.id: service for service in services}
    missing = [service_id for service_id in service_ids if service_id not in by_id]
    if missing:
        raise PackageSolutionRepairError("Missing referenced services: " + ", ".join(missing))
    wrong_owner = [
        service.id for service in services
        if service.created_by_user_id != solution.created_by_user_id
    ]
    if wrong_owner:
        raise PackageSolutionRepairError("Referenced services do not belong to the draft owner: " + ", ".join(wrong_owner))

    service_by_legacy_key = {str(node["id"]): by_id[str(node["service_id"])] for node in legacy_nodes}
    connections = []
    for edge in solution.edges or []:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in service_by_legacy_key or target not in service_by_legacy_key:
            raise PackageSolutionRepairError(f"Unresolved legacy edge '{source}' to '{target}'.")
        connections.append({"source_service": source, "target_service": target})
    nodes, edges = build_linear_builder_design(service_by_legacy_key, connections)
    result = {
        "status": "repair_ready",
        "solution_id": solution.id,
        "name": solution.name,
        "services": count_service_nodes(nodes),
        "internal_connections": sum(
            1 for edge in edges if (edge.get("data") or {}).get("connection_kind") == "service_connection"
        ),
        "boundary_connections": sum(
            1 for edge in edges if (edge.get("data") or {}).get("connection_kind") == "workflow_boundary"
        ),
    }
    if not apply:
        return result

    actor = db.get(User, import_event.actor_user_id) if import_event.actor_user_id else None
    original = {"nodes": solution.nodes, "edges": solution.edges}
    record_audit_event(
        db, actor, "solution.package_repair_snapshot", "solution", solution.id,
        {"reason": "legacy package graph was incompatible with Builder", "original_design": original},
    )
    solution.nodes = nodes
    solution.edges = edges
    solution.updated_at = datetime.utcnow()
    record_audit_event(
        db, actor, "solution.package_repaired", "solution", solution.id,
        {key: value for key, value in result.items() if key not in {"status", "name"}},
    )
    db.commit()
    result["status"] = "repaired"
    return result
