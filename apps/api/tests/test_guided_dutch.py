"""Offline guided draft checks. No provider, orchestrator or real execution."""
import json
from copy import deepcopy

from app.core.config import settings
from app.models.solution import Solution
from app.models.user import User
from app.main import app
from app.routers.design_ai import pilot_user
from app.services import design_ai as service


def configure(monkeypatch):
    policies = json.loads(settings.design_ai_templates)
    policies["dutch"]["run_input"] = {"service_id": "dutch-ConfigureAndSynthesize", "operation_name": "ConfigureAndSynthesize",
        "evidence_reference": "offline fixture", "json_schema": {"type": "object", "properties": {"seed": {"type": "integer", "enum": [42, 43]}}, "required": ["seed"], "additionalProperties": False}}
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps(policies))


def test_guided_defaults_explicit_settings_save_and_undo(environment, db, provider, monkeypatch):
    configure(monkeypatch)
    source = deepcopy(service.content(db.get(Solution, "source-dutch")))
    assert next(t for t in environment.get("/design-ai/templates").json() if t["key"] == "dutch")["guided_available"]
    draft = environment.post("/design-ai/drafts", json={"template_key": "dutch", "guided": True}).json()
    assert draft["design"]["run_input"] == {"seed": 42} and draft["validation"]["valid"]
    assert [n["data"]["label"] for n in service.service_nodes(draft["design"]["nodes"])] == ["Generate sample grid.", "Benchmark grid."]
    url = f"/design-ai/drafts/{draft['id']}"
    proposal = environment.post(url + "/guided-settings", json={"revision": 0, "seed": 43}).json()
    assert proposal["design"]["run_input"] == {"seed": 42}
    assert proposal["pending"]["design"]["run_input"] == {"seed": 43}
    applied = environment.post(url + "/apply", json={"revision": 0, "proposal_id": proposal["pending"]["id"]}).json()
    assert applied["design"]["run_input"] == {"seed": 43}
    assert environment.post(url + "/guided-settings", json={"revision": 0, "seed": 42}).status_code == 409
    bad = environment.post(url + "/guided-settings", json={"revision": 1, "seed": 999}).json()
    assert not bad["pending"]["validation"]["valid"]
    assert environment.post(url + "/apply", json={"revision": 1, "proposal_id": bad["pending"]["id"]}).status_code == 422
    undone = environment.post(url + "/undo", json={"revision": 1}).json()
    assert undone["design"]["run_input"] == {"seed": 42}
    saved = environment.post(url + "/save", json={"revision": 2}).json()["draft"]
    result = environment.get("/solutions/" + saved["saved_solution_id"]).json()
    assert result["design_metadata"]["run_input"] == {"seed": 42}
    assert result["design_metadata"]["guided_experiment"] == "dutch_sample_grid"
    db.expire_all()
    assert db.get(Solution, saved["saved_solution_id"]).created_by_user_id == "designer"
    assert service.content(db.get(Solution, "source-dutch")) == source
    assert not provider.contexts


def test_guided_unavailable_policy_and_request_boundaries(environment, db, monkeypatch):
    assert environment.post("/design-ai/drafts", json={"template_key": "dutch", "guided": True}).status_code == 422
    configure(monkeypatch)
    assert environment.post("/design-ai/drafts", json={"template_key": "denmark", "guided": True}).status_code == 422
    draft = environment.post("/design-ai/drafts", json={"template_key": "dutch", "guided": True}).json()
    url = f"/design-ai/drafts/{draft['id']}/guided-settings"
    for seed in (True, "43", 42.5):
        assert environment.post(url, json={"revision": 0, "seed": seed}).status_code == 422
    assert environment.post(url, json={"revision": 0, "seed": 43}, headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert environment.post(url, json={"revision": 0, "seed": 43, "dataset": "upload"}).status_code == 422
    app.dependency_overrides[pilot_user] = lambda: db.get(User, "other")
    try:
        assert environment.post(url, json={"revision": 0, "seed": 43}).status_code == 404
    finally:
        app.dependency_overrides.pop(pilot_user)
    environment.post("/auth/logout")
    assert environment.post(url, json={"revision": 0, "seed": 43}).status_code == 401
