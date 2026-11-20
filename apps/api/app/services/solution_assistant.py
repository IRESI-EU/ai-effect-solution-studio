"""Conversation and reviewed edits around ONE canonical saved Solution.

DesignDraft retains conversation/proposals only. It never contains an editable
solution graph and never submits execution. Apply uses Builder's normal writer.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
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


def view(solution, row, db=None, user=None):
    pending = row.state.get('pending') if row else None
    review = None
    if pending:
        review = {key: deepcopy(pending[key]) for key in ('id', 'changes', 'base_updated_at')}
        review['supersedes'] = pending.get('supersedes')
        try:
            if db is None or user is None: raise HTTPException(409, 'Reload the current review')
            result = materialize(solution, pending, db, user)
            review.update(current=True, candidate=projection(solution, result, db, pending=pending))
        except HTTPException as exc:
            review.update(current=False, candidate=None, unavailable_reason=str(exc.detail))
    last = row.state.get('last_applied') if row else None
    applied = bool(last and last['updated_at'] == solution.updated_at.isoformat() and last['sha256'] == digest(content(solution)))
    return {"solution_id": solution.id, "expected_updated_at": solution.updated_at.isoformat(),
            "application_notice": "The reviewed changes were applied and saved. Run remains a separate action." if applied else None,
            "conversation_revision": row.revision if row else 0,
            "can_undo": bool(row and row.state.get("last_applied") and row.state["last_applied"]["updated_at"] == solution.updated_at.isoformat()),
            "messages": deepcopy(row.state.get("messages", [])) if row else [],
            "clarification": deepcopy(row.state.get("clarification")) if row else None,
            "catalogue_used": deepcopy(row.state.get("catalogue_used")) if row else None,
            "pending": review}


def edit_base(solution, row, pending=None):
    return {'kind': 'pending' if pending else 'saved', 'expected_updated_at': solution.updated_at.isoformat(),
            'conversation_revision': row.revision if row else 0, 'proposal_id': pending['id'] if pending else None,
            'candidate_sha256': pending['candidate_sha256'] if pending else None}


def target_ref(solution, identifier, pending=None):
    # Scope references to this solution AND exact saved/proposal base. Proposed
    # node IDs remain stable across revisions; eligibility references rotate.
    return 'instance_' + digest([solution.id, solution.updated_at.isoformat(), pending['id'] if pending else 'saved', identifier])[:32]


def projection(solution, result, db, *, pending=None):
    """Allowlisted read-only view, never a second persisted/editable graph."""
    steps = []
    for n in result['nodes']:
        data = n.get('data', {}); reference = data.get('service')
        if not isinstance(reference, dict): continue
        service = db.get(Service, reference['id']); contract = active_contract(service, db)
        if service is None: raise HTTPException(409, 'A selected service is unavailable')
        parameters = contract.definition.get('execution_parameters') if contract else None
        overrides = deepcopy((data.get('configuration') or {}).get('parameters', {}))
        steps.append({'node_id': n['id'], 'target_ref': target_ref(solution, n['id'], pending),
                      'label': data.get('label') or service.name, 'service_id': service.id,
                      'operation_name': service.operation_name,
                      'contract': {'contract_id': contract.id, 'contract_version': contract.contract_version,
                                   'definition': contract.definition} if contract else None,
                      'effective_settings': effective_parameters(parameters, overrides) if parameters else {},
                      'requested_overrides': overrides,
                      'setting_labels': {k:v.get('title', k.replace('_', ' ')) for k,v in (parameters or {}).get('properties', {}).items()}})
    refs = {n['node_id']: n['target_ref'] for n in steps}
    return {'name': result['name'], 'description': result['description'], 'steps': steps,
            'connections': [{'source': refs[e['source']], 'target': refs[e['target']],
                             'binding': deepcopy((e.get('data') or {}).get('binding'))}
                            for e in result['edges'] if e['source'] in refs and e['target'] in refs],
            'assumptions': deepcopy(pending.get('assumptions', [c['after'] for c in pending['changes'] if c['action']=='proposed_assumption'])) if pending else [],
            'prior_assumptions': deepcopy(pending.get('prior_assumptions', [])) if pending else [],
            'proposal_id': pending['id'] if pending else None,
            'base_updated_at': solution.updated_at.isoformat(), 'candidate_sha256': digest(result),
            'workflow_input_selected': (result.get('design_metadata') or {}).get('run_input') is not None}


def materialize(solution, pending, db, user):
    """Replay stored cumulative edits against the owned saved base with normal validators."""
    if pending['base_updated_at'] != solution.updated_at.isoformat() or pending['base_sha256'] != digest(content(solution)):
        raise HTTPException(409, 'Builder changed the saved solution. Request a new proposal against its current version.')
    try:
        result = replay(solution, pending['edits'], pending.get('batch_sizes', [len(pending['edits'])]), pending['allocations'], db, user)
    except HTTPException as exc:
        raise HTTPException(409, 'The pending candidate is no longer valid; review catalogue authority and Builder changes') from exc
    if digest(result) != pending['candidate_sha256'] or authority(result['nodes'], db) != pending['authority_sha256']:
        raise HTTPException(409, 'Catalogue settings changed after review. Request a new proposal before applying.')
    return result


def replay(solution, edits, batch_sizes, allocations, db, user):
    """Replay normal editor batches, including its deterministic boundary layout.

    Only edits/allocations are stored. Batch boundaries preserve the exact order
    and positions of additions across multiple reviews; there is no second graph.
    """
    from app.schemas.design_ai import SolutionEdit
    if sum(batch_sizes) != len(edits) or any(n < 1 for n in batch_sizes):
        raise HTTPException(409, 'Invalid cumulative proposal replay')
    result = content(solution); offset = 0
    for size in batch_sizes:
        result, _ = candidate(SimpleNamespace(**result), [SolutionEdit.model_validate(e) for e in edits[offset:offset+size]], deepcopy(allocations), db, user)
        offset += size
    return result


def resolve_edits(solution, result, edits, db, pending=None):
    """Resolve only exact scoped instance refs and this turn's new local refs."""
    from app.schemas.design_ai import SolutionEdit
    eligible = {target_ref(solution, n['id'], pending): n['id'] for n in result['nodes'] if isinstance(n.get('data', {}).get('service'), dict)}
    local = set(); resolved = []
    catalogue_ids = {n['data']['service']['id'] for n in result['nodes'] if n.get('data', {}).get('service')}
    def instance(ref):
        if isinstance(ref, str) and ref in eligible: return eligible[ref]
        if isinstance(ref, str) and ref in local: return ref
        raise HTTPException(422, 'Select one existing service instance using its current target_ref; catalogue IDs are not instance references')
    for edit in edits:
        value = edit.value; node_id = edit.node_id
        if edit.kind in {'set_node_label', 'set_node_parameters', 'remove_service', 'replace_service'}:
            node_id = instance(node_id)
        if edit.kind == 'add_service':
            data = parsed(value, {'service_id', 'local_ref', 'parameters'}); ref = data.get('local_ref')
            if not isinstance(ref, str) or not ref or ref.startswith('instance_') or ref in local or ref in eligible or ref in catalogue_ids or ref == data.get('service_id') or db.get(Service, ref) is not None:
                raise HTTPException(422, 'New services need a unique proposal-local reference distinct from catalogue and instance references')
            local.add(ref)
        elif edit.kind in {'connect', 'disconnect'}:
            data = parsed(value, {'source', 'target', 'source_slot', 'target_slot'})
            data['source'] = instance(data.get('source')); data['target'] = instance(data.get('target'))
            value = json.dumps(data)
        if edit.kind == 'remove_service':
            eligible = {r:n for r,n in eligible.items() if n != node_id}; local.discard(node_id)
        resolved.append(SolutionEdit(kind=edit.kind, node_id=node_id, value=value))
    return resolved


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
    saved_projection = projection(solution, content(solution), db)
    pending = row.state.get('pending') if row else None
    pending_projection = None; pending_error = None
    if pending:
        try:
            result = materialize(solution, pending, db, user)
            pending_projection = projection(solution, result, db, pending=pending)
        except HTTPException as exc: pending_error = str(exc.detail)
    saved_base = edit_base(solution, row)
    pending_base = edit_base(solution, row, pending) if pending_projection else None
    # Compatible actions use the same validator, for each declared base. Replace
    # raw node IDs with scoped references before presenting them to the provider.
    def scoped_actions(result, proposal=None):
        choices = actions(SimpleNamespace(**result), catalogue, db, user)
        for item in choices['replacements']: item['node_id'] = target_ref(solution, item['node_id'], proposal)
        for item in choices['add_after']: item['source_node_id'] = target_ref(solution, item['source_node_id'], proposal)
        return choices
    return {'mode': 'saved_solution', 'request': message, 'history': (row.state.get('messages', [])[-12:] if row else []),
            'solution': {'id': solution.id, **saved_projection},
            'saved_design': saved_projection, 'pending_candidate': pending_projection,
            'edit_bases': {'saved': saved_base, 'pending': pending_base},
            'pending_unavailable_reason': pending_error,
            'pending_clarification': deepcopy(row.state.get('clarification')) if row else None,
            'pending_proposal': ({'id': pending['id'], 'base_updated_at': pending['base_updated_at'],
                                  'changes': deepcopy(pending['changes']), 'current': pending_projection is not None} if pending else None),
            'catalogue': catalogue, 'compatible_actions': scoped_actions(content(solution)),
            'pending_compatible_actions': scoped_actions(result, pending) if pending_projection else None,
            'limits': {'service_instances': 24, 'edits_per_proposal': 10, 'cumulative_edits': 80},
            'supported_actions': ['rename', 'describe', 'set_node_label', 'set_node_parameters', 'add_service',
                                  'remove_service', 'replace_service', 'connect', 'disconnect'],
            'input_selection': "Use Builder's existing input controls. Data and credentials are not model-editable settings.",
            'execution': 'Chat never applies or executes. Apply and save requires a separate explicit action; Run stays in Builder.'}


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
            if not patch: raise HTTPException(422, "Choose at least one supported setting to change")
            values = {**((old or {}).get("parameters") or {}), **patch}
            data["configuration"] = {"contract_id": contract.id, "contract_version": contract.contract_version, "parameters": values}
            try:
                effective = effective_parameters(contract.definition["execution_parameters"], values)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
            changes.append({"action": edit.kind, "instance_id": target["id"], "step": data.get("label") or service.name, "before": effective_parameters(contract.definition["execution_parameters"], (old or {}).get("parameters", {})), "after": effective, "requested_overrides": patch,
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


def setting_difference(changes):
    result = []
    for change in changes:
        if change['action'] != 'set_node_parameters': continue
        for name, after in change['after'].items():
            before = change['before'].get(name)
            if name in change['before'] and digest(before) == digest(after): continue
            result.append({'instance_id':change['instance_id'], 'step':change['step'],
                'parameter':name, 'label':change['setting_labels'].get(name,name),
                'before':before, 'before_present':name in change['before'], 'after':after})
    return result


def setting_summary(changes, differences, base_kind):
    """Only validated application facts; no interpretation of the user's words."""
    if differences:
        parts = [f"{d['step']} ({d['instance_id'][-8:]}): {d['label']} "
                 f"{json.dumps(d['before'],ensure_ascii=False) if d['before_present'] else 'not set'} → {json.dumps(d['after'],ensure_ascii=False)}"
                 for d in differences]
        message = 'Proposed setting changes: ' + '; '.join(parts) + '. These changes have not been applied; Run remains a separate action.'
    else:
        parts = [f"{c['step']} ({c['instance_id'][-8:]}): {c['setting_labels'].get(k,k)} is already {json.dumps(c['after'][k],ensure_ascii=False)}"
                 for c in changes if c['action']=='set_node_parameters' for k in c['requested_overrides']]
        message = 'No change needed in the ' + ('proposed' if base_kind=='pending' else 'saved') + ' design: ' + '; '.join(parts) + '. '
        message += ('The existing pending review is retained. ' if base_kind=='pending' else '') + 'This request made no design changes and did not run the workflow.'
    return message, {'source':'application_diff','base_kind':base_kind,
                     'status':'proposed' if differences else 'no_change','changes':differences}


def propose(solution, row, message, turn, db, user, *, catalogue_used=None, assumptions=(), outcome=None, base=None):
    if turn.edits or turn.template_key is not None or turn.composition_settings or turn.registered_settings or turn.recommended_seed is not None or (turn.discovery and turn.discovery.candidate_id) or turn.expected_revision is not None:
        raise HTTPException(502, "The assistant returned legacy workflow authority instead of saved-solution edits")
    state = deepcopy(row.state)
    allocations = {}; edits = turn.solution_edits or []
    clarification = turn.discovery and turn.discovery.outcome == 'clarification_needed'
    if clarification and edits: raise HTTPException(502,'Clarification cannot also propose design changes')
    pending = None; change_summary = None; actual_message = turn.message
    setting_only = bool(edits) and all(e.kind == "set_node_parameters" for e in edits)
    if edits:
        if base is None: raise HTTPException(422, 'An explicit current edit base is required')
        check(solution, row, base.expected_updated_at, base.conversation_revision)
        if setting_only and state.get('pending') and base.kind != 'pending':
            raise HTTPException(409, 'Revise the current pending review or dismiss it explicitly before editing the saved design')
        previous = None; prior_edits = []; disclosures = []; batches = []
        if base.kind == 'pending':
            previous = state.get('pending')
            if not previous or previous['id'] != base.proposal_id or previous['candidate_sha256'] != base.candidate_sha256:
                raise HTTPException(409, 'This pending proposal has been superseded or does not belong to this review')
            original = materialize(solution, previous, db, user)
            allocations = deepcopy(previous['allocations'])
            prior_edits = deepcopy(previous['edits'])
            batches = deepcopy(previous.get('batch_sizes', [len(prior_edits)]))
            disclosures = [*previous.get('prior_assumptions', []), *previous.get('assumptions', [c['after'] for c in previous['changes'] if c['action']=='proposed_assumption'])]
        else:
            original = content(solution)
        # Resolve before the normal editor. No service-ID fallback or guesses.
        edits = resolve_edits(solution, original, edits, db, previous)
        delta_allocations = {} # additions allocate once, then replay with the same IDs
        revised, changes = candidate(SimpleNamespace(**original), edits, delta_allocations, db, user)
        if setting_only:
            differences = setting_difference(changes)
            actual_message, change_summary = setting_summary(changes, differences, base.kind)
            if not differences: edits = []
        if edits:
            if set(allocations) & set(delta_allocations):
                raise HTTPException(422, 'Use fresh proposal-local references for additional instances')
            allocations.update(delta_allocations)
            cumulative = prior_edits + [e.model_dump() for e in edits]
            if len(cumulative) > 80: raise HTTPException(422, 'Apply or dismiss this review before requesting further revisions')
            batches.append(len(edits))
            result = replay(solution, cumulative, batches, allocations, db, user)
            if digest(result) != digest(revised): raise HTTPException(409, 'Cumulative proposal replay differs from the reviewed candidate')
            disclosures = list(dict.fromkeys(disclosures))
            if len(disclosures) > 12: raise HTTPException(422, 'Review existing assumptions before adding more')
            changes = [{'action': 'proposed_assumption', 'after': text} for text in assumptions] + changes
            pending = {'id': str(uuid4()), 'base_updated_at': solution.updated_at.isoformat(), 'base_sha256': digest(content(solution)),
                       'candidate_sha256': digest(result), 'authority_sha256': authority(result['nodes'], db),
                       'edits': cumulative, 'batch_sizes': batches, 'allocations': allocations, 'changes': changes, 'assumptions': list(assumptions), 'prior_assumptions': disclosures,
                       'supersedes': previous['id'] if previous else None}
    reply = {'role':'assistant','content':actual_message}
    if change_summary is not None:
        reply['change_summary'] = change_summary
        outcome = 'proposal' if edits else 'answer'
    if outcome is not None:
        reply.update(outcome=outcome, assumptions=[] if setting_only and not edits else list(assumptions))
    if clarification:
        reply['question'] = turn.discovery.question
        state['clarification'] = {'request':(state.get('clarification') or {}).get('request',message),'question':turn.discovery.question}
    elif edits or change_summary is not None: state['clarification'] = None
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
    return view(solution, row, db, user)


def apply(solution_id, payload, db, user):
    solution = owned_solution(solution_id, db, user, lock=True)
    row = conversation(solution, db, user, lock=True)
    check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    pending = row.state.get("pending") if row else None
    if not pending or pending["id"] != payload.proposal_id:
        raise HTTPException(409, "This proposal is no longer pending")
    result = materialize(solution, pending, db, user)
    before = content(solution)
    try:
        solution = update(solution_id, SolutionUpdate(expected_updated_at=payload.expected_updated_at, **result), db, user, commit=False)
        state = deepcopy(row.state); state["pending"] = None
        state["last_applied"] = {"id": pending["id"], "before": before, "updated_at": solution.updated_at.isoformat(), "sha256": digest(content(solution))}
        row.state = state; row.revision += 1
        db.commit(); db.refresh(solution); db.refresh(row)
        return view(solution, row, db, user)
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
        return view(solution, row, db, user)
    except Exception:
        db.rollback(); raise
