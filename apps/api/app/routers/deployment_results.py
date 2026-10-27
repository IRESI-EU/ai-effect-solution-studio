"""Ownership checks precede all orchestrator and capture reads."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import can_manage_owned_record, get_current_user
from app.models.deployment import Deployment
from app.models.user import User
from app.schemas.deployment import DeploymentRead
from app.services import local_dutch_evidence as evidence
from app.services import local_dutch_capture as automatic
from app.services.orchestrator_adapter import get_workflow_status, get_workflow_tasks

router = APIRouter()


def authorized_deployment(db, user, workflow_id):
    deployment = db.query(Deployment).filter(Deployment.workflow_id == workflow_id).first()
    if deployment is None:
        raise HTTPException(404, "Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(403, "You can only access your own deployments")
    return deployment


def current_state(deployment):
    try:
        workflow = get_workflow_status(deployment.workflow_id)
        tasks = get_workflow_tasks(deployment.workflow_id)["tasks"]
        return workflow, tasks, True
    except (HTTPException, KeyError):
        return {"workflow_id": deployment.workflow_id, "status": deployment.status}, [], False


def load_evidence(db, deployment, workflow, tasks, live):
    captured = automatic.collect(db, deployment, workflow, tasks)
    if captured is not None:
        return captured
    return evidence.load_capture(deployment, workflow if live else None, tasks if live else None)


@router.get("/deployments/by-workflow/{workflow_id}/results")
def deployment_results(workflow_id: str, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, no-store"
    deployment = authorized_deployment(db, user, workflow_id)
    workflow, tasks, live = current_state(deployment)
    captured, _ = load_evidence(db, deployment, workflow, tasks, live)
    if captured["state"] == "available":
        tasks = captured.pop("tasks", tasks)
    return {"deployment": DeploymentRead.model_validate(deployment), "workflow": workflow,
            "status_source": "orchestrator" if live else "stored deployment record; orchestrator unavailable",
            "tasks": tasks, "evidence": captured}


@router.get("/deployments/by-workflow/{workflow_id}/artifacts/{artifact_id}")
def deployment_artifact(workflow_id: str, artifact_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deployment = authorized_deployment(db, user, workflow_id)
    if artifact_id not in {"configuration", "grid", "network", "benchmark"}:
        raise HTTPException(404, "Artifact not recorded")
    workflow, tasks, live = current_state(deployment)
    captured, blobs = load_evidence(db, deployment, workflow, tasks, live)
    if artifact_id not in blobs:
        state = next((a["state"] for a in captured["artifacts"] if a["id"] == artifact_id), None)
        raise HTTPException(404 if state == "not_recorded" or captured["state"] == "unavailable" else 410,
                            "No artifact recorded" if state == "not_recorded" else "Artifact unavailable or association not validated")
    return Response(blobs[artifact_id], media_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{workflow_id}-{evidence.FILES[artifact_id][0]}"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
        "Content-Security-Policy": "sandbox; default-src 'none'",
    })
