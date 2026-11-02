"""Exactly two catalogue operations, one whole-output binding, design only.

The model selects a server-advertised pair and typed settings, never a graph.
No saved template, qualification, runtime probe or execution is used here.
"""
from copy import deepcopy
import json
from uuid import UUID, uuid4, uuid5

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.design_ai import DesignDraft
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.user import User
from app.schemas.design_ai import CompositionSettings
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import capability_bindings, catalogue_discovery as discovery, design_ai
from app.services.instance_configuration import validate_builder_configurations
from app.services.parameter_values import effective_parameters, parameter_contract_digest
from app.services.solution_design import service_to_builder_data
from app.services.workflow_compiler import compile_to_wp3_payload

KIND = "catalogue_composed"
SCOPE = "catalogue_pair"
MAX_OPERATIONS = 16
MAX_PAIRS = 8
MAX_PAIR_CHARS = 12000
NAMESPACE = UUID("4f717369-f771-4a15-b2bf-f3bc44aa2150")


def composed(state):
    return (state.get("source") or {}).get("kind") == KIND


def settings_definition(definition):
    return definition.get("execution_parameters") or {"properties": {}}


def safe_settings(definition):
    if definition.get("execution_parameters"):
        try:
            parameter_contract_digest(definition["execution_parameters"])
        except ValueError:
            raise HTTPException(422, "This operation has an unsupported settings contract") from None
    values = []
    for name, spec in settings_definition(definition)["properties"].items():
        # Never expose a path/endpoint/credential as a selectable string setting.
        declared = ([spec["default"]] if "default" in spec else []) + spec.get("enum", [])
        if any(isinstance(v, str) and (len(v) > 80 or discovery.text(v, 1000) != v) for v in declared):
            raise HTTPException(422, "This operation requires settings outside the supported design-only scope")
        values.append({"name": name, "title": discovery.text(spec["title"], 120),
            "description": discovery.text(spec["description"], 240),
            **{k: deepcopy(spec[k]) for k in ("type", "required", "minimum", "maximum", "default", "enum") if k in spec}})
    return values


def engineering(record, identifiers, parameters):
    nodes = []
    for index, (service, contract, definition) in enumerate(record["_operations"]):
        data = {"node_kind": "service", "label": service.name, "service": service_to_builder_data(service),
            "operation_contract": {"contract_id": contract.id, "contract_version": contract.contract_version}}
        if definition.get("execution_parameters"):
            data["configuration"] = {**data["operation_contract"], "parameters": deepcopy(parameters[index])}
        nodes.append({"id": identifiers[index], "type": "default", "position": {"x": 240, "y": 80 + index * 180}, "data": data})
    return {"name": record["label"][:160], "description": record["purpose"], "nodes": nodes,
        "edges": [{"id": identifiers[0] + "-to-" + identifiers[1], "source": identifiers[0], "target": identifiers[1],
            "data": {"connection_kind": "service_connection", "binding": deepcopy(record["_binding"])}}],
        "editing_scope": SCOPE, "run_input": None, "input_policy": None}


def record_for(first, second, db, user):
    operations = []
    if first.id == second.id:
        raise HTTPException(422, "Choose two distinct catalogue operations")
    for service in (first, second):
        contract, definition = discovery.contract_for(db, service)
        if (not discovery.eligible(service, user) or not contract or definition.get("binding_transport") != "whole-output-v1"
                or definition["operation_role"] == "adapter" or service.orchestration_mode != "native" or service.adapter_type
                or service.interface_type != "control" or any(not getattr(service, k) for k in ("container_name", "proto_uri", "image", "operation_name"))
                or len(definition["inputs"]) > 1 or len(definition["outputs"]) > 1):
            raise HTTPException(422, "Only approved native whole-output operations with resolved complete contracts are supported")
        declared = safe_settings(definition)
        if discovery.omit_private_metadata(declared, service) != declared:
            raise HTTPException(422, "Private runtime references cannot be selectable settings")
        operations.append((service, contract, definition))
    if (operations[0][1].operation_identity == operations[1][1].operation_identity
            or len(operations[0][2]["outputs"]) != 1 or len(operations[1][2]["inputs"]) != 1):
        raise HTTPException(422, "A unique source output and downstream input are required")
    output, target = operations[0][2]["outputs"][0], operations[1][2]["inputs"][0]
    if any(discovery.text(s["name"], 1000) != s["name"] for s in (output, target)):
        raise HTTPException(422, "This slot identifier is outside the supported metadata scope")
    binding = {"source_slot": output["name"], "target_slot": target["name"]}
    identifier = discovery.identifier("pair", [first.id, operations[0][1].id, second.id, operations[1][1].id, binding])
    record = {"candidate_id": identifier, "kind": KIND, "label": f"{discovery.text(first.name, 75)} → {discovery.text(second.name, 75)}",
        "purpose": discovery.text(first.description) + " " + discovery.text(second.description), "creation_supported": True,
        "runtime_checked": False, "execution_supported": False, "_operations": operations, "_binding": binding}
    # Binding validation deliberately does not invent missing required settings.
    # Empty configuration envelopes suffice to validate the connection itself.
    preview = engineering(record, ["first", "second"], [{}, {}])
    report = capability_bindings.validate_builder(preview["nodes"], preview["edges"], db)
    if report["status"] != "verified" or len(report["bindings"]) != 1:
        raise HTTPException(422, "No supported single whole-output connection was verified")
    record.update(revision=discovery.revision(db, user, [first, second], {"kind": KIND, "binding": binding}),
        steps=[{"step": step, "title": discovery.text(s.name, 160), "operation": discovery.text(s.operation_name, 120),
                "purpose": discovery.text(s.description), "settings": safe_settings(d)}
               for step, (s, _, d) in zip(("first", "second"), operations)],
        connection=f"Pass one complete {discovery.text(output['semantic_concept'], 160)} reference from the first step to the second",
        declared_binding={**binding, "transport": "whole-output-v1", "schema_fingerprint": design_ai.digest(output["schema_ref"])},
        unresolved_requirements=[{"step": step, "name": name, "title": discovery.text(spec["title"], 120)}
            for step, (_, _, definition) in zip(("first", "second"), operations)
            for name, spec in settings_definition(definition)["properties"].items() if spec.get("required") and "default" not in spec],
        limitations=["New catalogue-composed design; not a registered or qualified experiment.",
            "Exactly two operations and one whole-output connection. No conversion or external input routing.",
            "Runtime readiness, execution, scientific validity and production compatibility are unverified."])
    # Omit known private references embedded in descriptions, without altering authority.
    for service in (first, second):
        public = discovery.omit_private_metadata({k: v for k, v in record.items() if not k.startswith("_")}, service)
        record.update(public)
    return record


def records(db, user):
    user = discovery.actor(db, user)
    rows = discovery.visible_services(db, user, MAX_OPERATIONS + 1)
    operations = rows[:MAX_OPERATIONS]
    pairs, truncated, size = [], len(rows) > MAX_OPERATIONS, 0
    for first in operations:
        for second in operations:
            try:
                record = record_for(first, second, db, user)
            except HTTPException:
                continue
            length = len(json.dumps(public(record)))
            if len(pairs) == MAX_PAIRS or size + length > MAX_PAIR_CHARS:
                truncated = True
                continue
            pairs.append(record); size += length
    return pairs, truncated


def public(record):
    return {k: deepcopy(v) for k, v in record.items() if not k.startswith("_")}


def resolve(candidate_id, db, user, *, lock=False):
    candidates, _ = records(db, user)
    record = next((r for r in candidates if r["candidate_id"] == candidate_id), None)
    if not record:
        raise HTTPException(409, "This operation pair is unavailable or no longer authorized; request a new proposal")
    if lock:
        identifiers = sorted(s.id for s, _, _ in record["_operations"])
        services = db.query(Service).filter(Service.id.in_(identifiers)).order_by(Service.id).with_for_update().populate_existing().all()
        db.query(OperationContract).filter(OperationContract.service_id.in_(identifiers)).order_by(OperationContract.id).with_for_update().populate_existing().all()
        by_id = {s.id: s for s in services}
        if len(by_id) != 2:
            raise HTTPException(409, "An operation is no longer accessible")
        old = record["_operations"]
        record = record_for(by_id[old[0][0].id], by_id[old[1][0].id], db, discovery.actor(db, user))
    return record


def parameters(record, choice):
    choice = choice or CompositionSettings()
    result = []
    for step, (_, _, definition) in zip(("first", "second"), record["_operations"]):
        assignments = getattr(choice, step)
        if len({a.name for a in assignments}) != len(assignments):
            raise HTTPException(422, f"{step}: select each setting only once")
        try:
            result.append(effective_parameters(settings_definition(definition), {a.name: a.value for a in assignments}))
        except ValueError as exc:
            raise HTTPException(422, f"{step}: {exc}. Clarify the required setting before creation.") from None
    return result


def choice_value(parameters):
    return {step: [{"name": k, "value": v} for k, v in sorted(values.items())] for step, values in zip(("first", "second"), parameters)}


def recommendation(record, choice):
    values = parameters(record, choice)
    return {**public(record), "mechanism": KIND, "recommendation_revision": record["revision"],
        "composition_settings": choice_value(values), "creation_request_id": str(uuid4()),
        "composition_review": review(record, values),
        "unresolved_requirements": [], "required_inputs": [], "proposed_settings": {step: value for step, value in zip(("first", "second"), values)},
        "availability": "Design compatibility checked; runtime readiness and execution are unverified and unavailable for this design.",
        "expected_result_view": [], "optional_downloads": []}


def snapshot(record, user):
    return json.loads(json.dumps({"actor": [user.id, user.role, user.node], "binding": record["_binding"],
        "operations": [{"service": {c.name: getattr(s, c.name) for c in Service.__table__.columns},
                        "contract": {c.name: getattr(contract, c.name) for c in OperationContract.__table__.columns}}
                       for s, contract, _ in record["_operations"]]}, default=str))


def review(record, values):
    return {"steps": [{"title": step["title"], "purpose": step["purpose"], "settings": v}
                      for step, v in zip(record["steps"], values)],
        "connection": record["connection"], "binding": deepcopy(record["declared_binding"]),
        "unresolved_requirements": [], "runtime_checked": False, "execution_supported": False}


def pending(state, revision):
    plan = state["composition"]["plan"]
    return {"id": state["composition"]["proposal_id"], "base_revision": revision,
        "turn": {"message": "Review the new two-operation design before Apply.", "edits": []},
        "design": deepcopy(plan["design"]), "validation": deepcopy(plan["validation"]), "composition_review": deepcopy(plan["review"])}


def validate_engineering(design, db, user):
    validate_builder_configurations(db, design["nodes"], design["edges"], user)
    request = WorkflowSubmitRequest(name=design["name"], nodes=[{
        "node_id": n["id"], "service_id": n["data"]["service"]["id"],
        "container_name": n["data"]["service"]["container_name"], "operation_name": n["data"]["service"]["operation_name"],
        **{k: n["data"][k] for k in ("configuration", "operation_contract") if k in n["data"]}}
        for n in design["nodes"]], edges=[{"source": e["source"], "target": e["target"], "binding": e["data"]["binding"]} for e in design["edges"]])
    compiled = compile_to_wp3_payload(request, db)  # Pure compiler; no preflight/adapter/submission call.
    if len(compiled["solution_studio_metadata"]["capability_bindings"]["bindings"]) != 1:
        raise HTTPException(422, "The existing compiler did not preserve the exact binding")


def create(payload, db, user):
    user = discovery.actor(db, user)
    try:
        nonce = str(UUID(payload.creation_request_id or ""))
    except ValueError:
        raise HTTPException(422, "Explicit creation needs its retained request identity") from None
    draft_id = str(uuid5(NAMESPACE, user.id + ":" + nonce))
    spec = {"candidate_id": payload.candidate_id, "revision": payload.recommendation_revision,
            "settings": (payload.composition_settings or CompositionSettings()).model_dump()}
    fingerprint = design_ai.digest(spec)
    db.query(User).filter(User.id == user.id).with_for_update().populate_existing().one()
    user = discovery.actor(db, user)
    existing = db.query(DesignDraft).filter(DesignDraft.id == draft_id, DesignDraft.owner_id == user.id).populate_existing().first()
    if existing:
        if existing.state["composition"]["request_fingerprint"] != fingerprint:
            raise HTTPException(409, "This creation request identity already belongs to a different proposal")
        return design_ai.view(existing, db)
    record = resolve(payload.candidate_id, db, user, lock=True)
    if record["revision"] != payload.recommendation_revision:
        raise HTTPException(409, "The catalogue proposal is stale; request a new recommendation before Create")
    values = parameters(record, payload.composition_settings)
    identifiers = [str(uuid4()), str(uuid4())]
    design = engineering(record, identifiers, values)
    validate_engineering(design, db, user)
    validation = design_ai.validate(design, db, user)
    if not validation["valid"]:
        raise HTTPException(422, "This operation pair cannot produce a valid saved design")
    authority = snapshot(record, user)
    empty = {**deepcopy(design), "nodes": [], "edges": []}
    row = DesignDraft(id=draft_id, owner_id=user.id, revision=0, state={
        "source": {"kind": KIND, "candidate_id": record["candidate_id"], "revision": record["revision"], "authority_sha256": design_ai.digest(authority)},
        "design": empty, "validation": design_ai.validate(empty, db, user), "history": [], "edit_history": [],
        "reference_note": "New catalogue-composed design; no saved template or qualified execution is copied.",
        "reserved_solution_id": str(uuid4()), "saved_solution_id": None, "saved_revision": None, "dirty": True,
        "guided_experiment": None, "composition": {"request_fingerprint": fingerprint, "instance_ids": identifiers,
            "authority": authority, "settings": choice_value(values), "proposal_id": str(uuid4()),
            "plan": {"design": design, "validation": validation, "review": review(record, values)}}})
    row.state = {**row.state, "pending": pending(row.state, 0)}
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(DesignDraft).filter(DesignDraft.id == draft_id, DesignDraft.owner_id == user.id).first()
        if not existing or existing.state["composition"]["request_fingerprint"] != fingerprint:
            raise HTTPException(409, "Another creation request claimed this identity") from None
        row = existing
    return design_ai.view(row, db)


def revalidate(row, db, user, *, lock=True):
    record = resolve(row.state["source"]["candidate_id"], db, discovery.actor(db, user), lock=lock)
    if (record["revision"] != row.state["source"]["revision"]
            or snapshot(record, user) != row.state["composition"]["authority"]):
        raise HTTPException(409, "The catalogue or contract authority changed; this proposal must be reviewed anew")
    values = parameters(record, CompositionSettings.model_validate(row.state["composition"]["settings"]))
    design = engineering(record, row.state["composition"]["instance_ids"], values)
    if design != row.state["composition"]["plan"]["design"]:
        raise HTTPException(409, "The preserved proposal does not match its authority snapshot")
    validate_engineering(design, db, user)
    return design


def apply(row, revision, proposal_id, db, user):
    proposal = row.state.get("pending")
    if not proposal or proposal["id"] != proposal_id or proposal["base_revision"] != revision:
        raise HTTPException(409, "This proposal is no longer current")
    design = revalidate(row, db, user)
    if design != proposal["design"]:
        raise HTTPException(409, "The proposal changed; request a fresh review")
    state = deepcopy(row.state)
    state["history"].append({"design": state["design"], "validation": state["validation"]})
    state.update(design=design, validation=design_ai.validate(design, db, user), pending=None, dirty=True)
    state["edit_history"].append({"revision": revision + 1, "edits": ["create_catalogue_pair"]})
    row.state, row.revision = state, revision + 1
    db.commit()
    return design_ai.view(row, db)


def require_save(row, db, user):
    if row.state.get("pending") or not row.state["design"]["nodes"]:
        raise HTTPException(409, "Apply the two-operation proposal before Save")
    if revalidate(row, db, user) != row.state["design"]:
        raise HTTPException(409, "The applied design differs from its reviewed proposal")


def context(row):
    return {"source_kind": KIND, "editing_scope": SCOPE, "supported_edits": [],
        "review": deepcopy(row.state["composition"]["plan"]["review"]),
        "applied": bool(row.state["design"]["nodes"]), "runtime_checked": False, "execution_supported": False,
        "scope": "Explain this two-operation design only. Explicit Apply, Undo and Save controls change it; no additional edits or execution are supported."}


def design_only(metadata):
    return bool(metadata and ((metadata.get("source") or {}).get("kind") == KIND
                              or metadata.get("execution_policy") == "design_only_catalogue_pair"))


def require_execution_allowed(workflow, db, user):
    from app.models.solution import Solution
    from app.dependencies.auth import can_manage_owned_record
    if workflow.solution_id:
        solution = db.get(Solution, workflow.solution_id)
        if solution and design_only(solution.design_metadata):
            if not can_manage_owned_record(user, solution.created_by_user_id):
                raise HTTPException(403, "You can only access your own solutions")
            raise HTTPException(403, "This catalogue-composed design has no qualified runtime or execution path. Design review only.")
