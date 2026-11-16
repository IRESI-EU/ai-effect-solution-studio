"""Disabled-by-default admission for one frozen Portuguese sandbox request.

Reuses ExecutionSubmission, existing journal authorization and the one-shot WP3
worker. A dispatching/unknown attempt is never dispatched again. No new grants.
"""
import hashlib
import json
import re
from uuid import uuid4
import requests
from fastapi import HTTPException
from app.core.config import settings
from app.models.user import User
from app.models.solution import Solution
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.services import execution_submission


def boundary(action, value):
    # Operator configuration is server-only. Neither URL nor credential comes
    # from a saved design, request body or data reference.
    url = settings.portuguese_supervised_adapter_url
    if (not settings.portuguese_supervised_mode or not settings.portuguese_supervised_authorization_id
        or url != "http://pt-adapter:8080" or not settings.orchestrator_services_api_key):
        raise HTTPException(409, "Supervised authority/processing is not configured; inspection only")
    try:
        with requests.Session() as client:
            client.trust_env = False
            r = client.post(url + "/control/supervised/" + action, json=value,
                headers={"Authorization": "Bearer " + settings.orchestrator_services_api_key}, timeout=5, allow_redirects=False)
        if r.status_code != 200:
            raise ValueError()
        result = r.json()
        request = value["request"] if action == "bind" else value
        if (result.get("status") != ("bound" if action == "bind" else "ready")
            or any(result.get(k) != request[k] for k in ("authorization_id", "owner_id", "request_sha256"))
            or not re.fullmatch(r"[a-f0-9]{64}", result.get("policy_sha256", ""))
            or (action == "bind" and result.get("workflow_id") != value["workflow_id"])):
            raise ValueError()
        return result
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        raise HTTPException(409, "Exact execution authority or waiting targeted processing is unavailable. No automatic retry; inspect any accepted attempt.") from None


def saved(workflow, db, user):
    if user.id != settings.portuguese_evidence_owner_id or user.status != "active":
        raise HTTPException(403, "Only the configured active sandbox reviewer may submit")
    row = db.query(Solution).filter(Solution.id == workflow.solution_id).with_for_update().populate_existing().first()
    if not row or row.created_by_user_id != user.id:
        raise HTTPException(403, "An owned saved sandbox design is required")
    if row.status != "draft" or workflow.expected_updated_at != row.updated_at.isoformat():
        raise HTTPException(409, "Saved design changed; reload before preparing execution")
    nodes = {n["id"]: n["data"] for n in row.nodes if n.get("data", {}).get("service")}
    if len(workflow.nodes) != 2 or set(nodes) != {n.node_id for n in workflow.nodes} or any(
        nodes[n.node_id]["service"]["id"] != n.service_id
        or nodes[n.node_id].get("configuration") != n.configuration
        or nodes[n.node_id].get("operation_contract") != (n.operation_contract.model_dump() if n.operation_contract else None)
        for n in workflow.nodes):
        raise HTTPException(409, "Submitted instances, parameters and pins must match the saved design")
    edges = sorted((e["source"], e["target"], json.dumps((e.get("data") or {}).get("binding"), sort_keys=True)) for e in row.edges if e["source"] in nodes and e["target"] in nodes)
    if edges != sorted((e.source, e.target, json.dumps(e.binding.model_dump() if e.binding else None, sort_keys=True)) for e in workflow.edges):
        raise HTTPException(409, "Submitted binding must match the saved design")
    if ((row.design_metadata or {}).get("run_input") or None) != (workflow.run_input or None):
        raise HTTPException(409, "Training input must match the saved design")
    from app.services.catalogue_composition import require_execution_allowed
    require_execution_allowed(workflow, db, user)


def frozen_request(workflow, compiled, user):
    instances = compiled["solution_studio_metadata"]["execution_instances"]
    if len(instances) != 2 or {n["operation_name"] for n in instances} != {"TrainModel", "GenerateData"}:
        raise HTTPException(409, "Only the published chained TrainModel → GenerateData path is supported")
    train = next(n for n in instances if n["operation_name"] == "TrainModel")
    gen = next(n for n in instances if n["operation_name"] == "GenerateData")
    if (gen["input_bindings"] != [train["instance_id"]] or train["input_bindings"]
        or train["service_id"] != "pt-experimental-chain-TrainModel" or gen["service_id"] != "pt-experimental-chain-GenerateData"):
        raise HTTPException(409, "The exact published chained services and model handoff are required")
    return {"authorization_id": settings.portuguese_supervised_authorization_id, "owner_id": user.id,
        # Same request hash convention as the existing supported journal operator.
        "request_sha256": hashlib.sha256(json.dumps(execution_submission.request_value(workflow), sort_keys=True).encode()).hexdigest(),
        "tasks": {n["task_id"]: {"method": n["operation_name"], "configuration": n["configuration"],
            "inputs": compiled["inputs"] if n is train else "producer:model_ref"} for n in instances},
        "binding": {"producer_task": train["task_id"], "consumer_task": gen["task_id"], "source_slot": "model_ref", "target_slot": "model_ref"}}


def preflight(workflow, db, user):
    from app import main
    saved(workflow, db, user)
    compiled = main.compile_to_wp3_payload(workflow, db)
    frozen = frozen_request(workflow, compiled, user)
    authority = boundary("check", frozen)
    result = main.run_runtime_preflight(workflow.nodes, db)
    if result["status"] != "ready":
        raise HTTPException(409, "Required services are unavailable; no workflow was submitted")
    from app.services.orchestrator_adapter import require_parameter_transport
    main.require_binding_transport(compiled)
    require_parameter_transport(compiled)
    result["design_compatibility"] = compiled["solution_studio_metadata"]["capability_bindings"]
    result["supervised_processing"] = {"status": "ready", "message": "One targeted processor is waiting for this authorized request. No algorithm has been dispatched by this readiness check."}
    return result, compiled, frozen, authority


def submit(workflow, db, user):
    from app import main
    # Serialize across all designs for this one configured reviewer. No schema
    # migration or mutable local grant file substitutes for journal authority.
    db.query(User).filter(User.id == user.id).with_for_update().populate_existing().one()
    saved(workflow, db, user)
    identity = settings.portuguese_supervised_authorization_id
    rows = db.query(ExecutionSubmission).filter(ExecutionSubmission.owner_user_id == user.id).all()
    old = next((r for r in rows if (r.submitted.get("authorization") or {}).get("authorization_id") == identity), None)
    if old:
        execution_submission.view(old)
        if old.submitted["request"] != execution_submission.request_value(workflow):
            raise HTTPException(409, "This authorization already belongs to another immutable request")
        if old.phase == "submitted":
            return {"workflow_id": old.workflow_id, "status": "submitted", "submission_id": old.id,
                    "results_url": f"/deployments/{old.workflow_id}#results", "replayed": True}
        raise HTTPException(409, {"message": "This attempt is consumed or uncertain. Reconcile it; never resubmit.", "submission_id": old.id, "phase": old.phase})
    _, compiled, frozen, authority = preflight(workflow, db, user)
    if boundary("check", frozen) != authority:  # Fresh lease/scope immediately before admission.
        raise HTTPException(409, "Reviewed execution authority changed; no workflow submitted")
    row = execution_submission.prepare(db, user, workflow, compiled, phase="dispatching", authorization=authority)
    try:
        payload = {k: compiled[k] for k in ("blueprint", "dockerinfo", "inputs", "task_configurations") if k in compiled}
        result = main.submit_to_orchestrator(payload)
        wf = result.get("workflow_id")
        if not isinstance(wf, str) or not re.fullmatch(r"wf-[a-f0-9]{12}", wf) or db.query(Deployment).filter(Deployment.workflow_id == wf).first():
            raise ValueError("Invalid or previously recorded workflow identity")
        row.workflow_id = wf
        row.phase = "binding"
        db.add(Deployment(id=str(uuid4()), workflow_id=wf, solution_id=workflow.solution_id,
                         created_by_user_id=user.id, name=workflow.name, status="submitted"))
        db.commit()  # Keep the accepted identity even if processing disappears.
        bound = boundary("bind", {"request": frozen, "workflow_id": wf, "policy_sha256": authority["policy_sha256"]})
        if bound["policy_sha256"] != authority["policy_sha256"]:
            raise ValueError("Authorization changed")
        row.phase = "submitted"
        db.commit()
    except Exception:
        row.phase = "submission_unknown"
        db.commit()
        raise HTTPException(409, {"message": "Submission or processing outcome requires reconciliation. Do not confirm again.",
                                  "submission_id": row.id, "workflow_id": row.workflow_id}) from None
    return {"workflow_id": wf, "status": "submitted", "submission_id": row.id, "results_url": f"/deployments/{wf}#results"}
