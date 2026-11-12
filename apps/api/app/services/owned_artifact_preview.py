"""Generic previews require deployment, task-output and file-namespace authority.

Legacy references with no provable association remain unavailable. Never infer
ownership from a caller-supplied path or fetch an arbitrary remote URI.
"""
from fastapi import HTTPException

from app.routers.deployment_results import authorized_deployment
from app.services.orchestrator_adapter import get_workflow_tasks
from app.services.data_reference_service import preview_data_reference, resolve_artifact_path
from app.models.execution_submission import ExecutionSubmission
from app.services.execution_submission import view as submitted_view


def references(value):
    if isinstance(value, dict):
        if isinstance(value.get("protocol"), str) and isinstance(value.get("uri"), str):
            yield value["protocol"], value["uri"]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def preview(payload, db, user):
    deployment = authorized_deployment(db, user, payload.workflow_id)
    if not deployment.created_by_user_id:
        raise HTTPException(409, "Legacy deployment ownership is not recorded; preview is unavailable")
    submission = db.query(ExecutionSubmission).filter(ExecutionSubmission.workflow_id == payload.workflow_id).first()
    if (submission is None or submission.phase != "submitted"
            or submission.owner_user_id != deployment.created_by_user_id
            or submission.solution_id != deployment.solution_id):
        raise HTTPException(409, "Server-recorded submission association is unavailable; legacy preview stays blocked")
    submitted_view(submission)
    observed = get_workflow_tasks(payload.workflow_id)
    if not isinstance(observed, dict) or observed.get("workflow_id") != payload.workflow_id:
        raise HTTPException(409, "Workflow task association could not be verified")
    tasks = observed.get("tasks")
    if not isinstance(tasks, list):
        raise HTTPException(409, "Workflow task evidence is unavailable")
    matches = [task for task in tasks if isinstance(task, dict) and task.get("task_id") == payload.task_id]
    if len(matches) != 1:
        raise HTTPException(404, "Task is not recorded for this workflow")
    # Only server-observed outputs confer authority; inputs/metadata do not.
    outputs = list(references(matches[0].get("result")))
    if payload.protocol not in {"file", "inline"}:
        raise HTTPException(409, "Remote preview transport has no qualified ownership boundary")
    requested = (payload.protocol, payload.uri)
    if payload.protocol == "inline":
        if requested not in outputs:
            raise HTTPException(403, "Reference is not an output of this task")
    else:
        path = resolve_artifact_path(payload.uri)
        # Validate resolved paths, including symlinks. Shared or legacy paths
        # without a workflow namespace are deliberately not assigned an owner.
        if path is None or payload.workflow_id not in path.parts:
            raise HTTPException(409, "Artifact workflow namespace could not be verified")
        associated = requested in outputs
        if not associated:
            for protocol, uri in outputs:
                if protocol != "file":
                    continue
                parent = resolve_artifact_path(uri)
                if (parent is not None and parent.is_dir() and payload.workflow_id in parent.parts
                        and path.is_relative_to(parent)):
                    associated = True
                    break
        if not associated:
            raise HTTPException(403, "Reference is not an output of this task")
    return preview_data_reference(payload.protocol, payload.uri, payload.task_id)
