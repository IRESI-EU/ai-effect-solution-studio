"""Compatibility fixtures do not contact real wrappers or providers."""
from copy import deepcopy
import json
import pytest
from fastapi import HTTPException
from app.services import orchestrator_adapter as adapter
from app.services.parameter_values import parameter_contract_digest
from test_instance_parameters import configured, node, workflow, configuration


@pytest.mark.parametrize("mutation", [None, "old-runtime", "unknown", "malformed-transports", "schema", "contract", "digest", "missing-instance"])
def test_compatibility_matrix_and_contract_agreement(configured, monkeypatch, mutation):
    client = configured
    saved = client.post("/solutions", json={"name": "Compatibility fixture", "nodes": [node("first"), node("second", 43)], "edges": []}).json()
    compiled = client.post("/workflows/compile", json=workflow(saved)).json()
    capability = {"capability_schema_version": "1.0", "transports": ["http-parameters-v1"], "parameter_validation": "wrapper-contract-v1"}
    report = {"status": "ready", "checks": {n["node_key"]: {
        **{key: n["configuration"][key] for key in ("operation_identity", "contract_version", "schema_version")},
        "parameter_contract_sha256": n["parameter_contract_sha256"]}
        for n in compiled["solution_studio_metadata"]["execution_instances"]}}
    if mutation == "old-runtime": capability.pop("parameter_validation")
    if mutation == "unknown": capability = {}
    if mutation == "malformed-transports": capability["transports"] = "http-parameters-v1"
    first = next(iter(report["checks"]))
    if mutation == "schema": report["checks"][first]["schema_version"] = "2.0"
    if mutation == "contract": report["checks"][first]["contract_version"] = "2.0.0"
    if mutation == "digest": report["checks"][first]["parameter_contract_sha256"] = "unrecognized-definition"
    if mutation == "missing-instance": report["checks"].pop(first)
    class Response:
        status_code = 200
        def __init__(self, value): self.value = value
        def json(self): return deepcopy(self.value)
    calls = []
    monkeypatch.setattr(adapter.requests, "get", lambda *a, **k: Response(capability))
    def post(url, **kwargs):
        assert url.endswith("/workflows/check-compatibility")
        assert kwargs["json"]["task_configurations"] == compiled["task_configurations"]
        calls.append(url)
        return Response(report)
    monkeypatch.setattr(adapter.requests, "post", post)
    if mutation is None:
        assert adapter.require_parameter_transport(compiled) == report
    else:
        with pytest.raises(HTTPException) as error: adapter.require_parameter_transport(compiled)
        assert error.value.status_code == 409
    assert len(calls) == (0 if mutation in ("old-runtime", "unknown", "malformed-transports") else 1)


def test_offline_parameter_proposal_apply_save_reload(configured, provider):
    from app.schemas.design_ai import AssistantTurn
    client = configured
    draft = client.post("/design-ai/drafts", json={"template_key": "dutch"}).json()
    instance = next(n for n in draft["design"]["nodes"] if n.get("data", {}).get("service", {}).get("operation_name") == "ConfigureAndSynthesize")
    provider.turn = AssistantTurn(message="Offline parameter proposal", template_key=None, expected_revision=0,
        edits=[{"kind": "set_node_parameters", "node_id": instance["id"], "value": json.dumps(configuration(43))}])
    response = client.post("/design-ai/chat", json={"message": "Set this instance seed to 43", "draft_id": draft["id"], "revision": 0})
    assert response.status_code == 200, response.text
    pending = response.json()["draft"]
    assert pending["design"] == draft["design"]
    apply_body = {"revision": pending["revision"], "proposal_id": pending["pending"]["id"]}
    applied = client.post(f"/design-ai/drafts/{draft['id']}/apply", json=apply_body)
    assert applied.status_code == 200, applied.text
    assert client.post(f"/design-ai/drafts/{draft['id']}/apply", json=apply_body).status_code == 409
    saved = client.post(f"/design-ai/drafts/{draft['id']}/save", json={"revision": 1})
    assert saved.status_code == 200, saved.text
    reopened = client.get("/solutions/" + saved.json()["draft"]["saved_solution_id"]).json()
    target = next(n for n in reopened["nodes"] if n["id"] == instance["id"])
    assert target["data"]["configuration"] == configuration(43)
    # Untargeted operation retains its prior configuration state.
    for before in draft["design"]["nodes"]:
        if before["id"] != instance["id"]:
            assert next(n for n in reopened["nodes"] if n["id"] == before["id"])["data"] == before["data"]
