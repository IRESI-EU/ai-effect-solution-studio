import asyncio
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.design_ai import ApplyRequest, AssistantTurn, ChatRequest, GuidedSettingsRequest, RevisionRequest, StartRequest
from app.services import design_ai as service
from app.services.design_ai_mcp import connection
from app.services.design_ai_provider import Provider, configured, get_provider, redact_context


router = APIRouter(prefix="/design-ai", tags=["design-ai"])


def pilot_user(request: Request, user: User = Depends(get_current_user)):
    service.enabled()
    if user.status != "active" or user.role not in {"solution_designer", "node_manager", "platform_admin"}:
        raise HTTPException(403, "Active design account required")
    # Cookie-authenticated writes must originate from this application (works behind Next's rewrite).
    if request.method not in {"GET", "HEAD"} and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site design requests are not allowed")
    return user


@router.get("/config")
def configuration(provider: Provider = Depends(get_provider)):
    result = {"enabled": settings.design_ai_enabled, "provider_configured": settings.design_ai_enabled and configured()}
    if settings.design_ai_enabled:
        result.update(provider_name=getattr(provider, "name", "Test provider"),
                      provider_mode=getattr(provider, "mode", "test"), model=settings.design_ai_model or None)
        if settings.design_ai_acceptance_budget_file:
            from app.services.design_ai_budget import Budget
            try:
                result["test_allowance"] = Budget(settings.design_ai_acceptance_budget_file, task_limit_file=settings.design_ai_acceptance_task_limit_file).availability()
            except (HTTPException, OSError, sqlite3.Error):
                result["test_allowance"] = {"can_request": False, "blocked_reason": "unavailable",
                    "message": "AI testing is paused because the local test allowance cannot be read. Ask the local operator to check its configuration."}
    return result


@router.get("/templates")
def templates(db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.list_templates(db, user)


@router.post("/drafts")
def start(payload: StartRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.start(payload.template_key, db, user, guided=payload.guided)


@router.get("/drafts")
def drafts(db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.list_drafts(db, user)


@router.post("/drafts/{draft_id}/guided-settings")
def guided_settings(draft_id: str, payload: GuidedSettingsRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.guided_settings(draft_id, payload.revision, payload.seed, db, user)


@router.get("/drafts/{draft_id}")
def read(draft_id: str, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    row = service.load_draft(draft_id, db, user)
    result = service.view(row)
    result["validation"] = service.validate(row.state["design"], db, user)
    if service.policy_scope(row.state["design"]):
        from app.services.instance_proposals import settings_context
        result["instance_settings"] = settings_context(row, db)["instances"]
    return result


@router.post("/drafts/{draft_id}/apply")
def apply(draft_id: str, payload: ApplyRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.apply(draft_id, payload.revision, payload.proposal_id, db, user)


@router.post("/drafts/{draft_id}/undo")
def undo(draft_id: str, payload: RevisionRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    return service.undo(draft_id, payload.revision, db, user)


@router.post("/drafts/{draft_id}/save")
async def save(draft_id: str, payload: RevisionRequest, db: Session = Depends(get_db), user: User = Depends(pilot_user)):
    async with connection(db, user, draft_id=draft_id, explicit_save=True) as tools:
        result = await tools.call("save_draft", {"revision": payload.revision})
        return {"draft": result, "activity": tools.activity}


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(pilot_user), provider: Provider = Depends(get_provider)):
    context = {"request": payload.message, "history": []}
    base_revision = None
    for item in payload.history:
        if set(item) != {"role", "content"} or item["role"] not in {"user", "assistant"} or len(item["content"]) > 5000:
            raise HTTPException(422, "Conversation history is invalid")
        context["history"].append(item)
    if sum(len(item["content"]) for item in context["history"]) > 16000:
        raise HTTPException(422, "Conversation history is too large. Start a new conversation.")
    async with connection(db, user, draft_id=payload.draft_id) as tools:
        await tools.discover()
        current = service.load_draft(payload.draft_id, db, user) if payload.draft_id else None
        focused = current is not None and service.policy_scope(current.state["design"])
        if not focused:
            context["templates"] = (await tools.call("list_pilot_templates", {}))["templates"]
        discovery = None
        if not payload.draft_id:
            # Discovery is scoped by authenticated MCP catalogue reads, not model choice.
            context["templates"] = [t for t in context["templates"] if t["key"] == "dutch" and t.get("available") and t.get("guided_available")]
            if context["templates"]:
                context["template"] = await tools.call("read_template", {"template_key": "dutch"})
                context["configuration"] = await tools.call("inspect_supported_configuration", {"template_key": "dutch"})
                discovery = await tools.call("discover_guided_capability", {"template_key": "dutch"})
                context["guided_experiment"] = discovery
            context["discovery"] = {"draft_exists": False, "creation": "Recommendation only. A separate copy requires explicit Create this experiment.",
                "supported_scope": "Only the enabled approved local Dutch sample-grid experiment. Explain unsupported requests honestly; no datasets, forecasting, model replacement or execution."}
        if payload.draft_id:
            row = service.load_draft(payload.draft_id, db, user)
            service.check_revision(row, payload.revision)
            # This server-read revision, never an LLM-supplied value, binds
            # proposals to the exact draft supplied as provider context.
            base_revision = row.revision
            key = row.state["template_key"]
            if not focused:
                context["template"] = await tools.call("read_template", {"template_key": key})
            context["configuration"] = await tools.call("inspect_supported_configuration", {"template_key": key})
            design = row.state["design"]
            guided = service.guided_context(row)
            if guided is not None:
                context["guided_experiment"] = guided
            context["draft"] = {"revision": row.revision, "name": design["name"], "description": design["description"],
                "run_input": design["run_input"], "labels": [{"node_id": n["id"], "label": n.get("data", {}).get("label")} for n in design["nodes"]],
                "validation": service.validate(design, db, user)}
            if focused:
                # No template payload, workflow input, artifacts, runtime endpoints
                # or unrelated catalogue data enter this focused provider context.
                context["draft"] = {"revision": row.revision, "editing_scope": "instance_settings"}
                context["history"] = []  # Each edit is grounded in the current authorized instance projection.
        context = redact_context(context)
        try:
            async with asyncio.timeout(min(max(settings.design_ai_timeout_seconds, 1), 90) + 2):
                turn = AssistantTurn.model_validate(await provider.respond(context))
        except TimeoutError as exc:
            raise HTTPException(504, "The AI provider timed out. Your draft is unchanged; retry when ready.") from exc
        except (ValidationError, ValueError) as exc:
            raise HTTPException(502, "The AI provider returned an invalid proposal. Your draft is unchanged.") from exc
        # End read transactions and re-read state after awaiting an external provider.
        db.rollback()
        service.enabled()
        if await request.is_disconnected():
            raise HTTPException(499, "Request cancelled; no proposal was stored")
        result = {"message": turn.message, "recommendation": None, "draft": None}
        if not payload.draft_id:
            if turn.edits:
                raise HTTPException(422, "Create an editable draft before proposing changes")
            if turn.template_key:
                if discovery is None or turn.template_key != discovery["key"]:
                    raise HTTPException(422, "The recommendation is outside the enabled approved local capabilities. No experiment was created.")
                # Re-check eligibility after the provider wait, without trusting its service claims.
                result["recommendation"] = await tools.call("discover_guided_capability", {"template_key": turn.template_key})
        else:
            row = service.load_draft(payload.draft_id, db, user)
            if turn.edits:
                service.check_revision(row, base_revision)
                if focused and turn.expected_revision != base_revision:
                    raise HTTPException(409, "The proposal revision does not match the reviewed instance settings. Request a new proposal.")
                turn = turn.model_copy(update={"expected_revision": base_revision})
                await tools.call("validate_draft", {"proposal": turn.model_dump()})
                # propose takes a refreshed SELECT FOR UPDATE and checks the
                # bound revision again; Apply retains its own locked check.
                result["draft"] = service.propose(payload.draft_id, turn, db, user)
            else:
                # Explanations/refusals cannot mutate draft or proposal state.
                # A model revision is irrelevant; disclose a newer real draft.
                result.update(context_revision=base_revision, current_revision=row.revision)
                if row.revision != base_revision:
                    result["message"] = f"This response describes draft revision {base_revision}; the current draft is revision {row.revision}.\n\n" + turn.message
        result["activity"] = tools.activity
        return result
