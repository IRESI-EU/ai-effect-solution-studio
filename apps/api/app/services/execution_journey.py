"""Durable review/attempt identity for the bounded Dutch demonstration.

The database claim prevents redispatch of this attempt. A lost runtime response
is explicitly uncertain, not retryable and not a distributed exactly-once claim.
"""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings
from app.models.execution_submission import ExecutionSubmission
from app.models.solution import Solution
from app.services import design_ai, execution_submission, qualified_demo


def public(row):
    execution_submission.view(row)
    return {"submission_id": row.id, "phase": row.phase, "workflow_id": row.workflow_id,
        "results_url": f"/deployments/{row.workflow_id}#results" if row.workflow_id else None,
        "submitted_sha256": row.submitted_sha256}


def load_attempt(identifier, db, user, *, lock=False):
    query = db.query(ExecutionSubmission).filter(ExecutionSubmission.id == identifier,
        ExecutionSubmission.owner_user_id == user.id)
    if lock:
        query = query.with_for_update().populate_existing()
    row = query.first()
    if not row:
        raise HTTPException(404, "Execution attempt not found")
    execution_submission.view(row)
    return row


def saved_draft(draft_id, revision, db, user):
    row = design_ai.load_draft(draft_id, db, user, lock=True)
    design_ai.check_revision(row, revision)
    if row.state.get("guided_experiment") != "qualified_dutch_grid" or not qualified_demo.profile_enabled():
        raise HTTPException(422, "This execution journey requires the qualified registered Dutch experiment")
    if row.state["dirty"] or row.state.get("pending") or not row.state.get("saved_solution_id"):
        raise HTTPException(409, "Apply and Save the reviewed design before preparing execution")
    solution = db.query(Solution).filter(Solution.id == row.state["saved_solution_id"]).with_for_update().populate_existing().first()
    if (not solution or solution.created_by_user_id != user.id or solution.status != "draft"
        or design_ai.digest(design_ai.content(solution)) != row.state.get("saved_fingerprint")):
        raise HTTPException(409, "The saved solution changed. Reload and review before execution")
    design = {"name": solution.name, "nodes": solution.nodes, "edges": solution.edges,
        "run_input": (solution.design_metadata or {}).get("run_input")}
    qualified_demo.inspect(design, db, user)
    return row, qualified_demo.workflow_payload(design, solution)


def authorization(db, user, seed):
    """Read an attributable one-attempt grant; never create or amend one."""
    if not settings.design_ai_demo_execution_grant_file:
        return None
    try:
        grant = json.loads(Path(settings.design_ai_demo_execution_grant_file).read_text())
        required = {"id", "profile", "owner_id", "seed", "source_solution_id", "max_attempts", "approved_by", "approved_at"}
        if (set(grant) != required or grant["profile"] != "qualified-dutch-goal-to-results"
            or grant["owner_id"] != user.id or type(grant["seed"]) is not int or grant["seed"] != seed
            or type(grant["max_attempts"]) is not int or grant["max_attempts"] != 1
            or grant["source_solution_id"] != design_ai.policies()["dutch"].solution_id
            or not all(isinstance(grant[key], str) and 0 < len(grant[key]) < 256 for key in ["id", "approved_by", "approved_at"])):
            raise ValueError()
        datetime.fromisoformat(grant["approved_at"])
        return grant
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(403, "The separately authorized local execution grant is absent or invalid; no execution is permitted") from None


def seed(workflow):
    return next(node.configuration["parameters"].get("seed", 42) for node in workflow.nodes
        if node.operation_name == "ConfigureAndSynthesize")


def claim(row, workflow, compiled, db, user):
    if (row.submitted["request"] != execution_submission.request_value(workflow)
        or row.submitted["compiled"] != compiled or row.submitted["runtime_destination"] != settings.orchestrator_base_url):
        raise HTTPException(409, "The saved design, contracts or runtime changed since review. Review readiness again")
    grant = authorization(db, user, seed(workflow))
    if not grant or row.submitted.get("authorization") != grant:
        raise HTTPException(403, "Explicit operator authorization for one local execution is required; no workflow was submitted")
    # Serialize this grant across different saved solutions, without altering the
    # original exhausted AIE-37 one-run guard or the provider allowance.
    source = db.query(Solution).filter(Solution.id == grant["source_solution_id"]).with_for_update().populate_existing().first()
    if not source:
        raise HTTPException(409, "The registered source workflow is unavailable")
    attempts = db.query(ExecutionSubmission).filter(ExecutionSubmission.phase.in_(
        ["dispatching", "submitted", "submission_unknown", "submission_failed"])).all()
    if any((attempt.submitted.get("authorization") or {}).get("id") == grant["id"] for attempt in attempts):
        raise HTTPException(409, "The one local execution permission is consumed. Preserve its outcome; do not retry")
    row.phase = "dispatching"
    db.commit()  # Claim is durable BEFORE any possible runtime submission.


def prepare(draft_id, revision, db, user):
    from app import main
    row, workflow = saved_draft(draft_id, revision, db, user)
    preflight = main.run_runtime_preflight(workflow.nodes, db)
    if preflight["status"] != "ready":
        return {"design": "saved", "readiness": preflight, "attempt": None, "execution_authorized": False}
    compiled = main.compile_to_wp3_payload(workflow, db)
    from app.services.capability_readiness import require_binding_transport
    from app.services.orchestrator_adapter import require_parameter_transport
    compiled["solution_studio_metadata"]["connection_compatibility"] = require_binding_transport(compiled)
    compiled["solution_studio_metadata"]["parameter_compatibility"] = require_parameter_transport(compiled)
    grant = authorization(db, user, seed(workflow))
    old = db.query(ExecutionSubmission).filter(ExecutionSubmission.owner_user_id == user.id,
        ExecutionSubmission.solution_id == workflow.solution_id).order_by(ExecutionSubmission.created_at.desc()).first()
    if old and old.phase != "reviewed":
        return {"design": "saved", "readiness": preflight, "attempt": public(old), "execution_authorized": False}
    if not old or old.submitted != {"request": execution_submission.request_value(workflow), "compiled": compiled,
        "runtime_destination": settings.orchestrator_base_url, "authorization": grant or {}}:
        old = execution_submission.prepare(db, user, workflow, compiled, phase="reviewed", authorization=grant or {})
    return {"design": "saved", "seed": seed(workflow), "readiness": preflight, "attempt": public(old), "execution_authorized": bool(grant)}


def latest(draft_id, db, user):
    row = design_ai.load_draft(draft_id, db, user)
    if not row.state.get("saved_solution_id"):
        return None
    attempt = db.query(ExecutionSubmission).filter(ExecutionSubmission.owner_user_id == user.id,
        ExecutionSubmission.solution_id == row.state["saved_solution_id"]).order_by(ExecutionSubmission.created_at.desc()).first()
    return public(attempt) if attempt else None
