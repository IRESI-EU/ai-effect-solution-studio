"""Canonical saved-solution writes shared by manual Builder and assistant review."""
from datetime import datetime

from fastapi import HTTPException

from app.dependencies.auth import can_manage_owned_record
from app.models.solution import Solution
from app.services.audit import record_audit_event
from app.services.instance_configuration import has_configuration, validate_builder_configurations


def owned_solution(solution_id, db, user, *, lock=False):
    query = db.query(Solution).filter(Solution.id == solution_id)
    if lock:
        query = query.with_for_update().populate_existing()
    solution = query.first()
    if solution is None:
        raise HTTPException(404, "Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(403, "You can only access your own solutions")
    return solution


def update(solution_id, payload, db, user, *, commit=True):
    solution = owned_solution(solution_id, db, user, lock=True)
    if solution.status == "archived":
        raise HTTPException(400, "Archived solutions cannot be edited. Restore the solution first.")
    if payload.design_metadata is not None:
        from app.services.catalogue_composition import design_only
        if design_only(solution.design_metadata) and any(
            payload.design_metadata.get(key) != solution.design_metadata.get(key)
            for key in ("source", "execution_policy", "composition_authority", "draft_id")
        ):
            raise HTTPException(409, "Keep the catalogue-composed provenance and design-only execution boundary")
    configured = has_configuration(solution.nodes) or has_configuration(payload.nodes or [])
    if (configured or payload.expected_updated_at is not None) and payload.expected_updated_at != solution.updated_at.isoformat():
        raise HTTPException(409, "This solution changed since it was opened. Reload before saving.")
    validate_builder_configurations(db, payload.nodes if payload.nodes is not None else solution.nodes,
                                    payload.edges if payload.edges is not None else solution.edges, user)
    for key in ("name", "description", "nodes", "edges", "status", "design_metadata"):
        value = getattr(payload, key)
        if value is not None:
            setattr(solution, key, value)
    solution.updated_at = datetime.utcnow()
    record_audit_event(db, user, "solution.updated", "solution", solution.id)
    if commit:
        db.commit()
        db.refresh(solution)
    else:
        db.flush()
    return solution


def require_saved_input(solution, workflow):
    """A configured Run must use the input the designer saved and reviewed."""
    import json
    metadata = solution.design_metadata or {}
    # Legacy designs without a saved input declaration retain their established
    # explicit run-time input path. All new assistant/input edits persist this key.
    if "run_input" in metadata:
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if canonical(metadata["run_input"]) != canonical(workflow.run_input):
            raise HTTPException(409, "Submitted input differs from the saved solution. Save and review the input before running.")
