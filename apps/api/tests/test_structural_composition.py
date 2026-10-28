"""Explicit provider-boundary fixtures; no intent interpretation or execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.solution import Solution
from app.services.design_ai_provider import get_provider
from conftest import TestProvider

DEFINITIONS = json.loads((Path(__file__).resolve().parents[3] / "deploy/aie37/contracts.json").read_text())
PROMPT = "Add a benchmark step after the grid generator and use the grid it produces. Keep the generator settings unchanged."


@pytest.fixture
def composition(environment, monkeypatch):
    with SessionLocal() as db:
        for operation, definition in DEFINITIONS.items():
            db.add(OperationContract(id=f"contract-{operation}", service_id=f"dutch-{operation}", status="active", **definition))
        source = db.get(Solution, "source-dutch")
        generator = next(n for n in source.nodes if n.get("data", {}).get("service", {}).get("operation_name") == "ConfigureAndSynthesize")
        generator = deepcopy(generator)
        pin = {"contract_id": "contract-ConfigureAndSynthesize", "contract_version": "1.0.0"}
        generator["data"].update(operation_contract=pin, configuration={**pin, "parameters": {"seed": 42}})
        boundaries = [deepcopy(n) for n in source.nodes if n.get("type") in {"input", "output"}]
        first, last = next(n for n in boundaries if n["type"] == "input"), next(n for n in boundaries if n["type"] == "output")
        source.nodes = [first, generator, last]
        source.edges = [{"id": "start", "source": first["id"], "target": generator["id"]},
                        {"id": "terminal", "source": generator["id"], "target": last["id"]}]
        db.commit()
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps({"dutch": {"solution_id": "source-dutch", "structural_append_only": True}}))
    provider = TestProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    draft = environment.post("/design-ai/drafts", json={"template_key": "dutch"})
    assert draft.status_code == 200, draft.text
    return environment, draft.json(), provider


def propose(scenario, **patch):
    client, draft, provider = scenario
    source = next(n for n in draft["design"]["nodes"] if n.get("data", {}).get("service"))
    value = {"local_ref": "new_benchmark", "service_id": "dutch-RunBenchmark", "contract_id": "contract-RunBenchmark",
             "contract_version": "1.0.0", "source_slot": "captured_grid", "target_slot": "captured_grid"}
    value.update(patch.pop("value", {}))
    provider.turn = {"message": "OFFLINE FIXTURE: review adding the analyzer; no workflow executes.", "template_key": None,
                     "expected_revision": draft["revision"], "edits": [{"kind": "append_bound_operation", "node_id": source["id"], "value": json.dumps(value)}]}
    provider.turn["edits"][0].update(patch)
    return client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": draft["id"], "revision": draft["revision"],
        "history": [{"role": "user", "content": "unrelated history"}]})


def apply(client, draft):
    return client.post(f"/design-ai/drafts/{draft['id']}/apply", json={"revision": draft["revision"], "proposal_id": draft["pending"]["id"]})


def test_main_pending_apply_undo_save_builder(composition):
    client, draft, provider = composition
    response = propose(composition)
    assert response.status_code == 200, response.text
    pending = response.json()["draft"]
    assert pending["design"] == draft["design"]
    review = pending["pending"]["structural_review"]
    assert review["connections_removed"] == [draft["design"]["edges"][1]]
    assert len(review["connections_added"]) == 2
    candidate = pending["pending"]["design"]
    assert candidate["nodes"][:-1] == draft["design"]["nodes"]
    assert candidate["edges"][0] == draft["design"]["edges"][0]
    assert candidate["edges"][1]["data"]["binding"] == {"source_slot": "captured_grid", "target_slot": "captured_grid"}
    assert candidate["nodes"][-1]["id"] != "new_benchmark"
    current = apply(client, pending)
    assert current.status_code == 200, current.text
    assert current.json()["design"] == candidate
    assert apply(client, pending).status_code == 409
    undone = client.post(f"/design-ai/drafts/{draft['id']}/undo", json={"revision": 1}).json()
    assert undone["design"] == draft["design"]
    pending = propose((client, undone, provider)).json()["draft"]
    current = apply(client, pending).json()
    saved = client.post(f"/design-ai/drafts/{draft['id']}/save", json={"revision": current["revision"]})
    assert saved.status_code == 200, saved.text
    saved = saved.json()["draft"]
    reopened = client.get(f"/design-ai/drafts/{draft['id']}").json()
    builder = client.get(f"/solutions/{saved['saved_solution_id']}").json()
    assert reopened["design"] == current["design"]
    assert builder["nodes"] == current["design"]["nodes"] and builder["edges"] == current["design"]["edges"]
    assert propose((client, current, provider)).status_code == 422  # existing analyzer
    context = provider.contexts[0]
    assert set(context) == {"request", "history", "draft", "configuration"}
    assert context["history"] == []
    assert not any(word in json.dumps(context) for word in ("internal_host", "internal_port", "password", "unrelated history", "artifact contents"))
    assert len(context["configuration"]["compatible_candidates"]) == 1


@pytest.mark.parametrize("patch", [
    {"value": {"service_id": "unknown"}}, {"value": {"contract_id": "unknown"}},
    {"value": {"contract_version": "9.0.0"}}, {"value": {"source_slot": "json"}},
    {"value": {"target_slot": "json"}}, {"value": {"projection": "grid"}},
    {"value": {"merge": []}}, {"value": {"node_id": "arbitrary"}},
    {"value": {"local_ref": "workflow-input"}}, {"node_id": "cross-draft"},
])
def test_reject_invalid_provider_proposals(composition, patch):
    client, draft, _ = composition
    if patch.get("value", {}).get("local_ref") == "workflow-input":
        patch = {"value": {"local_ref": draft["design"]["nodes"][0]["id"]}}
    response = propose(composition, **patch)
    assert response.status_code in {409, 422}, response.text
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]


@pytest.mark.parametrize("change", ["contract", "schema", "pin", "approval", "authorization", "catalogue", "revision"])
def test_apply_rechecks_authority_atomically(composition, change):
    from app.models.design_ai import DesignDraft
    client, draft, _ = composition
    pending = propose(composition).json()["draft"]
    with SessionLocal() as db:
        contract = db.get(OperationContract, "contract-RunBenchmark")
        service = db.get(Service, "dutch-RunBenchmark")
        if change in {"contract", "schema"}:
            definition = deepcopy(contract.definition)
            if change == "schema":
                definition["inputs"][0]["schema_ref"] = "urn:incompatible"
            else:
                definition["compatibility_notes"] = ["Changed after review"]
            contract.definition = definition
        elif change == "pin": contract.status = "deprecated"
        elif change == "approval": service.status = "draft"
        elif change == "authorization": service.status, service.created_by_user_id = "validated", "other"
        elif change == "catalogue": service.description = "Changed after review"
        else: db.get(DesignDraft, draft["id"]).revision = 1
        db.commit()
    response = apply(client, pending)
    assert response.status_code in {409, 422}, response.text
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]


def test_clarification_has_no_mutation(composition):
    # Two current grid-producing instances make the user's source wording ambiguous.
    # Interpretation remains an explicit boundary fixture, not a model-quality claim.
    from app.models.design_ai import DesignDraft
    client, draft, provider = composition
    with SessionLocal() as db:
        db.add(Service(id="transformer", name="Other grid generator", operation_name="TransformGrid", provider="Test",
            category="Test", description="Offline fixture", input_type="JSON", output_type="JSON", status="approved"))
        db.flush()
        definition = deepcopy(DEFINITIONS["RunBenchmark"])
        definition["operation_identity"] = "urn:test:transform-grid"
        definition["runtime_operation_name"] = "TransformGrid"
        definition["definition"]["outputs"] = deepcopy(DEFINITIONS["ConfigureAndSynthesize"]["definition"]["outputs"])
        db.add(OperationContract(id="transform-contract", service_id="transformer", status="active", **definition))
        row = db.get(DesignDraft, draft["id"])
        state = deepcopy(row.state)
        design = state["design"]
        source = next(n for n in design["nodes"] if n.get("data", {}).get("service"))
        design["nodes"].append({"id": "other-grid", "position": {"x": 600, "y": 0}, "data": {
            "label": "Other grid generator", "service": {"id": "transformer", "operation_name": "TransformGrid"},
            "operation_contract": {"contract_id": "transform-contract", "contract_version": "1.0.0"}}})
        design["edges"][-1]["source"] = "other-grid"
        design["edges"].append({"id": "upstream", "source": source["id"], "target": "other-grid",
            "data": {"binding": {"source_slot": "captured_grid", "target_slot": "captured_grid"}}})
        row.state = state
        db.commit()
    provider.turn = {"message": "OFFLINE FIXTURE: Which generator should supply the input?", "template_key": None, "expected_revision": 0, "edits": []}
    before = client.get(f"/design-ai/drafts/{draft['id']}").json()
    assert before["validation"]["valid"]
    response = client.post("/design-ai/chat", json={"message": "Add a benchmark using the grid", "draft_id": draft["id"], "revision": 0})
    assert response.status_code == 200 and response.json()["draft"] is None
    assert client.get(f"/design-ai/drafts/{draft['id']}").json() == before


def test_existing_analyzer_explanation_does_not_add_duplicate(composition):
    client, _, provider = composition
    pending = propose(composition).json()["draft"]
    applied = apply(client, pending).json()
    before = client.get(f"/design-ai/drafts/{applied['id']}").json()
    provider.turn = {"message": "OFFLINE FIXTURE: The benchmark already consumes the generated grid; no addition is needed.",
        "template_key": None, "expected_revision": 1, "edits": []}
    response = client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": applied["id"], "revision": 1})
    assert response.status_code == 200 and response.json()["draft"] is None
    assert provider.contexts[-1]["configuration"]["compatible_candidates"] == []
    assert client.get(f"/design-ai/drafts/{applied['id']}").json() == before


def test_trusted_identity_collision_fails_closed(composition, monkeypatch):
    from app.services import design_ai
    client, draft, _ = composition
    monkeypatch.setattr(design_ai, "uuid4", lambda: draft["design"]["nodes"][0]["id"])
    assert propose(composition).status_code == 409
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]


def test_structural_source_cannot_enable_workflow_input_routing(composition):
    client, _, _ = composition
    with SessionLocal() as db:
        db.get(Solution, "source-dutch").design_metadata = {"run_input": {"unsupported": "routing"}}
        db.commit()
    assert client.post("/design-ai/drafts", json={"template_key": "dutch"}).status_code == 422


@pytest.mark.parametrize("mutation", ["duplicate", "cycle", "merge", "projection"])
def test_complete_graph_rejected_without_partial_mutation(composition, mutation):
    from app.models.design_ai import DesignDraft
    client, draft, _ = composition
    with SessionLocal() as db:
        row = db.get(DesignDraft, draft["id"])
        state = deepcopy(row.state)
        edges = state["design"]["edges"]
        if mutation == "duplicate": edges.append({**edges[0], "id": "duplicate"})
        elif mutation == "cycle": edges.append({"id": "cycle", "source": edges[1]["target"], "target": edges[0]["source"]})
        elif mutation == "merge": edges.append({"id": "merge", "source": edges[0]["source"], "target": edges[1]["target"]})
        else: edges[0]["sourceHandle"] = "projection"
        row.state = state
        db.commit()
        before = deepcopy(state["design"])
    assert propose(composition).status_code == 422
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == before


def test_settings_scope_cannot_append(composition, monkeypatch):
    from app.models.design_ai import DesignDraft
    client, draft, _ = composition
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps({"dutch": {"solution_id": "source-dutch", "instance_settings_only": True}}))
    with SessionLocal() as db:
        row = db.get(DesignDraft, draft["id"])
        state = deepcopy(row.state)
        state["design"]["editing_scope"] = "instance_settings"
        row.state = state
        db.commit()
    assert propose(composition).status_code == 422


def test_historical_snapshot_and_other_owner_unchanged(composition):
    from app.models.user import User
    from app.services.execution_submission import prepare
    from app.schemas.workflow_submit import WorkflowSubmitRequest
    from app.services import design_ai
    client, draft, _ = composition
    with SessionLocal() as db:
        history = prepare(db, db.get(User, "designer"), WorkflowSubmitRequest(name="Historical fixture", nodes=[], edges=[]),
            {"solution_studio_metadata": {"execution_instances": []}, "fixture_seed": 43})
        history.workflow_id = "wf-abcdefabcdef"
        db.commit()
        source = deepcopy(design_ai.content(db.get(Solution, "source-dutch")))
    before = client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json()
    pending = propose(composition).json()["draft"]
    assert apply(client, pending).status_code == 200
    assert client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json() == before
    with SessionLocal() as db:
        assert design_ai.content(db.get(Solution, "source-dutch")) == source
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:
            design_ai.apply(draft["id"], 0, pending["pending"]["id"], db, db.get(User, "other"))
        assert error.value.status_code == 404
