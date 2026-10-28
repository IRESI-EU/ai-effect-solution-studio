"""Resolve explicit I/O bindings in the existing operation registry.

whole-output-v1 names the one reference WP3 already forwards unchanged.
Multiple slots, joins, projections and conversions need another supported
transport; matching labels alone never establish compatibility.
"""
import hashlib
import json

from fastapi import HTTPException
from pydantic import ValidationError

from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.operation_contract import OperationContractDefinition
from app.schemas.workflow_submit import WorkflowSubmitRequest


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def explicit(workflow):
    return any("operation_contract" in n.model_fields_set for n in workflow.nodes) or any(
        "binding" in e.model_fields_set for e in workflow.edges)


def validate(workflow, db):
    pins, definitions, snapshots = {}, {}, {}
    for node in workflow.nodes:
        active = None
        if db is not None and node.service_id:
            service = db.get(Service, node.service_id)
            if service:
                active = db.query(OperationContract).filter(
                    OperationContract.service_id == service.id,
                    OperationContract.runtime_operation_name == service.operation_name,
                    OperationContract.status == "active").first()
        strict = active is not None and active.definition.get("binding_transport") is not None
        if not strict and "operation_contract" not in node.model_fields_set:
            continue
        pin = node.operation_contract
        if (not active or pin is None or active.id != pin.contract_id
                or active.contract_version != pin.contract_version):
            raise HTTPException(409, f"{node.node_id}: pin the current operation contract before validating connections.")
        try:
            definition = OperationContractDefinition.model_validate(active.definition).model_dump(exclude_none=True)
        except ValidationError:
            raise HTTPException(409, f"{node.node_id}: operation contract is invalid; ask its owner to review it.") from None
        if definition.get("binding_transport") != "whole-output-v1":
            raise HTTPException(422, f"{node.node_id}: named bindings have no supported runtime transport.")
        if len(definition["outputs"]) > 1 or len(definition["inputs"]) > 1:
            raise HTTPException(422, f"{node.node_id}: whole-output-v1 supports at most one input and output slot.")
        if definition.get("execution_parameters") and node.configuration is None:
            raise HTTPException(422, f"{node.node_id}: choose and save instance settings before qualification.")
        if node.configuration is not None and any(node.configuration.get(k) != getattr(pin, k)
                                                   for k in ("contract_id", "contract_version")):
            raise HTTPException(409, f"{node.node_id}: settings and connections must use the same contract version.")
        pins[node.node_id], definitions[node.node_id] = active, definition
        snapshots[node.node_id] = {"contract_id": active.id, "contract_version": active.contract_version,
            "operation_identity": active.operation_identity, "runtime_operation_name": active.runtime_operation_name,
            "source_kind": active.source_kind, "source_reference": active.source_reference,
            "definition": definition, "definition_sha256": digest(definition)}
    incoming, bindings, seen = {}, [], set()
    for edge in workflow.edges:
        pair = (edge.source, edge.target)
        if edge.source not in pins and edge.target not in pins and edge.binding is None:
            continue  # Existing supported unqualified designs remain explicit legacy paths.
        if pair in seen or edge.source == edge.target:
            raise HTTPException(422, "Qualified connections must be unique and cannot connect an instance to itself.")
        seen.add(pair)
        if edge.source not in pins or edge.target not in pins or edge.binding is None:
            raise HTTPException(422, f"{edge.source} → {edge.target}: select explicit slots and pin both operation contracts.")
        outputs, inputs = definitions[edge.source]["outputs"], definitions[edge.target]["inputs"]
        output = next((s for s in outputs if s["name"] == edge.binding.source_slot), None)
        target = next((s for s in inputs if s["name"] == edge.binding.target_slot), None)
        if not output or not target:
            raise HTTPException(422, "The selected output or input slot is unknown; review this connection.")
        if target["source_requirement"] not in ("upstream_operation", "upstream_or_workflow_input"):
            raise HTTPException(422, f"{edge.target}: this slot does not accept an upstream operation.")
        fields = ("semantic_concept", "schema_ref", "value_representation")
        if (any(not output.get(k) or output.get(k) != target.get(k) for k in fields)
                or output["value_representation"] != "data_reference"
                or not output["data_reference_protocols"] or not output["content_types"]
                or not set(output["data_reference_protocols"]) <= set(target["data_reference_protocols"])
                or not set(output["content_types"]) <= set(target["content_types"])
                or output["min_cardinality"] != 1 or output["max_cardinality"] != 1
                or target["max_cardinality"] != 1):
            raise HTTPException(422, "Incompatible connection: schema/version, meaning, representation, format, protocol or cardinality differs. No conversion is available.")
        incoming.setdefault(edge.target, []).append(edge)
        if len(incoming[edge.target]) > 1:
            raise HTTPException(422, f"{edge.target}: whole-output-v1 cannot merge multiple references.")
        bindings.append({"source": edge.source, "target": edge.target, **edge.binding.model_dump(),
                         "transport": "whole-output-v1", "schema_ref": output["schema_ref"],
                         "source_contract_id": pins[edge.source].id, "target_contract_id": pins[edge.target].id})
    # Reject cycles, including mixed legacy/qualified cycles, before runtime.
    adjacency = {n.node_id: [] for n in workflow.nodes}
    for edge in workflow.edges:
        if edge.source not in adjacency or edge.target not in adjacency:
            raise HTTPException(422, "A connection references a missing instance.")
        adjacency[edge.source].append(edge.target)
    visited, visiting = set(), set()
    def visit(key):
        if key in visiting:
            raise HTTPException(422, "Workflow connections contain a cycle.")
        if key not in visited:
            visiting.add(key)
            for child in adjacency[key]:
                visit(child)
            visiting.remove(key)
            visited.add(key)
    if pins:
        for key in adjacency:
            visit(key)
    for key, definition in definitions.items():
        slots = definition["inputs"]
        if any(s["required"] for s in slots) and not incoming.get(key):
            raise HTTPException(422, f"{key}: connect its required input before saving or executing.")
        if workflow.run_input is not None and not incoming.get(key):
            raise HTTPException(422, f"{key}: workflow input is not supported by this qualified contract; use instance settings.")
    return {"status": "verified" if pins else "unqualified", "contracts": snapshots, "bindings": bindings,
            "message": "Explicit schema and slot compatibility verified." if pins else
                       "Legacy connections: semantic compatibility has not been established."}


def validate_builder(nodes, edges, db):
    if any(not isinstance(e.get("data", {}), dict) for e in edges):
        raise HTTPException(422, "Connection data must be a JSON object.")
    service_nodes = [n for n in nodes if n.get("data", {}).get("service")]
    ids = {n["id"] for n in service_nodes}
    values = [{"node_id": n["id"], "service_id": n["data"]["service"].get("id"),
               "container_name": "registry", "operation_name": "registry",
               **{k: n["data"][k] for k in ("configuration", "operation_contract") if k in n["data"]}}
              for n in service_nodes]
    links = [{"source": e["source"], "target": e["target"],
              **({"binding": e["data"]["binding"]} if "binding" in (e.get("data") or {}) else {})}
             for e in edges if e.get("source") in ids and e.get("target") in ids]
    try:
        workflow = WorkflowSubmitRequest(name="Saved design validation", nodes=values, edges=links)
    except ValidationError:
        raise HTTPException(422, "Invalid operation contract pin or slot binding.") from None
    if explicit(workflow) and any(e.get("sourceHandle") or e.get("targetHandle") for e in edges):
        raise HTTPException(422, "Use the verified connection slots; canvas handle projection is not supported.")
    return validate(workflow, db)
