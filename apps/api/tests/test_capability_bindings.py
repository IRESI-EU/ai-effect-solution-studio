"""Contract/binding fixtures; no real workflow execution or provider call."""
from copy import deepcopy
import pytest
import requests
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.schemas.operation_contract import OperationContractDefinition
from app.services import capability_readiness

SLOT = {"name": "grid", "semantic_concept": "urn:test:synthetic-grid",
        "schema_ref": "urn:test:captured-grid:1", "value_representation": "data_reference",
        "data_reference_protocols": ["file"], "content_types": ["application/json"],
        "min_cardinality": 1, "max_cardinality": 1}


@pytest.fixture
def bound(environment):
    with SessionLocal() as db:
        for name, operation, role in [("source", "ConfigureAndSynthesize", "source"), ("sink", "RunBenchmark", "analyzer")]:
            definition = {"operation_role": role, "binding_transport": "whole-output-v1",
                "inputs": [{**SLOT, "required": True, "source_requirement": "upstream_operation"}] if name == "sink" else [],
                "outputs": [SLOT] if name == "source" else []}
            db.add(OperationContract(id=name, service_id=f"dutch-{operation}", status="active",
                operation_identity=f"urn:test:{name}", runtime_operation_name=operation, contract_version="1.0.0",
                schema_version="1.0", source_kind="manual", definition=definition))
        db.commit()
    nodes = [{"id": name, "data": {"service": {"id": f"dutch-{operation}"}, "operation_contract": {
        "contract_id": name, "contract_version": "1.0.0"}}} for name, operation in [
            ("source", "ConfigureAndSynthesize"), ("sink", "RunBenchmark")]]
    edges = [{"id": "link", "source": "source", "target": "sink", "data": {
        "binding": {"source_slot": "grid", "target_slot": "grid"}}}]
    return environment, {"name": "Qualified fixture", "nodes": nodes, "edges": edges}


def workflow(saved):
    return {"name": saved["name"], "solution_id": saved["id"], "expected_updated_at": saved["updated_at"],
            "nodes": [{"node_id": n["id"], "container_name": "ignored", "operation_name": "ignored",
                       "service_id": n["data"]["service"]["id"], "operation_contract": n["data"]["operation_contract"]}
                      for n in saved["nodes"]],
            "edges": [{"source": e["source"], "target": e["target"], "binding": e["data"]["binding"]} for e in saved["edges"]]}


def test_save_reload_compile_preserves_named_bindings_and_provenance(bound):
    client, payload = bound
    response = client.post("/solutions", json=payload)
    assert response.status_code == 200, response.text
    saved = client.get("/solutions/" + response.json()["id"]).json()
    assert saved["edges"] == payload["edges"]
    compiled = client.post("/workflows/compile", json=workflow(saved))
    assert compiled.status_code == 200, compiled.text
    report = compiled.json()["solution_studio_metadata"]["capability_bindings"]
    assert report["status"] == "verified"
    assert report["bindings"][0]["source_slot"] == report["bindings"][0]["target_slot"] == "grid"
    assert report["contracts"]["sink"]["definition_sha256"]
    assert compiled.json()["blueprint"]["nodes"][0]["operation_signature_list"][0]["connected_to"][0]["container_name"] == "runbenchmark"


@pytest.mark.parametrize("field,value", [
    ("schema_ref", "urn:test:captured-grid:2"), ("semantic_concept", "urn:test:other-grid"),
    ("value_representation", "structured_object"), ("content_types", ["image/svg+xml"]),
    ("data_reference_protocols", ["http"]), ("max_cardinality", 2), ("schema_ref", None)])
def test_json_labels_are_insufficient_and_unknown_schema_rejected(bound, field, value):
    client, payload = bound
    with SessionLocal() as db:
        contract = db.get(OperationContract, "source")
        definition = deepcopy(contract.definition)
        definition["outputs"][0][field] = value
        contract.definition = definition
        db.commit()
    response = client.post("/solutions", json=payload)
    assert response.status_code == 422, response.text
    assert "Incompatible connection" in response.text


@pytest.mark.parametrize("mutation", ["slot", "missing-pin", "stale-version", "no-binding", "required", "duplicate", "cycle", "null-pin"])
def test_unresolved_or_ambiguous_bindings_rejected(bound, mutation):
    client, original = bound
    payload = deepcopy(original)
    if mutation == "slot": payload["edges"][0]["data"]["binding"]["source_slot"] = "unknown"
    if mutation == "missing-pin": del payload["nodes"][0]["data"]["operation_contract"]
    if mutation == "stale-version": payload["nodes"][0]["data"]["operation_contract"]["contract_version"] = "9.0.0"
    if mutation == "no-binding": payload["edges"][0]["data"] = {}
    if mutation == "required": payload["edges"] = []
    if mutation == "duplicate": payload["edges"].append(deepcopy(payload["edges"][0]))
    if mutation == "cycle": payload["edges"][0]["target"] = "source"
    if mutation == "null-pin": payload["nodes"][0]["data"]["operation_contract"] = None
    assert client.post("/solutions", json=payload).status_code in (409, 422)


def test_optional_input_can_be_absent_and_workflow_data_is_not_a_parameter(bound):
    client, payload = bound
    with SessionLocal() as db:
        contract = db.get(OperationContract, "sink")
        definition = deepcopy(contract.definition)
        definition["inputs"][0].update(required=False, min_cardinality=0)
        contract.definition = definition
        db.commit()
    payload["edges"] = []
    saved = client.post("/solutions", json=payload)
    assert saved.status_code == 200, saved.text
    request = workflow(saved.json())
    request["run_input"] = {"seed": 43}
    assert client.post("/workflows/compile", json=request).status_code == 422


def test_unknown_contract_cannot_be_bypassed_by_omitting_pin(bound):
    client, payload = bound
    del payload["nodes"][0]["data"]["operation_contract"]
    assert client.post("/solutions", json=payload).status_code == 409


def test_submission_revision_binding_equality_and_history(bound, monkeypatch):
    client, payload = bound
    saved = client.post("/solutions", json=payload).json()
    import app.main as main
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *a: {"status": "ready"})
    monkeypatch.setattr(main, "require_binding_transport", lambda *a: {"status": "ready", "fixture": True})
    monkeypatch.setattr(main, "submit_to_orchestrator", lambda *a: {"workflow_id": "wf-abcdefabcdef", "status": "submitted"})
    from app.services import orchestrator_adapter
    monkeypatch.setattr(orchestrator_adapter, "require_parameter_transport", lambda *a: {"status": "ready", "fixture": True})
    request = workflow(saved)
    changed = deepcopy(request)
    changed["edges"][0]["binding"]["source_slot"] = "other"
    assert client.post("/workflows/submit-to-orchestrator", json=changed).status_code == 409
    assert client.post("/workflows/submit-to-orchestrator", json=request).status_code == 200
    before = client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json()
    assert client.put("/solutions/" + saved["id"], json={"name": "Later draft", "expected_updated_at": saved["updated_at"]}).status_code == 200
    assert client.get("/workflows/wf-abcdefabcdef/submitted-configuration").json() == before
    assert client.post("/workflows/submit-to-orchestrator", json=request).status_code == 409


@pytest.mark.parametrize("failure", ["timeout", "unavailable", "version", "schema", "malformed", "redirect"])
def test_actual_network_capability_mismatch_blocks_without_submission(bound, monkeypatch, failure):
    client, payload = bound
    saved = client.post("/solutions", json=payload).json()
    compiled = client.post("/workflows/compile", json=workflow(saved)).json()
    contracts = compiled["solution_studio_metadata"]["capability_bindings"]["contracts"]
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        if failure == "timeout": raise requests.Timeout()
        contract = contracts["source" if "configureandsynthesize" in url else "sink"]
        operation = {**contract, "operation_name": contract["runtime_operation_name"], "binding_transport": "whole-output-v1",
                     "io_contract_sha256": contract["definition_sha256"]}
        if failure == "version": operation["contract_version"] = "2.0.0"
        if failure == "schema": operation["io_contract_sha256"] = "0" * 64
        class Response:
            status_code = 302 if failure == "redirect" else 200
            def raise_for_status(self):
                if failure == "unavailable": raise requests.HTTPError()
            def json(self): return [] if failure == "malformed" else {"capability_schema_version": "1.0", "operations": [operation]}
        return Response()
    monkeypatch.setattr(capability_readiness.requests, "get", get)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error: capability_readiness.require_binding_transport(compiled)
    assert error.value.status_code == 409
    assert calls[0][1]["timeout"] == 5
    assert calls[0][1]["allow_redirects"] is False


def test_malformed_connection_data_is_actionable(bound):
    client, payload = bound
    payload["edges"][0]["data"] = None
    response = client.post("/solutions", json=payload)
    assert response.status_code == 422
    assert "Connection data must be a JSON object" in response.text
