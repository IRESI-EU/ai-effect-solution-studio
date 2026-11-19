"""Normal authorised saved-solution conversation; no execution tools."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.schemas.solution_assistant import SolutionChatRequest, SolutionProposalRequest, SolutionRevisionRequest
from app.services import solution_assistant as service
from app.services.design_ai_provider import Provider, get_provider, redact_context
from app.services.solution_editing import owned_solution

router = APIRouter(prefix="/design-ai/solutions", tags=["saved-solution-assistant"])


def workspace_user(request: Request, user: User = Depends(get_current_user)):
    if not settings.design_ai_enabled: raise HTTPException(404, "Design with AI is not enabled")
    if user.status != "active" or user.role not in {"solution_designer", "node_manager", "platform_admin"}:
        raise HTTPException(403, "An active design account is required")
    if settings.design_ai_restricted_beta or settings.design_ai_local_pilot:
        raise HTTPException(403, "This retained experimental profile does not enable the normal saved-solution assistant")
    if request.method not in {"GET", "HEAD"} and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site design requests are not allowed")
    return user


@router.get("/{solution_id}")
def read(solution_id: str, db: Session = Depends(get_db), user: User = Depends(workspace_user)):
    solution = owned_solution(solution_id, db, user)
    return service.view(solution, service.conversation(solution, db, user))


@router.post("/{solution_id}/chat")
async def chat(solution_id: str, payload: SolutionChatRequest, request: Request, db: Session = Depends(get_db),
               user: User = Depends(workspace_user), provider: Provider = Depends(get_provider)):
    solution = owned_solution(solution_id, db, user)
    row = service.conversation(solution, db, user, create=True)
    service.check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    base_sha = service.digest(service.content(solution))
    context = redact_context(service.context(solution, row, payload.message, db, user))
    if settings.design_ai_scoped_acceptance_file:
        from app.services.scoped_ai_acceptance import binding
        context['_acceptance_binding']=binding(settings,user.id,solution.id)
    identifier = row.id
    # No transaction or row lock is held across a provider request.
    db.rollback()
    try:
        from app.services.provider_evidence import correlation
        with correlation(conversation_id=identifier, draft_id=None, revision=payload.conversation_revision):
            async with asyncio.timeout(min(max(settings.design_ai_timeout_seconds, 1), 90) + 2):
                turn = AssistantTurn.model_validate(await provider.respond(context))
    except TimeoutError as exc:
        raise HTTPException(504, {"code": "assistant_timeout", "stage": "provider_call", "message": "AI response timed out. Your saved solution and pending proposal are unchanged."}) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(502, {"code": "assistant_response_invalid", "stage": "response_validation", "message": "AI returned an invalid response. Your saved solution and pending proposal are unchanged."}) from exc
    db.rollback()
    if await request.is_disconnected(): raise HTTPException(499, "Request cancelled; no proposal was stored")
    workspace_user(request, user)
    solution = owned_solution(solution_id, db, user, lock=True)
    row = service.conversation(solution, db, user, lock=True)
    service.check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    if service.digest(service.content(solution)) != base_sha:
        raise HTTPException(409, "Builder changed the design while AI was responding. Request a new proposal.")
    try:
        return service.propose(solution, row, payload.message, turn, db, user, catalogue_used=context['catalogue'])
    except HTTPException as exc:
        if exc.status_code in {409, 422, 502}:
            db.rollback()
            if settings.design_ai_scoped_acceptance_file:
                from app.services.scoped_ai_acceptance import Budget
                Budget(settings.design_ai_scoped_acceptance_file).close()
            detail = exc.detail if isinstance(exc.detail, str) else "The proposed edit is incompatible"
            raise HTTPException(exc.status_code, {"code": "assistant_edit_rejected", "stage": "application_validation",
                "message": detail + ". The saved solution and previous pending proposal are unchanged."}) from exc
        raise


@router.post("/{solution_id}/apply")
def apply(solution_id: str, payload: SolutionProposalRequest, db: Session = Depends(get_db), user: User = Depends(workspace_user)):
    return service.apply(solution_id, payload, db, user)


@router.post("/{solution_id}/undo")
def undo(solution_id: str, payload: SolutionRevisionRequest, db: Session = Depends(get_db), user: User = Depends(workspace_user)):
    return service.undo(solution_id, payload, db, user)


@router.post("/{solution_id}/dismiss")
def dismiss(solution_id: str, payload: SolutionProposalRequest, db: Session = Depends(get_db), user: User = Depends(workspace_user)):
    from copy import deepcopy
    solution = owned_solution(solution_id, db, user, lock=True)
    row = service.conversation(solution, db, user, lock=True)
    service.check(solution, row, payload.expected_updated_at, payload.conversation_revision)
    if not row or not row.state.get("pending") or row.state["pending"]["id"] != payload.proposal_id:
        raise HTTPException(409, "This proposal is no longer pending")
    state = deepcopy(row.state); state["pending"] = None
    row.state = state; row.revision += 1
    db.commit(); db.refresh(row)
    return service.view(solution, row)
