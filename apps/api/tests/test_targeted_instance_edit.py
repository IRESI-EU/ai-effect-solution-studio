"""Provider-boundary fixtures; these never interpret intent or execute services."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models.operation_contract import OperationContract
from app.models.solution import Solution
from app.models.user import User
from app.services import design_ai
from app.services.design_ai_provider import get_provider
from conftest import TestProvider

DEFINITION = json.loads((Path(__file__).resolve().parents[3] / "deploy/aie18/contracts.json").read_text())["GenerateTopology"]
PROMPT = "Change the second topology step to generate up to four options. Leave the first step unchanged."


@pytest.fixture
def scenario(environment, monkeypatch):
    with SessionLocal() as db:
        db.add(OperationContract(id="topology-contract", service_id="denmark-GenerateTopology", status="active",
            operation_identity=DEFINITION["operation_identity"], runtime_operation_name="GenerateTopology", contract_version="1.0.0",
            schema_version="1.0", source_kind="manual", definition={"operation_role": "source", "execution_parameters": DEFINITION["execution_parameters"]}))
        nodes = [{"id": identifier, "position": {"x": index * 250, "y": 0}, "data": {
            "label": label, "service": {"id": "denmark-GenerateTopology", "operation_name": "GenerateTopology"},
            "configuration": {"contract_id": "topology-contract", "contract_version": "1.0.0",
                "parameters": {"how_many": index + 1, "allow_hx": index == 0, "allow_bypass": index != 0}}}}
            for index, (identifier, label) in enumerate((("topology-first", "First topology step"), ("topology-second", "Second topology step")))]
        db.add(Solution(id="instance-source", name="Disposable topology settings", nodes=nodes,
            edges=[{"id": "binding", "source": "topology-first", "target": "topology-second"}], status="draft", created_by_user_id="designer"))
        db.commit()
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps({"denmark": {"solution_id": "instance-source", "instance_settings_only": True}}))
    provider = TestProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    response = environment.post("/design-ai/drafts", json={"template_key": "denmark"})
    assert response.status_code == 200, response.text
    return environment, response.json(), provider


def propose(client, draft, provider, *, parameters=None, target="topology-second", revision=None):
    provider.turn = {"message": "Offline fixture: review the second step's maximum; no experiment has run.", "template_key": None,
        "expected_revision": draft["revision"] if revision is None else revision,
        "edits": [{"kind": "set_node_parameters", "node_id": target, "value": json.dumps({"contract_id": "topology-contract",
            "contract_version": "1.0.0", "parameters": {"how_many": 4} if parameters is None else parameters})}]}
    return client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": draft["id"], "revision": draft["revision"]})


def apply(client, pending):
    return client.post(f"/design-ai/drafts/{pending['id']}/apply", json={"revision": pending["revision"], "proposal_id": pending["pending"]["id"]})


def configurations(design):
    return {n["id"]: n["data"]["configuration"] for n in design["nodes"]}


def test_targeted_review_apply_undo_save_reload_builder_and_history(scenario):
    client, draft, provider = scenario
    with SessionLocal() as db:
        source = deepcopy(design_ai.content(db.get(Solution, "instance-source")))
        from app.services.execution_submission import prepare
        from app.schemas.workflow_submit import WorkflowSubmitRequest
        history = prepare(db, db.get(User, "designer"), WorkflowSubmitRequest(name="Historical fixture", nodes=[], edges=[]),
            {"solution_studio_metadata": {"execution_instances": []}, "fixture_original_limits": [1, 2]})
        history.workflow_id = "wf-abcdefabcdef"
        db.commit()
    historical = client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json()
    response = propose(client, draft, provider)
    assert response.status_code == 200, response.text
    pending = response.json()["draft"]
    assert pending["design"] == draft["design"]
    review = pending["pending"]["parameter_review"]
    assert [(x["node_id"], x["key"], x["before"], x["after"]) for x in review["changes"]] == [("topology-second", "how_many", 2, 4)]
    assert review["unchanged"][0]["parameters"]["how_many"] == 1
    applied = apply(client, pending)
    assert applied.status_code == 200, applied.text
    current = applied.json()
    expected = deepcopy(draft["design"])
    expected["nodes"][1]["data"]["configuration"]["parameters"]["how_many"] = 4
    assert current["design"] == expected
    assert apply(client, pending).status_code == 409
    undone = client.post(f"/design-ai/drafts/{draft['id']}/undo", json={"revision": 1}).json()
    assert undone["design"] == draft["design"]
    reproposed = propose(client, undone, provider).json()["draft"]
    applied = apply(client, reproposed).json()
    saved = client.post(f"/design-ai/drafts/{draft['id']}/save", json={"revision": applied["revision"]})
    assert saved.status_code == 200, saved.text
    saved = saved.json()["draft"]
    reopened_draft = client.get(f"/design-ai/drafts/{draft['id']}").json()
    reopened_solution = client.get("/solutions/" + saved["saved_solution_id"]).json()
    assert configurations(reopened_draft["design"]) == configurations(reopened_solution)
    assert configurations(reopened_solution) == configurations(expected)
    assert reopened_solution["edges"] == draft["design"]["edges"]
    assert client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json() == historical
    with SessionLocal() as db:
        assert design_ai.content(db.get(Solution, "instance-source")) == source


def test_ambiguous_fixture_clarifies_without_mutation_and_context_is_scoped(scenario):
    client, draft, provider = scenario
    provider.turn = {"message": "Which instance should change: First topology step or Second topology step?", "template_key": None,
        "expected_revision": 0, "edits": []}
    response = client.post("/design-ai/chat", json={"message": "Change the topology limit to four.", "draft_id": draft["id"], "revision": 0,
        "history": [{"role": "user", "content": "unrelated old private data"}]})
    assert response.status_code == 200 and response.json()["draft"] is None
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]
    context = provider.contexts[0]
    assert set(context) == {"request", "history", "configuration", "draft"}
    assert context["history"] == [] and context["draft"] == {"revision": 0, "editing_scope": "instance_settings"}
    instances = context["configuration"]["instances"]
    assert [(n["node_id"], n["label"], n["parameters"]["how_many"]) for n in instances] == [
        ("topology-first", "First topology step", 1), ("topology-second", "Second topology step", 2)]
    assert instances[1]["definition"]["properties"]["how_many"]["maximum"] == 20
    assert not any(key in json.dumps(context) for key in ("internal_host", "internal_port", "password", "artifact", "unrelated old private data"))


@pytest.mark.parametrize("parameters", [{"unknown": 4}, {"how_many": "4"}, {"how_many": True}, {"how_many": 21}, {"how_many": None}])
def test_invalid_setting_rejected_without_proposal(scenario, parameters):
    client, draft, provider = scenario
    assert propose(client, draft, provider, parameters=parameters).status_code == 422
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["pending"] is None


def test_logical_target_stability_missing_target_and_stale_revision(scenario):
    client, draft, provider = scenario
    assert propose(client, draft, provider, target="deleted-instance").status_code == 422
    assert propose(client, draft, provider, revision=99).status_code == 409
    with SessionLocal() as db:
        row = design_ai.load_draft(draft["id"], db, db.get(User, "designer"))
        state = deepcopy(row.state)
        state["design"]["nodes"].reverse()  # Array order is not an instance identity.
        row.state = state
        db.commit()
    pending = propose(client, draft, provider).json()["draft"]
    applied = apply(client, pending).json()
    assert configurations(applied["design"])["topology-first"]["parameters"]["how_many"] == 1
    assert configurations(applied["design"])["topology-second"]["parameters"]["how_many"] == 4
    assert client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": draft["id"], "revision": 0}).status_code == 409


def test_unauthorized_draft_and_cross_draft_target_are_rejected(scenario):
    client, draft, provider = scenario
    with TestClient(app) as anonymous:
        assert anonymous.get(f"/design-ai/drafts/{draft['id']}").status_code == 401
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, "other")
        assert client.get(f"/design-ai/drafts/{draft['id']}").status_code == 404
        assert client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": draft["id"], "revision": 0}).status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert provider.contexts == []
    assert propose(client, draft, provider, target="node-from-another-draft").status_code == 422


@pytest.mark.parametrize("mutation", ["unavailable", "definition-drift", "version"])
def test_contract_pins_revalidate_before_apply(scenario, mutation):
    client, draft, provider = scenario
    pending = propose(client, draft, provider).json()["draft"]
    with SessionLocal() as db:
        contract = db.get(OperationContract, "topology-contract")
        if mutation == "unavailable": contract.status = "deprecated"
        if mutation == "version": contract.contract_version = "2.0.0"
        if mutation == "definition-drift":
            definition = deepcopy(contract.definition)
            definition["execution_parameters"]["properties"]["how_many"]["description"] += " Contract changed after review."
            contract.definition = definition
        db.commit()
    assert apply(client, pending).status_code == 409
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]
    if mutation != "definition-drift":
        assert client.get(f"/design-ai/drafts/{draft['id']}").json()["instance_settings"][0]["resolution"] == "unavailable"


def test_settings_scope_cannot_rename_or_rebind_contract(scenario):
    client, draft, provider = scenario
    provider.turn = {"message": "Unsupported fixture", "template_key": None, "expected_revision": 0,
        "edits": [{"kind": "rename", "node_id": None, "value": "Changed"}]}
    assert client.post("/design-ai/chat", json={"message": "Rename", "draft_id": draft["id"], "revision": 0}).status_code == 422
    assert client.get(f"/design-ai/drafts/{draft['id']}").json()["design"] == draft["design"]


def test_unavailable_contract_explained_without_guessed_settings(scenario):
    client, draft, provider = scenario
    with SessionLocal() as db:
        db.get(OperationContract, "topology-contract").status = "deprecated"
        db.commit()
    provider.turn = {"message": "The parameter contract is unavailable; I cannot propose a supported value.", "template_key": None,
        "expected_revision": 0, "edits": []}
    result = client.post("/design-ai/chat", json={"message": PROMPT, "draft_id": draft["id"], "revision": 0})
    assert result.status_code == 200 and result.json()["draft"] is None
    assert provider.contexts[-1]["configuration"]["supported_edits"] == []
    assert all(n["resolution"] == "unavailable" and "definition" not in n for n in provider.contexts[-1]["configuration"]["instances"])
    assert client.post(f"/design-ai/drafts/{draft['id']}/save", json={"revision": 0}).status_code == 422


def test_deleted_target_cannot_be_retargeted_after_review(scenario):
    client, draft, provider = scenario
    pending = propose(client, draft, provider).json()["draft"]
    with SessionLocal() as db:
        row = design_ai.load_draft(draft["id"], db, db.get(User, "designer"))
        state = deepcopy(row.state)
        state["design"]["nodes"] = [n for n in state["design"]["nodes"] if n["id"] != "topology-second"]
        row.state = state
        db.commit()
    assert apply(client, pending).status_code == 422
    assert configurations(client.get(f"/design-ai/drafts/{draft['id']}").json()["design"])["topology-first"]["parameters"]["how_many"] == 1


def test_saved_settings_copy_still_requires_compatible_readiness(scenario, monkeypatch):
    import app.main as main
    from app.services import orchestrator_adapter as adapter
    from app.models.execution_submission import ExecutionSubmission
    client, draft, provider = scenario
    applied = apply(client, propose(client, draft, provider).json()["draft"]).json()
    saved = client.post(f"/design-ai/drafts/{draft['id']}/save", json={"revision": applied["revision"]}).json()["draft"]
    solution = client.get("/solutions/" + saved["saved_solution_id"]).json()
    payload = {"name": solution["name"], "solution_id": solution["id"], "expected_updated_at": solution["updated_at"],
        "nodes": [{"node_id": n["id"], "service_id": n["data"]["service"]["id"], "container_name": "ignored", "operation_name": "GenerateTopology",
            "configuration": n["data"]["configuration"]} for n in solution["nodes"]], "edges": [{"source": "topology-first", "target": "topology-second"}]}
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *args: {"status": "ready"})
    monkeypatch.setattr(adapter.requests, "get", lambda *a, **k: type("Response", (), {"status_code": 404})())
    monkeypatch.setattr(main, "submit_to_orchestrator", lambda *a: pytest.fail("No workflow may be submitted"))
    assert client.post("/workflows/runtime-preflight", json=payload).status_code == 409
    assert client.post("/workflows/submit-to-orchestrator", json=payload).status_code == 409
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).count() == 0
