"""Conversation and reviewed edits around ONE canonical saved Solution.

DesignDraft retains conversation/proposals only. It never contains an editable
solution graph and never submits execution. Apply uses Builder's normal writer.
"""
from copy import deepcopy
import hashlib
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.design_ai import DesignDraft
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.solution import SolutionUpdate
from app.services.instance_configuration import validate_builder_configurations
from app.services.parameter_values import effective_parameters
from app.services.solution_design import service_to_builder_data
from app.services.solution_editing import owned_solution, update


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def content(solution):
    return {key: deepcopy(getattr(solution, key)) for key in ("name", "description", "nodes", "edges", "design_metadata")}


def conversation(solution, db, user, *, lock=False, create=False):
    identifier = str(uuid5(NAMESPACE_URL, f"ai-effect:saved-solution:{solution.id}:{user.id}"))
    query = db.query(DesignDraft).filter(DesignDraft.id == identifier, DesignDraft.owner_id == user.id)
    if lock: query = query.with_for_update().populate_existing()
    row = query.first()
    if row is None and create:
        row = DesignDraft(id=identifier, owner_id=user.id, revision=0,
                          state={"kind": "saved_solution_conversation", "solution_id": solution.id, "messages": [], "pending": None})
        db.add(row)
        try: db.commit(); db.refresh(row)
        except IntegrityError:
            db.rollback(); row = query.first()
    if row and (row.state.get("kind") != "saved_solution_conversation" or row.state.get("solution_id") != solution.id):
        raise HTTPException(409, "Conversation association differs from this saved solution")
    return row


def view(solution, row):
    return {"solution_id": solution.id, "expected_updated_at": solution.updated_at.isoformat(),
            "conversation_revision": row.revision if row else 0,
            "can_undo": bool(row and row.state.get("last_applied") and row.state["last_applied"]["updated_at"] == solution.updated_at.isoformat()),
            "messages": deepcopy(row.state.get("messages", [])) if row else [],
            "clarification": deepcopy(row.state.get("clarification")) if row else None,
            "catalogue_used": deepcopy(row.state.get("catalogue_used")) if row else None,
            "pending": ({key: deepcopy(row.state["pending"][key]) for key in ("id", "changes", "base_updated_at")}
                        if row and row.state.get("pending") else None)}


def check(solution, row, version, revision):
    if solution.status == "archived": raise HTTPException(409, "Restore the saved solution before editing")
    if solution.updated_at.isoformat() != version or (row.revision if row else 0) != revision:
        raise HTTPException(409, "The solution or conversation changed. Reload before requesting or applying edits.")


def active_contract(service, db):
    if service is None: return None
    return db.query(OperationContract).filter(OperationContract.service_id == service.id,
        OperationContract.runtime_operation_name == service.operation_name, OperationContract.status == "active").first()


def authority(nodes, db):
    """Pin provider definitions and runtime metadata as well as the editable graph."""
    from app.services.parameter_discovery import reviewed_service_digest
    ids = sorted({n["data"]["service"]["id"] for n in nodes if isinstance(n.get("data", {}).get("service"), dict)})
    result = []
    for identifier in ids:
        service = db.get(Service, identifier)
        if service is None: raise HTTPException(409, "A proposed service is no longer available")
        contract = active_contract(service, db)
        result.append({"id": identifier, "runtime": reviewed_service_digest(service), "version": service.version,
                       "status": service.status, "lifecycle_status": service.lifecycle_status,
                       "contract": {"id": contract.id, "version": contract.contract_version, "definition": contract.definition} if contract else None})
    return digest(result)


def selectable(service):
    return service is not None and service.status in {"approved", "validated"} and service.lifecycle_status not in {"archived", "deprecated"}


def context(solution, row, message, db, user):
    from app.services.assistant_catalogue import retrieve, actions
    catalogue = retrieve(db,user,solution,row,message)
    steps = []
    for node in solution.nodes:
        data = node.get("data", {}); reference = data.get("service")
        if not isinstance(reference, dict): continue
        service = db.get(Service, reference.get("id"))
        if service is None: raise HTTPException(409, "A saved service is unavailable; review it in Builder")
        contract = active_contract(service, db)
        steps.append({"node_id": node["id"], "label": data.get("label") or service.name, "service_id": service.id,
                      "operation_name": service.operation_name, "configuration": data.get("configuration"),
                      "contract": {"contract_id": contract.id, "contract_version": contract.contract_version,
                                   "definition": contract.definition} if contract else None})
    return {"mode": "saved_solution", "request": message, "history": (row.state.get("messages", [])[-12:] if row else []),
            "solution": {"id": solution.id, "name": solution.name, "description": solution.description,
                         "steps": steps, "connections": [{"source": e["source"], "target": e["target"],
                            "binding": (e.get("data") or {}).get("binding")} for e in solution.edges],
                         "workflow_input_selected": (solution.design_metadata or {}).get("run_input") is not None},
            "pending_clarification": deepcopy(row.state.get('clarification')) if row else None,
            "pending_proposal": ({k:deepcopy(row.state['pending'][k]) for k in ('id','changes','base_updated_at')}
                if row and row.state.get('pending') else None),
            "catalogue": catalogue, "compatible_actions": actions(solution,catalogue,db,user),
            "limits": {"service_instances": 24, "edits_per_proposal": 10}, "supported_actions": ["rename", "describe", "set_node_label", "set_node_parameters",
                "add_service", "remove_service", "replace_service", "connect", "disconnect"],
            "input_selection": "Use Builder's existing input controls. Data and credentials are not model-editable settings.",
            "execution": "No chat action executes anything. Apply and save requires a separate explicit action; Run stays in Builder."}


def parsed(value, allowed):
    try: result = json.loads(value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError): raise HTTPException(422, "Edit data must be valid JSON") from None
    if not isinstance(result, dict) or set(result) - set(allowed):
        raise HTTPException(422, "Edit contains unsupported fields")
    return result


def candidate(solution, edits, allocations, db, user):
    result = content(solution); nodes, edges = result["nodes"], result["edges"]
    changes = []
    def node(identifier):
        identifier = allocations.get(identifier, identifier)
        matches = [n for n in nodes if n["id"] == identifier and isinstance(n.get("data", {}).get("service"), dict)]
        if len(matches) != 1: raise HTTPException(422, "Select one existing service instance")
        return matches[0]
    def service_data(service_id, parameters):
        service = db.get(Service, service_id) if isinstance(service_id, str) else None
        if not selectable(service): raise HTTPException(422, "Select an approved active catalogue service")
        data = {"node_kind": "service", "label": service.name, "service": service_to_builder_data(service)}
        contract = active_contract(service, db)
        if contract and contract.definition.get("execution_parameters"):
            if not isinstance(parameters, dict): raise HTTPException(422, "Service settings must be an object")
            try: effective_parameters(contract.definition["execution_parameters"], parameters)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
            data["configuration"] = {"contract_id": contract.id, "contract_version": contract.contract_version, "parameters": deepcopy(parameters)}
        elif parameters:
            raise HTTPException(422, "This service has no published adjustable settings")
        if contract and contract.definition.get("binding_transport"):
            data["operation_contract"] = {"contract_id": contract.id, "contract_version": contract.contract_version}
        return data
    def review_data(data):
        service = db.get(Service, data["service"]["id"])
        contract = active_contract(service, db)
        parameters = contract.definition.get("execution_parameters") if contract else None
        return {"service_id": service.id, "operation": service.operation_name,
                "contract_version": contract.contract_version if contract else None,
                "effective_settings": effective_parameters(parameters, data.get("configuration", {}).get("parameters", {})) if parameters else {},
                "requested_overrides":deepcopy(data.get('configuration',{}).get('parameters',{})),
                "setting_labels":{k:v.get('title',k.replace('_',' ')) for k,v in (parameters or {}).get('properties',{}).items()},
                "published_inputs": contract.definition.get("inputs", []) if contract else [],
                "published_outputs": contract.definition.get("outputs", []) if contract else []}
    for edit in edits:
        if edit.kind in {"rename", "describe"}:
            key = "name" if edit.kind == "rename" else "description"
            if not edit.value.strip() or len(edit.value) > 2000: raise HTTPException(422, "Supply a clear solution name or description")
            changes.append({"action": edit.kind, "before": result[key], "after": edit.value}); result[key] = edit.value
        elif edit.kind == "set_node_label":
            target = node(edit.node_id)
            if not edit.value.strip() or len(edit.value) > 200: raise HTTPException(422, "Supply a short step label")
            changes.append({"action": edit.kind, "step": target["data"].get("label"), "before": target["data"].get("label"), "after": edit.value})
            target["data"]["label"] = edit.value
        elif edit.kind == "set_node_parameters":
            target = node(edit.node_id); data = target["data"]; old = deepcopy(data.get("configuration"))
            service = db.get(Service, data["service"]["id"]); contract = active_contract(service, db)
            patch = parsed(edit.value, contract.definition.get("execution_parameters", {}).get("properties", {}) if contract else {})
            if not contract or not contract.definition.get("execution_parameters"): raise HTTPException(422, "No published settings for this step")
            if old and (old["contract_id"] != contract.id or old["contract_version"] != contract.contract_version):
                raise HTTPException(409, "Review the changed parameter contract in Builder before editing")
            values = {**((old or {}).get("parameters") or {}), **patch}
            data["configuration"] = {"contract_id": contract.id, "contract_version": contract.contract_version, "parameters": values}
            try:
                effective = effective_parameters(contract.definition["execution_parameters"], values)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
            changes.append({"action": edit.kind, "step": data.get("label"), "before": effective_parameters(contract.definition["execution_parameters"], (old or {}).get("parameters", {})), "after": effective, "requested_overrides": patch,
                "setting_labels":{k:v.get('title',k.replace('_',' ')) for k,v in contract.definition['execution_parameters']['properties'].items()}})
        elif edit.kind == "add_service":
            value = parsed(edit.value, {"service_id", "local_ref", "parameters"})
            reference = value.get("local_ref")
            if not isinstance(reference, str) or not reference or len(reference) > 80 or reference in {n["id"] for n in nodes}:
                raise HTTPException(422, "New services need a unique proposal-local reference")
            if reference not in allocations: allocations[reference] = "service-" + str(uuid4())
            if any(n["id"] == allocations[reference] for n in nodes): raise HTTPException(422, "Duplicate proposed service reference")
            data = service_data(value.get("service_id"), value.get("parameters", {}))
            nodes.append({"id": allocations[reference], "type": "default", "position": {"x": 240, "y": 80 + len(nodes) * 160}, "data": data})
            changes.append({"action": edit.kind, "after": data["label"], **review_data(data)})
        elif edit.kind == "remove_service":
            target = node(edit.node_id); nodes.remove(target)
            edges[:] = [e for e in edges if target["id"] not in {e["source"], e["target"]}]
            changes.append({"action": edit.kind, "before": target["data"].get("label")})
        elif edit.kind == "replace_service":
            target = node(edit.node_id); value = parsed(edit.value, {"service_id", "parameters"})
            old = target["data"]; target["data"] = service_data(value.get("service_id"), value.get("parameters", {}))
            changes.append({"action": edit.kind, "before": old.get("label"), "after": target["data"]["label"],
                            **review_data(target["data"])})
        elif edit.kind in {"connect", "disconnect"}:
            value = parsed(edit.value, {"source", "target", "source_slot", "target_slot"})
            source, target = node(value.get("source")), node(value.get("target"))
            matches = [e for e in edges if e["source"] == source["id"] and e["target"] == target["id"]]
            if edit.kind == "disconnect":
                if len(matches) != 1: raise HTTPException(422, "Select an existing unambiguous connection")
                edges.remove(matches[0])
            else:
                if matches: raise HTTPException(422, "That connection already exists")
                if not source["data"].get("operation_contract") or not target["data"].get("operation_contract"):
                    raise HTTPException(422, "New chat connections require provider-published I/O contracts; JSON labels alone do not establish compatibility")
                if not isinstance(value.get("source_slot"), str) or not isinstance(value.get("target_slot"), str):
                    raise HTTPException(422, "Choose the published output and input slots")
                edges.append({"id": source["id"] + "-to-" + target["id"], "source": source["id"], "target": target["id"],
                              "data": {"connection_kind": "service_connection", "binding": {"source_slot": value["source_slot"], "target_slot": value["target_slot"]}}})
            changes.append({"action": edit.kind, "source": source["data"].get("label"), "target": target["data"].get("label"), "binding": value if edit.kind == "connect" else (matches[0].get("data") or {}).get("binding")})
    if len([n for n in nodes if n.get("data", {}).get("service")]) > 24:
        raise HTTPException(422, "This workspace supports up to 24 service instances per reviewed edit")
    from app.services.workflow_boundaries import complete
    if edits and complete(nodes,edges):
        changes.append({'action':'workflow_boundaries','after':'Connect Workflow Input to each starting step and each final step to Workflow Output. Data selection remains in Builder; these display edges are excluded from service compilation.'})
    validate_builder_configurations(db, nodes, edges, user)
    # The current compiler has no feedback-loop runtime. Reject cycles rather
    # than labelling a deadlocking graph runnable.
    remaining = {n["id"] for n in nodes}
    while remaining:
        ready = {key for key in remaining if not any(e["target"] == key and e["source"] in remaining for e in edges)}
        if not ready: raise HTTPException(422, "This execution path does not support feedback cycles")
        remaining -= ready
    return result, changes


def propose(solution, row, message, turn, db, user, *, catalogue_used=None):
    if turn.edits or turn.template_key is not None or turn.composition_settings or turn.registered_settings or turn.recommended_seed is not None or (turn.discovery and turn.discovery.candidate_id) or turn.expected_revision is not None:
        raise HTTPException(502, "The assistant returned legacy workflow authority instead of saved-solution edits")
    state = deepcopy(row.state)
    allocations = {}; edits = turn.solution_edits or []
    clarification = turn.discovery and turn.discovery.outcome == 'clarification_needed'
    if clarification and edits: raise HTTPException(502,'Clarification cannot also propose design changes')
    pending = None
    if edits:
        result, changes = candidate(solution, edits, allocations, db, user)
        pending = {"id": str(uuid4()), "base_updated_at": solution.updated_at.isoformat(), "base_sha256": digest(content(solution)),
                   "candidate_sha256": digest(result), "authority_sha256": authority(result["nodes"], db), "edits": [e.model_dump() for e in edits], "allocations": allocations, "changes": changes}
    reply = {'role':'assistant','content':turn.message}
    if clarification:
        reply['question'] = turn.discovery.question
        state['clarification'] = {'request':(state.get('clarification') or {}).get('request',message),'question':turn.discovery.question}
    elif edits: state['clarification'] = None
    if catalogue_used is not None:
        state['catalogue_used'] = {'services':[{'service_id':c['service_id'],'name':c['name'],'operation':c['operation_name'],
            'contract_version':c['contract']['contract_version'] if c['contract'] else None} for c in catalogue_used['services']],
            'truncated':catalogue_used['truncated'],'total_accessible':catalogue_used['total_accessible'],
            'compatible_connections':catalogue_used['compatible_connections']}
    state["messages"] = (state.get("messages", []) + [{"role": "user", "content": message}, reply])[-24:]
    # An explanation or clarification does not erase an already reviewed proposal.
    if edits: state["pending"] = pending
    row.state = state; row.revision += 1
    db.commit(); db.refresh(row)
    return view(solution, row)


def apply(solution_id, payload, db, user):
    from app.schemas.design_ai import SolutionEdit
    solution = owned_solution(solution_id, db, user, lock=True)
    row = conversation(solution, db, user, lock=True)
    check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    pending = row.state.get("pending") if row else None
    if not pending or pending["id"] != payload.proposal_id:
        raise HTTPException(409, "This proposal is no longer pending")
    if pending["base_updated_at"] != solution.updated_at.isoformat() or pending["base_sha256"] != digest(content(solution)):
        raise HTTPException(409, "Builder changed the saved solution. Request a new proposal against its current version.")
    result, _ = candidate(solution, [SolutionEdit.model_validate(e) for e in pending["edits"]], deepcopy(pending["allocations"]), db, user)
    if digest(result) != pending["candidate_sha256"] or authority(result["nodes"], db) != pending["authority_sha256"]:
        raise HTTPException(409, "Catalogue settings changed after review. Request a new proposal before applying.")
    before = content(solution)
    try:
        solution = update(solution_id, SolutionUpdate(expected_updated_at=payload.expected_updated_at, **result), db, user, commit=False)
        state = deepcopy(row.state); state["pending"] = None
        state["last_applied"] = {"id": pending["id"], "before": before, "updated_at": solution.updated_at.isoformat(), "sha256": digest(content(solution))}
        row.state = state; row.revision += 1
        db.commit(); db.refresh(solution); db.refresh(row)
        return view(solution, row)
    except Exception:
        db.rollback(); raise


def undo(solution_id, payload, db, user):
    solution = owned_solution(solution_id, db, user, lock=True)
    row = conversation(solution, db, user, lock=True)
    check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    last = row.state.get("last_applied") if row else None
    if not last or last["updated_at"] != solution.updated_at.isoformat() or last["sha256"] != digest(content(solution)):
        raise HTTPException(409, "Undo is unavailable because the saved solution changed after applying the proposal")
    try:
        solution = update(solution_id, SolutionUpdate(expected_updated_at=payload.expected_updated_at, **last["before"]), db, user, commit=False)
        state = deepcopy(row.state); state["last_applied"] = None; state["pending"] = None
        row.state = state; row.revision += 1
        db.commit(); db.refresh(solution); db.refresh(row)
        return view(solution, row)
    except Exception:
        db.rollback(); raise
