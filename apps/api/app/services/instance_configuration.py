"""One registry resolution and validation path for Builder, AI drafts and runs."""
from fastapi import HTTPException

from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.services.parameter_values import effective_parameters, parameter_contract_digest


def validate_configuration(db, service_id, operation_name, configuration):
    if configuration is None:
        raise HTTPException(422, "Instance configuration must be an object")
    if not isinstance(configuration, dict) or set(configuration) != {"contract_id", "contract_version", "parameters"}:
        raise HTTPException(422, "Configuration requires contract_id, contract_version and parameters")
    if any(not isinstance(configuration[key], str) or not configuration[key] for key in ("contract_id", "contract_version")):
        raise HTTPException(422, "Contract identifier and version must be non-empty strings")
    contract = db.query(OperationContract).filter(OperationContract.id == configuration["contract_id"]).first()
    if (not contract or contract.service_id != service_id or contract.status != "active"
            or contract.runtime_operation_name != operation_name
            or contract.contract_version != configuration["contract_version"]):
        raise HTTPException(409, "Instance operation/contract version is unavailable or incompatible; review its settings")
    definition = contract.definition.get("execution_parameters")
    if not definition or definition.get("schema_version") != "1.0" or definition.get("transport") != "http-parameters-v1":
        raise HTTPException(422, "This contract does not support editable execution parameters")
    try:
        parameter_contract_digest(definition)
        effective = effective_parameters(definition, configuration["parameters"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"contract_id": contract.id, "contract_version": contract.contract_version,
            "operation_identity": contract.operation_identity, "schema_version": "1.0",
            "parameters": effective}


def validate_builder_configurations(db, nodes, edges, user):
    from app.services.solution_design import validate_solution_service_references, service_id_from_builder_node
    validate_solution_service_references(db, nodes, user)
    if any(not isinstance(node.get("data", {}), dict) for node in nodes):
        raise HTTPException(422, "Node data must be a JSON object")
    ids = [node.get("id") for node in nodes]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise HTTPException(422, "Node instance IDs must be non-empty and unique")
    if any(edge.get("source") not in ids or edge.get("target") not in ids for edge in edges):
        raise HTTPException(422, "An edge references a missing instance")
    if has_configuration(nodes) and any(edge.get("sourceHandle") or edge.get("targetHandle") for edge in edges):
        raise HTTPException(422, "Named port bindings are not supported by the current compiler; use whole-output connections")
    from app.services.capability_bindings import validate_builder
    validate_builder(nodes, edges, db)
    for node in nodes:
        data = node.get("data", {})
        if "configuration" not in data:
            continue  # Preserve legacy designs without injecting new defaults.
        service_id = service_id_from_builder_node(node)
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(422, "Configured instances require a catalogue service")
        validate_configuration(db, service_id, service.operation_name, data["configuration"])


def has_configuration(nodes):
    return any(isinstance(node.get("data"), dict) and ("configuration" in node["data"] or "operation_contract" in node["data"]) for node in nodes)
