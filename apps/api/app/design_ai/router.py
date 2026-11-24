from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.dependencies.auth import get_current_user
from app.design_ai.catalogue import build_catalogue
from app.design_ai.composer import compose
from app.design_ai.providers import ModelError, get_model
from app.design_ai.usage import DesignAIUsage, requests_last_24h
from app.models.user import User

router = APIRouter(tags=["design-ai"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ComposeRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    current: dict | None = None  # current canvas: {"steps": [...], "connections": [...]}


@router.get("/design-ai/status")
def design_ai_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    used = requests_last_24h(db, user.id)
    return {
        "enabled": settings.design_ai_enabled,
        "provider": settings.design_ai_provider,
        "model": get_model().model,
        "daily_limit": settings.design_ai_daily_requests_per_user,
        "used_last_24h": used,
    }


@router.post("/design-ai/compose")
def design_ai_compose(payload: ComposeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not settings.design_ai_enabled:
        raise HTTPException(status_code=503, detail="Design with AI is switched off on this platform.")
    if not payload.messages or payload.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must come from the user.")
    if requests_last_24h(db, user.id) >= settings.design_ai_daily_requests_per_user:
        raise HTTPException(status_code=429, detail="You have reached today's Design with AI limit. Please try again tomorrow.")

    model = get_model()
    cards = build_catalogue(db)
    try:
        result = compose(model, cards, [m.model_dump() for m in payload.messages], payload.current)
    except ModelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db.add(DesignAIUsage(
        user_id=user.id, provider=model.name, model=model.model, attempts=result.attempts,
        prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens, valid=not result.errors,
    ))
    db.commit()

    return {
        "reply": result.reply,
        "clarifying_question": result.clarifying_question,
        "workflow": result.workflow,
        "valid": not result.errors and result.workflow is not None,
        "errors": result.errors,
        "attempts": result.attempts,
        "provider": model.name,
        "model": model.model,
    }
