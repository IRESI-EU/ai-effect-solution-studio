"""AIE-18 isolated fixtures; these are not runtime consumption evidence."""
from copy import deepcopy
import json

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.models.execution_submission import ExecutionSubmission
from app.models.solution import Solution
from app.models.user import User
from app.schemas.operation_contract import ExecutionParameterContract
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.parameter_values import effective_parameters
from app.services.workflow_compiler import compile_to_wp3_payload
from app.services import design_ai

DEFINITION = {"schema_version": "1.0", "transport": "http-parameters-v1", "properties": {
    "seed": {"type": "integer", "title": "Seed", "description": "Verified test fixture", "default": 42, "enum": [42, 43]}}}


@pytest.fixture
def configured(environment):
    with SessionLocal() as db:
        db.add(OperationContract(id="fixture-contract", service_id="dutch-ConfigureAndSynthesize", status="active",
            operation_identity="urn:aieffect:test:synth", runtime_operation_name="ConfigureAndSynthesize", contract_version="1.0.0",
            schema_version="1.0", source_kind="manual", definition={"operation_role": "source", "execution_parameters": DEFINITION}))
        db.commit()
    return environment


def configuration(seed=42):
    return {"contract_id": "fixture-contract", "contract_version": "1.0.0", "parameters": {"seed": seed}}


def node(identifier, seed=42):
    return {"id": identifier, "position": {"x": 0, "y": 0}, "data": {
        "node_kind": "service", "service": {"id": "dutch-ConfigureAndSynthesize"}, "configuration": configuration(seed)}}


def workflow(solution):
    return {"name": solution["name"], "solution_id": solution["id"], "expected_updated_at": solution["updated_at"],
            "nodes": [{"node_id": n["id"], "service_id": n["data"]["service"]["id"], "container_name": "ignored",
                       "operation_name": "ConfigureAndSynthesize", "configuration": n["data"]["configuration"]} for n in solution["nodes"]],
            "edges": [{"source": e["source"], "target": e["target"]} for e in solution["edges"]]}


@pytest.mark.parametrize("value", [None, {"seed": None}, {"seed": True}, {"seed": "42"}, {"seed": 42.0}, {"seed": 44}, {"path": "/tmp"}])
def test_reject_invalid_and_unsupported(value):
    with pytest.raises(ValueError):
        effective_parameters(DEFINITION, value)


def test_defaults_required_bounds_and_independence():
    assert effective_parameters(DEFINITION, {}) == {"seed": 42}
    spec = {"properties": {"count": {"type": "integer", "required": True, "minimum": 1, "maximum": 3}}}
    for value in ({}, {"count": 0}, {"count": 4}):
        with pytest.raises(ValueError):
            effective_parameters(spec, value)
    result = effective_parameters(DEFINITION, {})
    result["seed"] = 43
    assert effective_parameters(DEFINITION, {}) == {"seed": 42}


def test_registry_schema_rejects_unbounded_strings_invalid_defaults_and_versions():
    for definition in ({**DEFINITION, "schema_version": "2.0"},
        {**DEFINITION, "properties": {"path": {"type": "string", "title": "Path", "description": "Not supported"}}},
        {**DEFINITION, "properties": {"seed": {**DEFINITION["properties"]["seed"], "default": None}}}):
        with pytest.raises(ValidationError):
            ExecutionParameterContract.model_validate(definition)


@pytest.mark.parametrize("bad", [None, {"contract_id": {}, "contract_version": "1.0.0", "parameters": {}},
    {"contract_id": "fixture-contract", "contract_version": "1.0.0", "parameters": {"secret": "not-allowed"}}])
def test_save_rejects_malformed_configuration(configured, bad):
    value = node("one")
    value["data"]["configuration"] = bad
    assert configured.post("/solutions", json={"name": "Invalid", "nodes": [value], "edges": []}).status_code == 422


def test_unavailable_runtime_cannot_submit(configured, monkeypatch):
    import app.main as main
    import app.services.orchestrator_adapter as adapter
    saved = configured.post("/solutions", json={"name": "Blocked", "nodes": [node("one")], "edges": []}).json()
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *args: {"status": "ready"})
    monkeypatch.setattr(adapter.requests, "get", lambda *a, **k: type("Response", (), {"status_code": 404})())
    monkeypatch.setattr(main, "submit_to_orchestrator", lambda *a: pytest.fail("Must not submit to an old runtime"))
    assert configured.post("/workflows/submit-to-orchestrator", json=workflow(saved)).status_code == 409
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).count() == 0


def test_save_reload_ownership_stale_and_unsupported(configured):
    client = configured
    created = client.post("/solutions", json={"name": "Instances", "nodes": [node("one"), node("two", 43)], "edges": []})
    assert created.status_code == 200, created.text
    saved = created.json()
    reopened = client.get(f"/solutions/{saved['id']}").json()
    assert [n["data"]["configuration"]["parameters"] for n in reopened["nodes"]] == [{"seed": 42}, {"seed": 43}]
    edited = deepcopy(saved["nodes"])
    edited[0]["data"]["configuration"]["parameters"]["seed"] = 43
    assert client.put(f"/solutions/{saved['id']}", json={"nodes": edited}).status_code == 409
    update = client.put(f"/solutions/{saved['id']}", json={"nodes": edited, "expected_updated_at": saved["updated_at"]})
    assert update.status_code == 200, update.text
    assert client.put(f"/solutions/{saved['id']}", json={"nodes": edited, "expected_updated_at": saved["updated_at"]}).status_code == 409
    edited[0]["data"]["configuration"]["parameters"]["unsupported"] = 1
    assert client.put(f"/solutions/{saved['id']}", json={"nodes": edited, "expected_updated_at": update.json()["updated_at"]}).status_code == 422
    from app.main import app
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, "other")
        assert client.get(f"/solutions/{saved['id']}").status_code == 403
        assert client.put(f"/solutions/{saved['id']}", json={"name": "forbidden"}).status_code == 403
    app.dependency_overrides.pop(get_current_user)


def test_duplicate_compilation_downstream_and_legacy(configured):
    saved = configured.post("/solutions", json={"name": "Repeated", "nodes": [node("first"), node("second", 43)],
        "edges": [{"id": "edge", "source": "first", "target": "second"}]}).json()
    compiled = configured.post("/workflows/compile", json=workflow(saved))
    assert compiled.status_code == 200, compiled.text
    compiled = compiled.json()
    instances = compiled["solution_studio_metadata"]["execution_instances"]
    assert len({n["task_id"] for n in instances}) == 2
    assert [c["parameters"]["seed"] for c in compiled["task_configurations"].values()] == [42, 43]
    assert instances[1]["input_bindings"] == ["first"]
    assert compiled["blueprint"]["nodes"][0]["operation_signature_list"][0]["connected_to"][0]["container_name"] == instances[1]["node_key"].split(":")[0]
    assert {e["ip_address"] for e in compiled["dockerinfo"]["docker_info_list"]} == {"configureandsynthesize"}
    request = workflow(saved)
    request["nodes"] = request["nodes"][:1]
    request["edges"] = []
    del request["nodes"][0]["configuration"]
    legacy = configured.post("/workflows/compile", json=request).json()
    assert "task_configurations" not in legacy
    assert legacy["blueprint"]["nodes"][0]["container_name"] == "configureandsynthesize"
    for mutation in ("version", "null", "unknown-node"):
        broken = workflow(saved)
        if mutation == "version": broken["nodes"][0]["configuration"]["contract_version"] = "99.0.0"
        if mutation == "null": broken["nodes"][0]["configuration"] = None
        if mutation == "unknown-node": broken["edges"][0]["target"] = "missing"
        assert configured.post("/workflows/compile", json=broken).status_code in (409, 422)


def test_submission_is_durable_and_history_not_reconstructed(configured, monkeypatch):
    import app.main as main
    import app.services.orchestrator_adapter as adapter
    client = configured
    saved = client.post("/solutions", json={"name": "Snapshot", "nodes": [node("one")], "edges": []}).json()
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *args: {"status": "ready"})
    monkeypatch.setattr(adapter, "require_parameter_transport", lambda compiled: {"status": "ready", "fixture": True})
    def submit(payload):
        with SessionLocal() as db:
            row = db.query(ExecutionSubmission).one()
            assert row.phase == "prepared"
            assert next(iter(row.submitted["compiled"]["task_configurations"].values()))["parameters"] == {"seed": 42}
        return {"workflow_id": "wf-123456abcdef", "status": "running"}
    monkeypatch.setattr(main, "submit_to_orchestrator", submit)
    response = client.post("/workflows/submit-to-orchestrator", json=workflow(saved))
    assert response.status_code == 200, response.text
    before = client.get("/workflows/wf-123456abcdef/submitted-configuration").json()
    changed = deepcopy(saved["nodes"])
    changed[0]["data"]["configuration"]["parameters"]["seed"] = 43
    assert client.put(f"/solutions/{saved['id']}", json={"nodes": changed, "expected_updated_at": saved["updated_at"]}).status_code == 200
    assert client.get("/workflows/wf-123456abcdef/submitted-configuration").json() == before
    assert client.get("/workflows/wf-123456abcdef/instance-evidence").json()["state"] == "unavailable"
    assert client.post("/workflows/submit-to-orchestrator", json=workflow(saved)).status_code == 409


def test_ai_proposals_share_registry_validation(configured):
    client = configured
    response = client.post("/design-ai/drafts", json={"template_key": "dutch"})
    assert response.status_code == 200, response.text
    draft = response.json()
    from app.schemas.design_ai import AssistantTurn
    with SessionLocal() as db:
        row = design_ai.load_draft(draft["id"], db, db.get(User, "designer"))
        instance = next(n for n in row.state["design"]["nodes"] if n.get("data", {}).get("service", {}).get("operation_name") == "ConfigureAndSynthesize")
        turn = AssistantTurn(message="Test fixture proposal", template_key=None, expected_revision=0,
            edits=[{"kind": "set_node_parameters", "node_id": instance["id"], "value": json.dumps(configuration(43))}])
        candidate, validation = design_ai.candidate(row, turn, db, db.get(User, "designer"))
        assert validation["valid"]
        assert next(n for n in candidate["nodes"] if n["id"] == instance["id"])["data"]["configuration"]["parameters"] == {"seed": 43}
        turn.edits[0].value = json.dumps(configuration(99))
        with pytest.raises(HTTPException): design_ai.candidate(row, turn, db, db.get(User, "designer"))


def test_evidence_receipt_rejects_rehashed_replacement_and_cross_owner(configured, tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services.execution_submission import prepare
    from app.services.instance_evidence import sha
    client = configured
    saved = client.post("/solutions", json={"name": "Evidence fixture", "nodes": [node("one")], "edges": []}).json()
    with SessionLocal() as db:
        request = WorkflowSubmitRequest.model_validate(workflow(saved))
        compiled = compile_to_wp3_payload(request, db)
        row = prepare(db, db.get(User, "designer"), request, compiled)
        row.workflow_id = "wf-aabbccddeeff"
        db.commit()
        instance = compiled["solution_studio_metadata"]["execution_instances"][0]
        config = instance["configuration"]
        folder = tmp_path / "synth" / row.workflow_id / instance["task_id"]
        folder.mkdir(parents=True)
        raw = json.dumps({"workflow_id": row.workflow_id, "task_id": instance["task_id"], "method": instance["operation_name"],
                          "configuration": config, "inputs": []}).encode()
        output = b'{"grid_data":{"seed":42}}'
        manifest = {"workflow_id": row.workflow_id, "task_id": instance["task_id"], "operation": instance["operation_name"],
            "instance_id": "one", "contract": config, "algorithm_consumed": {"seed": 42}, "wrapper_received": {"seed": 42},
            "request_sha256": sha(raw), "output_sha256": sha(output), "wrapper_sha256": "fixture-only",
            "contracts_sha256": "fixture-only", "instrumentation": "Synthetic fixture, NOT algorithm evidence"}
        (folder / "request.json").write_bytes(raw)
        (folder / "output.json").write_bytes(output)
        (folder / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(settings, "aie18_evidence_root", str(tmp_path))
    endpoint = "/workflows/wf-aabbccddeeff/instance-evidence"
    assert client.get(endpoint).json()["state"] == "available"
    replacement = b'{"grid_data":{"seed":43}}'
    (folder / "output.json").write_bytes(replacement)
    manifest["output_sha256"] = sha(replacement)
    (folder / "manifest.json").write_text(json.dumps(manifest))
    assert client.get(endpoint).json()["state"] == "unavailable"
    from app.main import app
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, "other")
        assert client.get(endpoint).status_code == 403
        assert client.get("/workflows/wf-aabbccddeeff/submitted-configuration").status_code == 403
    app.dependency_overrides.pop(get_current_user)
