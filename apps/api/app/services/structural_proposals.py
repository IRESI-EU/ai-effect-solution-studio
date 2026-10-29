"""Bounded, registry-driven terminal analyzer append. No execution or model calls."""
import json
from copy import deepcopy

from fastapi import HTTPException
from pydantic import Field, ValidationError

from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.design_ai import StrictModel
from app.services.capability_bindings import digest, validate_builder
from app.services.solution_design import can_reference_service, service_to_builder_data


class Append(StrictModel):
    local_ref: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    service_id: str
    contract_id: str
    contract_version: str
    source_slot: str
    target_slot: str


def authority(db, service_id, user, *, lock=True):
    # Held through the caller's Apply transaction, including fingerprint comparison.
    query = db.query(Service).filter(Service.id == service_id).populate_existing()
    service = (query.with_for_update() if lock else query).first()
    if (not service or not can_reference_service(user, service)
            or service.status not in {"approved", "validated"} or service.lifecycle_status == "archived"):
        raise HTTPException(409, "The selected catalogue operation is unavailable or ineligible")
    query = db.query(OperationContract).filter(OperationContract.service_id == service_id,
        OperationContract.runtime_operation_name == service.operation_name,
        OperationContract.status == "active").populate_existing()
    contracts = (query.with_for_update() if lock else query).all()
    if len(contracts) != 1:
        raise HTTPException(409, "The operation has no unique active contract")
    return service, contracts[0]


def append(before, edit, allocation, db, user, *, lock=True):
    from app.services.design_ai import ordered_services
    try:
        request = Append.model_validate_json(edit.value)
    except (ValidationError, ValueError):
        raise HTTPException(422, "Use only an advertised operation, contract and explicit source/target slots") from None
    chain = ordered_services(before["nodes"], before["edges"])
    sources = [n for n in chain if n["id"] == edit.node_id]
    if len(sources) != 1 or sources[0]["id"] != chain[-1]["id"]:
        raise HTTPException(422, "Select the current terminal source instance; branching or cross-draft targets are unsupported")
    source = sources[0]
    if lock:
        identifiers_to_lock = sorted({request.service_id} | {n["data"]["service"]["id"] for n in chain})
        for service_id in identifiers_to_lock:
            authority(db, service_id, user)
    service, contract = authority(db, request.service_id, user, lock=lock)
    definition = contract.definition
    if (contract.id != request.contract_id or contract.contract_version != request.contract_version
            or definition.get("operation_role") != "analyzer"
            or definition.get("binding_transport") != "whole-output-v1"
            or definition.get("execution_parameters")
            or len(definition.get("inputs", [])) != 1 or len(definition.get("outputs", [])) != 1):
        raise HTTPException(422, "Only a pinned whole-output analyzer with one input/output and no editable settings can be appended")
    existing_contracts = [authority(db, n["data"]["service"]["id"], user, lock=lock)[1] for n in chain]
    if any(c.operation_identity == contract.operation_identity for c in existing_contracts):
        raise HTTPException(422, "This analyzer already exists. Review the existing step instead of adding a duplicate")
    if request.local_ref in {n["id"] for n in before["nodes"]}:
        raise HTTPException(422, "The proposal-local reference collides with a current instance")
    identifiers = {n["id"] for n in before["nodes"]} | {e["id"] for e in before["edges"]}
    if any(identifier in identifiers for identifier in (allocation, f"{allocation}-input", f"{allocation}-output")):
        raise HTTPException(409, "New instance identity collision; request a new proposal")
    boundaries = [n for n in before["nodes"] if n.get("type") == "output"]
    terminal = [e for e in before["edges"] if e["source"] == source["id"]]
    if len(boundaries) != 1 or len(terminal) != 1 or terminal[0]["target"] != boundaries[0]["id"]:
        raise HTTPException(422, "A single explicit terminal workflow-output connection is required")
    after = deepcopy(before)
    after["nodes"].append({"id": allocation, "type": "default",
        "position": {"x": source.get("position", {}).get("x", 0), "y": source.get("position", {}).get("y", 0) + 180},
        "data": {"node_kind": "service", "label": service.name, "service": service_to_builder_data(service),
                 "operation_contract": {"contract_id": contract.id, "contract_version": contract.contract_version}}})
    after["edges"] = [e for e in after["edges"] if e["id"] != terminal[0]["id"]]
    after["edges"].extend([
        {"id": f"{allocation}-input", "source": source["id"], "target": allocation,
         "data": {"connection_kind": "service_connection", "binding": {"source_slot": request.source_slot, "target_slot": request.target_slot}}},
        {**deepcopy(terminal[0]), "id": f"{allocation}-output", "source": allocation},
    ])
    ordered_services(after["nodes"], after["edges"])
    validate_builder(after["nodes"], after["edges"], db)
    return after


def review(before, after, db, user):
    old_ids = {n["id"] for n in before["nodes"]}
    added = next(n for n in after["nodes"] if n["id"] not in old_ids)
    old_edges, new_edges = {e["id"]: e for e in before["edges"]}, {e["id"]: e for e in after["edges"]}
    snapshots = {}
    for node in after["nodes"]:
        if node.get("data", {}).get("service"):
            service, contract = authority(db, node["data"]["service"]["id"], user)
            snapshots[node["id"]] = {"catalogue_sha256": digest(service_to_builder_data(service)),
                "contract_id": contract.id, "contract_version": contract.contract_version,
                "definition_sha256": digest(contract.definition), "operation_identity": contract.operation_identity}
    return {"added_operation": {"node_id": added["id"], "label": added["data"]["label"],
                "operation": added["data"]["service"]["operation_name"]},
        "connections_added": [e for key, e in new_edges.items() if key not in old_edges],
        "connections_removed": [e for key, e in old_edges.items() if key not in new_edges],
        "unchanged": [{"node_id": n["id"], "label": n.get("data", {}).get("label", n["id"]),
                       "configuration": deepcopy(n.get("data", {}).get("configuration")),
                       "operation_contract": deepcopy(n.get("data", {}).get("operation_contract"))} for n in before["nodes"]],
        "authority": snapshots,
        "compatibility": "Explicit named slots verified with whole-output-v1: one complete reference; no projection, conversion or merge.",
        "limitations": "Design preparation only. No workflow executes. Runtime availability and production compatibility remain unchecked."}


def context(row, db, user):
    design = row.state["design"]
    nodes = [{"node_id": n["id"], "label": n.get("data", {}).get("label", n["id"]),
              "operation_name": n.get("data", {}).get("service", {}).get("operation_name"),
              **{k: deepcopy(n.get("data", {})[k]) for k in ("configuration", "operation_contract") if k in n.get("data", {})}}
             for n in design["nodes"]]
    candidates = []
    # Reuse the exact candidate validator; shared display labels never establish eligibility.
    from app.schemas.design_ai import Edit
    for service in db.query(Service).order_by(Service.id).all():
        if not can_reference_service(user, service) or service.status not in {"approved", "validated"} or service.lifecycle_status == "archived":
            continue
        matches = db.query(OperationContract).filter(OperationContract.service_id == service.id,
            OperationContract.runtime_operation_name == service.operation_name, OperationContract.status == "active").all()
        if len(matches) != 1:
            continue
        contract = matches[0]
        for node in design["nodes"]:
            source_pin = node.get("data", {}).get("operation_contract", {})
            source_contract = db.get(OperationContract, source_pin.get("contract_id", ""))
            if not source_contract:
                continue
            for output in source_contract.definition.get("outputs", []):
                for target in contract.definition.get("inputs", []):
                    value = {"local_ref": "new_analyzer", "service_id": service.id, "contract_id": contract.id,
                        "contract_version": contract.contract_version, "source_slot": output["name"], "target_slot": target["name"]}
                    try:
                        append(design, Edit(kind="append_bound_operation", node_id=node["id"], value=json.dumps(value)), "context-preview", db, user, lock=False)
                    except HTTPException:
                        continue
                    candidates.append({"source_node_id": node["id"], "label": service.name, "operation_name": service.operation_name,
                        **value, "source_slot_definition": deepcopy(output), "target_slot_definition": deepcopy(target)})
    return {"instances": nodes, "connections": [{k: deepcopy(e[k]) for k in ("source", "target", "data") if k in e} for e in design["edges"]],
        "compatible_candidates": candidates, "supported_edits": ["append_bound_operation"],
        "targeting": "Use an explicit source_node_id and one advertised candidate; ambiguous source requires clarification with no edits. Existing analyzers must not be duplicated.",
        "runtime_checked": False, "execution": "Design preparation only; no workflow submission"}
