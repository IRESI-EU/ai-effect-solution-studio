import pytest

from app.core.config import settings
from app.design_ai.catalogue import build_catalogue, card_for
from app.design_ai.composer import compose
from app.design_ai.providers import ModelResult, OfflineModel
from app.design_ai.validator import validate_proposal
from app.models.service import Service
from app.services.service_settings import normalize_definition

VILLAS_SETTINGS = normalize_definition({
    "channel": "parameters",
    "schema": {"properties": {"round_decimals": {"type": "integer", "default": 3, "minimum": 0, "maximum": 8}}},
})


def _svc(sid, op, inp, out, description="d", status="approved", settings=None, container=None):
    return Service(
        id=sid, name=f"{op} ({sid})", provider="German node", category="Energy", description=description,
        input_type=inp, output_type=out, status=status, lifecycle_status="active",
        container_name=container or sid, operation_name=op, internal_host=sid,
        interface_contract={"settings": settings} if settings else {},
    )


@pytest.fixture
def ai_catalogue(session_factory):
    items = [
        _svc("ai-provider", "ProvideData", "Workflow Start", "villas_chronics1 Input"),
        _svc("ai-villas", "GenerateChronics", "villas_chronics1 Input", "output_formatter1 Input", settings=VILLAS_SETTINGS),
        _svc("ai-formatter", "FormatOutput", "output_formatter1 Input", "Workflow Output"),
        _svc("ai-test", "Hello", "Workflow Start", "Workflow Output", description="TEST only. Hello."),
        _svc("ai-pending", "Pending", "Workflow Start", "Workflow Output", status="pending_review"),
    ]
    with session_factory() as db:
        for item in items:
            db.merge(item)
        db.commit()
        cards = [c for c in build_catalogue(db) if c.id.startswith("ai-")]
    yield cards
    with session_factory() as db:
        db.query(Service).filter(Service.id.like("ai-%")).delete(synchronize_session=False)
        db.commit()


GOOD = {
    "steps": [
        {"ref": "s1", "service_id": "ai-provider", "why": "data", "settings": []},
        {"ref": "s2", "service_id": "ai-villas", "why": "series", "settings": [{"name": "round_decimals", "value_json": "2"}]},
        {"ref": "s3", "service_id": "ai-formatter", "why": "check", "settings": []},
    ],
    "connections": [{"from_ref": "s1", "to_ref": "s2"}, {"from_ref": "s2", "to_ref": "s3"}],
}


def test_catalogue_excludes_unapproved_and_test_services_and_uses_curated_purpose(ai_catalogue):
    ids = {c.id for c in ai_catalogue}
    assert ids == {"ai-provider", "ai-villas", "ai-formatter"}
    villas = next(c for c in ai_catalogue if c.id == "ai-villas")
    assert "VILLASnode" in villas.purpose
    assert villas.prompt_line()["settings"]["round_decimals"]["maximum"] == 8
    assert next(c for c in ai_catalogue if c.id == "ai-formatter").prompt_line()["settings"] == "fixed"


def test_provider_written_description_wins():
    service = _svc("x", "GenerateChronics", "a", "b")
    service.interface_contract = {"design": {"purpose": "Own words", "keywords": ["chronics"]}}
    assert card_for(service).purpose == "Own words"


def test_valid_proposal_is_normalised(ai_catalogue):
    workflow, errors = validate_proposal(GOOD, ai_catalogue)
    assert errors == []
    assert workflow["steps"][1]["settings"] == {"round_decimals": 2}
    assert workflow["steps"][1]["provider"] == "German node"


@pytest.mark.parametrize("mutate, message", [
    (lambda p: p["steps"].__setitem__(0, {**p["steps"][0], "service_id": "nope"}), "not an approved catalogue service"),
    (lambda p: p["connections"].__setitem__(0, {"from_ref": "s1", "to_ref": "s3"}), "cannot feed"),
    (lambda p: p["steps"][1].__setitem__("settings", [{"name": "round_decimals", "value_json": "42"}]), "at most 8"),
    (lambda p: p["steps"][2].__setitem__("settings", [{"name": "x", "value_json": "1"}]), "fixed settings"),
    (lambda p: p["connections"].append({"from_ref": "s3", "to_ref": "s1"}), "cannot feed"),
    (lambda p: p["steps"].append({"ref": "s4", "service_id": "ai-villas", "why": "", "settings": []}), "used twice"),
])
def test_invalid_proposals_are_explained(ai_catalogue, mutate, message):
    import copy
    proposal = copy.deepcopy(GOOD)
    mutate(proposal)
    _, errors = validate_proposal(proposal, ai_catalogue)
    assert any(message in e for e in errors), errors


class ScriptedModel:
    name, model = "scripted", "test"

    def __init__(self, answers):
        self.answers, self.seen = list(answers), []

    def complete(self, messages, cards):
        self.seen.append(messages)
        return ModelResult(self.answers.pop(0), 100, 20)


def test_composer_feeds_errors_back_and_accepts_repair(ai_catalogue):
    bad = {"reply": "r", "clarifying_question": None, "workflow": {**GOOD, "connections": [{"from_ref": "s1", "to_ref": "s3"}]}}
    good = {"reply": "Fixed", "clarifying_question": None, "workflow": GOOD}
    model = ScriptedModel([bad, good])
    result = compose(model, ai_catalogue, [{"role": "user", "content": "German time series with 2 decimals"}], None)
    assert result.errors == [] and result.attempts == 2 and result.reply == "Fixed"
    assert "VALIDATION FAILED" in model.seen[1][-1]["content"]
    assert result.prompt_tokens == 200


def test_offline_model_builds_compatible_chain(ai_catalogue):
    result = compose(OfflineModel(), ai_catalogue, [{"role": "user", "content": "generate German grid time series data"}], None)
    assert result.errors == []
    assert [s["service_id"] for s in result.workflow["steps"]] == ["ai-provider", "ai-villas", "ai-formatter"]


def test_endpoint_respects_switch_and_daily_limit(client, ai_catalogue, monkeypatch):
    body = {"messages": [{"role": "user", "content": "German grid time series"}]}
    monkeypatch.setattr(settings, "design_ai_enabled", False)
    assert client.post("/design-ai/compose", json=body).status_code == 503

    monkeypatch.setattr(settings, "design_ai_enabled", True)
    monkeypatch.setattr(settings, "design_ai_provider", "offline")
    response = client.post("/design-ai/compose", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["valid"] is True and data["provider"] == "offline"

    used = client.get("/design-ai/status").json()["used_last_24h"]
    monkeypatch.setattr(settings, "design_ai_daily_requests_per_user", used)
    assert client.post("/design-ai/compose", json=body).status_code == 429
