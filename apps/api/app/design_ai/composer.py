"""Prompt the model, validate its proposal and let it repair mistakes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.design_ai.catalogue import END_TYPE, START_TYPE, ServiceCard, select_cards
from app.design_ai.providers import DesignModel
from app.design_ai.validator import validate_proposal

MAX_ATTEMPTS = 3
MAX_HISTORY_MESSAGES = 12

SYSTEM_PROMPT = f"""You are the Design with AI assistant of the AI-EFFECT platform, a European testing and \
experimentation facility for AI in energy. Research partners ("nodes" in Germany, the Netherlands, Denmark, \
Portugal and others) publish AI services to a catalogue. You help people who are not programmers build a \
workflow from those services.

Rules:
1. Use ONLY services from the CATALOGUE below, referenced by their exact "id". Never invent services.
2. Connect step A to step B only when A.output_type is exactly equal to B.input_type.
3. A workflow starts with a service whose input_type is "{START_TYPE}" and should run through to a service \
whose output_type is "{END_TYPE}" (include the final reporting or formatting step when one exists).
4. Set a setting only when the person's request implies a value (for example "flag only serious anomalies" \
means a higher anomaly threshold). Values must respect the declared type and range. Services marked \
"settings": "fixed" have no adjustable settings; never give them settings. Each setting value is written as \
a JSON string in value_json (for example "3" or "true" or "\\"csv\\"").
5. Be honest about fit. Propose a workflow only if its services actually perform the task that was asked. \
If the catalogue has no service for the core task (for example forecasting, when no service forecasts), set \
workflow to null, say plainly which capability is missing, and use clarifying_question to offer the closest \
available alternative. Never present a service as doing something its purpose does not state. If the request \
is only ambiguous, ask ONE short clarifying question; you may still propose your best workflow.
6. When a CURRENT WORKFLOW is given, the person wants to change it: return the complete updated workflow.
7. reply: 2-4 plain-language sentences for a non-expert, explaining what the workflow does, which node \
provides each step and which settings you chose. Write flowing sentences, not a list; refer to services by \
name and never mention ids or input/output types. In each step, "why" is one short sentence. Leave a setting \
unset when its default already matches the request.
8. Prefer services from one node's pipeline when they fit together; combine nodes only where the input and \
output types actually match.
"""


@dataclass
class CompositionResult:
    reply: str
    clarifying_question: str | None
    workflow: dict | None
    errors: list[str] = field(default_factory=list)
    attempts: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _catalogue_message(cards: list[ServiceCard]) -> str:
    return "CATALOGUE (one JSON object per service):\n" + "\n".join(
        json.dumps(card.prompt_line(), ensure_ascii=False) for card in cards
    )


def _current_message(current: dict | None, cards: list[ServiceCard]) -> str | None:
    if not current or not current.get("steps"):
        return None
    workflow, _ = validate_proposal(current, cards)
    if not workflow:
        return None
    compact = {
        "steps": [{"ref": s["ref"], "service_id": s["service_id"], "settings": s["settings"]} for s in workflow["steps"]],
        "connections": workflow["connections"],
    }
    return "CURRENT WORKFLOW on the canvas:\n" + json.dumps(compact, ensure_ascii=False)


def compose(model: DesignModel, cards: list[ServiceCard], history: list[dict], current: dict | None) -> CompositionResult:
    history = [m for m in history if m.get("role") in ("user", "assistant") and m.get("content")][-MAX_HISTORY_MESSAGES:]
    latest = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    shown = select_cards(cards, latest)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + _catalogue_message(shown)}]
    current_text = _current_message(current, cards)
    if current_text:
        messages.append({"role": "system", "content": current_text})
    for m in history[:-1]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": f"USER REQUEST: {latest}"})

    result = CompositionResult(reply="", clarifying_question=None, workflow=None)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        answer = model.complete(messages, shown)
        result.attempts = attempt
        result.prompt_tokens += answer.prompt_tokens
        result.completion_tokens += answer.completion_tokens
        data = answer.data
        workflow, errors = validate_proposal(data.get("workflow"), cards)
        result.reply = str(data.get("reply") or "").strip()
        question = data.get("clarifying_question")
        result.clarifying_question = str(question).strip() if question else None
        result.workflow, result.errors = workflow, errors
        if not errors:
            break
        # Show the model its mistakes and ask for a corrected proposal.
        messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
        messages.append({
            "role": "user",
            "content": "VALIDATION FAILED. Fix these problems and return the full corrected answer:\n- " + "\n- ".join(errors),
        })
    return result
