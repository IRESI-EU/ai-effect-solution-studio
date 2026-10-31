"""Explicit review/confirm controls; no model can invoke execution tools."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.routers.design_ai import pilot_user
from app.schemas.design_ai import RevisionRequest, StrictModel
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import design_ai, execution_journey as journey, qualified_demo

router = APIRouter(prefix="/design-ai/drafts", tags=["experiment journey"])


class ConfirmExecution(RevisionRequest):
    submission_id: str
    confirm_execution: bool


@router.get("/{draft_id}/execution")
def execution(draft_id: str, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return {"attempt": journey.latest(draft_id, db, user)}


@router.post("/{draft_id}/execution-review")
def review(draft_id: str, payload: RevisionRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return journey.prepare(draft_id, payload.revision, db, user)


@router.post("/{draft_id}/execute")
def execute(draft_id: str, payload: ConfirmExecution, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    from app import main
    if not qualified_demo.profile_enabled():
        raise HTTPException(403, "Execution is unavailable in this profile")
    if not payload.confirm_execution:
        raise HTTPException(422, "Explicit execution confirmation is required")
    draft = design_ai.load_draft(draft_id, db, user, lock=True)
    attempt = journey.load_attempt(payload.submission_id, db, user, lock=True)
    if attempt.solution_id != draft.state.get("saved_solution_id"):
        raise HTTPException(404, "Execution attempt does not belong to this saved experiment")
    if attempt.phase == "reviewed":
        journey.saved_draft(draft_id, payload.revision, db, user)
    workflow = WorkflowSubmitRequest.model_validate(attempt.submitted["request"]).model_copy(update={"submission_id": attempt.id})
    result = main.submit_workflow_to_orchestrator_endpoint(workflow, db, user)
    return {"attempt": journey.public(attempt), "workflow": result}
