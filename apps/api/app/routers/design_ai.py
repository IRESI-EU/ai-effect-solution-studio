import asyncio
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.dependencies.auth import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.design_ai import ApplyRequest, AssistantTurn, ChatRequest, GuidedSettingsRequest, RevisionRequest, StartRequest
from app.services import design_ai as service
from app.services.design_ai_mcp import connection
from app.services.design_ai_provider import Provider, configured, get_provider, redact_context


router = APIRouter(prefix="/design-ai", tags=["design-ai"])


def require_reviewer(user):
    if settings.design_ai_local_pilot:
        from app.services.qualified_demo import profile_enabled
        from app.services.allowance_client import requested
        reviewers = {value.strip() for value in settings.design_ai_reviewer_ids.split(",") if value.strip()}
        if not settings.design_ai_restricted_beta or len(reviewers) != 1 or not profile_enabled() or not requested(settings):
            raise HTTPException(503, "Local pilot requires its qualified profile, one existing reviewer and exclusive shared accounting")
    if settings.design_ai_restricted_beta:
        allowed = {value.strip() for value in settings.design_ai_reviewer_ids.split(",") if value.strip()}
        if (not user or user.status != "active" or user.id not in allowed
                or user.role not in {"solution_designer", "node_manager", "platform_admin"}):
            raise HTTPException(403, "Design with AI is restricted to approved reviewers")


def pilot_user(request: Request, user: User = Depends(get_current_user)):
    service.enabled()
    require_reviewer(user)
    if user.status != "active" or user.role not in {"solution_designer", "node_manager", "platform_admin"}:
        raise HTTPException(403, "Active design account required")
    # Cookie-authenticated writes must originate from this application (works behind Next's rewrite).
    if request.method not in {"GET", "HEAD"} and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site design requests are not allowed")
    return user


@router.get("/config")
def configuration(provider: Provider = Depends(get_provider), user: User | None = Depends(get_optional_user)):
    require_reviewer(user)
    result = {"enabled": settings.design_ai_enabled, "provider_configured": settings.design_ai_enabled and configured()}
    if settings.design_ai_local_pilot:
        result["pilot_notice"] = "Restricted local design-only pilot · Supervised use through one existing reviewer account. Saving does not execute a workflow."
    if settings.design_ai_enabled:
        result.update(provider_name=getattr(provider, "name", "Test provider"),
                      provider_mode=getattr(provider, "mode", "test"), model=settings.design_ai_model or None)
        from app.services.allowance_client import Client, requested
        if requested(settings):
            try:result["test_allowance"]=Client(settings).availability()
            except HTTPException:
                result["test_allowance"]={"can_request":False,"blocked_reason":"accounting_unavailable",
                    "message":"AI messages paused: shared accounting is unavailable. Do not retry or use a local allowance."}
        elif settings.design_ai_acceptance_budget_file:
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
    if payload.candidate_id:
        from app.services.catalogue_discovery import create
        return create(payload, db, user)
    if payload.composition_settings is not None or payload.creation_request_id is not None:
        raise HTTPException(422, "Pair creation settings cannot be attached to a legacy template")
    if payload.template_key not in service.PILOTS:
        raise HTTPException(422, "Unknown legacy template selector; use an advertised registered recommendation")
    return service.start(payload.template_key, db, user, guided=payload.guided,
        recommended_seed=payload.recommended_seed, recommendation_revision=payload.recommendation_revision)


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
    if payload.clarification:
        context["pending_clarification"] = payload.clarification.model_dump()
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
        focused = current is not None and (service.policy_scope(current.state["design"]) or current.state["design"].get("editing_scope") in {"append_bound_operation", "catalogue_pair"})
        if payload.draft_id and not focused:
            context["templates"] = (await tools.call("list_pilot_templates", {}))["templates"]
        discovery = None
        if not payload.draft_id:
            discovery = await tools.call("discover_catalogue_capabilities", {})
            context["catalogue_discovery"] = discovery
            context["discovery"] = {"draft_exists": False, "creation": "Recommendation only. A separate copy requires explicit Create this experiment.",
                "supported_scope": "Use only advertised candidate identifiers. Catalogue-only services cannot create workflows; advertised pairs create design-only two-operation drafts. Ask for missing objectives, data sources or ambiguous targets. Runtime and data availability have not been checked."}
        if payload.draft_id:
            row = service.load_draft(payload.draft_id, db, user)
            service.check_revision(row, payload.revision)
            # This server-read revision, never an LLM-supplied value, binds
            # proposals to the exact draft supplied as provider context.
            base_revision = row.revision
            if row.state.get("source", {}).get("kind") == "catalogue_composed":
                context["configuration"] = await tools.call("inspect_catalogue_composition", {})
                context["draft"] = {"revision": row.revision, "editing_scope": "catalogue_pair", "source_kind": "catalogue_composed"}
            else:
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
                    if design.get("editing_scope") == "append_bound_operation":
                        context["draft"] = {"id": row.id, "revision": row.revision, "editing_scope": "append_bound_operation"}
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
        result = {"message": turn.message, "recommendation": None, "draft": None,
                  "clarification": payload.clarification.model_dump() if payload.clarification else None}
        if not payload.draft_id:
            if turn.discovery is not None:
                from app.services.catalogue_discovery import selected
                result["recommendation"] = selected(turn, discovery, db, user)
                result["outcome"] = turn.discovery.outcome
                result["question"] = turn.discovery.question
                # Selection/question comes from the provider. Capability claims and
                # creation authority come from validated server facts, not free prose.
                if turn.discovery.outcome == "clarification_needed":
                    question = turn.discovery.question.strip()
                    # Preserve the explanation and append the structured question once.
                    if question not in turn.message:
                        result["message"] = turn.message.rstrip() + "\n\n" + question
                    result["clarification"] = {"request": payload.clarification.request if payload.clarification else payload.message,
                                               "question": question}
                elif turn.discovery.outcome != "answer_only":
                    result["clarification"] = None
                if turn.discovery.outcome == "no_supported_match":
                    # No-match prose has no grounded selection to support capability
                    # claims. Keep the honest server limitation; explanations have
                    # their own answer-only outcome without creation authority.
                    result["message"] = "No supported catalogue match was found for this request. No design was created or changed."
                result["activity"] = tools.activity
                return result
            if turn.composition_settings is not None:
                raise HTTPException(422, "Pair settings require a structured catalogue-pair recommendation")
            if turn.edits:
                result["clarification"] = None
                raise HTTPException(422, "Create an editable draft before proposing changes")
            if turn.template_key:
                # Compatibility for existing clients/providers; the new discovery prompt
                # selects opaque advertised candidates instead of country/template keys.
                if turn.template_key not in {item["key"] for item in discovery["legacy_templates"]}:
                    raise HTTPException(422, "The recommendation was not advertised. No experiment was created.")
                try:
                    result["recommendation"] = await tools.call("discover_guided_capability", {"template_key": turn.template_key})
                except HTTPException as exc:
                    raise HTTPException(422, "The recommendation is outside the supported registered paths. No experiment was created.") from exc
                if result["recommendation"].get("mechanism") == "registered_workflow":
                    if turn.recommended_seed not in result["recommendation"]["supported_seeds"]:
                        raise HTTPException(422, "The recommendation needs a supported seed. No experiment was created.")
                    result["recommendation"]["recommended_seed"] = turn.recommended_seed
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
