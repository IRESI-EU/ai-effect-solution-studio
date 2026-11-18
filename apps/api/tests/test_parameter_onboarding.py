"""Normal authenticated provider -> contract -> independent designer path.

Disposable interface/runtime evidence below is synthetic, not Danish approval.
"""
from copy import deepcopy

import pytest

from app.db import SessionLocal
from app.core.security import hash_password
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.user import User, AuditEvent
from app.services.parameter_discovery import discover
from app.services.workflow_compiler import compile_to_wp3_payload
from app.schemas.workflow_submit import WorkflowSubmitRequest


SCHEMA = {"type": "object", "properties": {
    "iterations": {"type": "integer", "title": "Iterations", "description": "Number of fixture iterations", "default": 2, "minimum": 1, "maximum": 10},
    "enabled": {"type": "boolean", "description": "Enable fixture processing", "default": False},
    "mode": {"type": "string", "description": "Fixture mode", "enum": ["fast", "full"]},
    "dataset_ref": {"type": "string", "default": "not-an-algorithm-setting"},
    "api_key": {"type": "string", "default": "NEVER-RETAIN-THIS-VALUE"},
    "output_path": {"type": "string", "default": "/private/operator"},
    "complex": {"type": "array", "items": {"type": "number"}, "default": [1]},
    "precision": {"type": "number", "multipleOf": 0.1},
}, "required": ["iterations"]}


def login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "DisposableFixture12345"})
    assert response.status_code == 200, response.text


def manifest(service_id="fixture-onboarded"):
    return {"schema_version": "1.0", "service": {"id": service_id, "name": "Provider-owned fixture", "provider": "Test node", "category": "Test"},
            "runtime": {"container_name": "fixture", "internal_host": "fixture", "image": "fixture:local"},
            "interface": {"type": "control", "operation_name": "RunFixture", "input_type": "json", "output_type": "json", "parameter_schema": deepcopy(SCHEMA)}}


@pytest.fixture
def publisher(environment):
    with SessionLocal() as db:
        for uid, role, node in [("provider", "node_manager", "denmark"), ("outsider", "node_manager", "germany"), ("admin", "platform_admin", None)]:
            db.add(User(id=uid, email=f"{uid}@example.test", display_name=uid, role=role, node=node, status="active", password_hash=hash_password("DisposableFixture12345")))
        db.commit()
    login(environment, "provider@example.test")
    result = environment.post("/services/import/confirm-manual", json={"manifest": manifest()})
    assert result.status_code == 200, result.text
    return environment


def state(client):
    response = client.get("/services/fixture-onboarded/parameter-onboarding")
    assert response.status_code == 200, response.text
    return response.json()


def review_payload(client):
    discovery = state(client)["discovery"]
    candidate = next(c for c in discovery["candidates"] if c["name"] == "iterations")
    return {"discovery_revision": discovery["revision"], "operation_identity": "urn:fixture:provider:run", "contract_version": "1.0.0",
            "parameters": [{"name": "iterations", "source_pointer": candidate["source_pointer"], "definition": candidate["definition"], "algorithm_mapping": "Fixture uses configuration.parameters.iterations"}],
            "runtime_support_confirmed": True, "normal_configuration_tested": True, "invalid_configuration_tested": True,
            "evidence_reference": "Synthetic test fixture only; not node approval"}


def review(client, payload=None):
    response = client.post("/services/fixture-onboarded/parameter-onboarding/review", json=payload or review_payload(client))
    assert response.status_code == 201, response.text
    return response.json()


def approve(client):
    login(client, "admin@example.test")
    assert client.post("/services/fixture-onboarded/review/approve").status_code == 200
    login(client, "provider@example.test")


def test_discovery_excludes_secrets_data_operator_and_unsupported_constraints():
    result = discover(SCHEMA, "schema@revision", "RunFixture")
    candidates = {c["name"]: c for c in result["candidates"]}
    assert candidates["iterations"]["definition"]["default"] == 2
    assert candidates["enabled"]["definition"]["default"] is False
    assert "default" not in candidates["mode"]["definition"]
    assert candidates["api_key"]["classification"] == "secret"
    assert candidates["dataset_ref"]["classification"] == "data_input"
    assert candidates["output_path"]["classification"] == "operator"
    assert not candidates["complex"]["supported"] and not candidates["precision"]["supported"]
    assert "NEVER-RETAIN" not in str(result) and "/private/operator" not in str(result)
    assert "default" not in candidates["complex"]["definition"]


def test_openapi_selects_real_operation_resolves_local_refs_without_network():
    document = {"openapi": "3.1.0", "paths": {"/run": {"post": {"operationId": "actual-run", "requestBody": {
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Request"}}}}}}},
        "components": {"schemas": {"Request": {"type": "object", "properties": {"parameters": SCHEMA}}}}}
    result = discover(document, "openapi@commit", "RunFixture", "actual-run")
    assert result["candidates"][0]["source_pointer"] == "#/components/schemas/Request/properties/parameters/properties/iterations"
    with pytest.raises(ValueError, match="unique"):
        discover(document, "source", "invented-operation")
    document["components"]["schemas"]["Request"] = {"$ref": "https://never-fetch.example/schema"}
    with pytest.raises(ValueError, match="local"):
        discover(document, "source", "RunFixture", "actual-run")


def test_control_configuration_envelope_and_unknown_relations_are_not_flattened():
    document = {"type": "object", "properties": {"configuration": {"type": "object", "properties": {"parameters": SCHEMA}}, "inputs": {"type": "array"}}}
    result = discover(document, "control schema", "RunFixture")
    assert result["candidates"][0]["source_pointer"] == "#/properties/configuration/properties/parameters/properties/iterations"
    related = {**SCHEMA, "dependentRequired": {"iterations": ["enabled"]}}
    assert not any(c["supported"] for c in discover(related, "source", "RunFixture")["candidates"])


def test_provider_registration_review_governance_and_existing_designer_path(publisher):
    client = publisher
    data = state(client)
    assert data["service_status"] == "pending_review" and data["discovery"]["status"] == "awaiting_provider_review"
    contract = review(client)
    assert contract["status"] == "draft"
    assert client.get("/services/fixture-onboarded/operation-contract-resolution").json()["contract"] is None
    assert client.post(f"/operation-contracts/{contract['id']}/activate").status_code == 409
    approve(client)
    assert client.post(f"/operation-contracts/{contract['id']}/activate").status_code == 200
    resolved = client.get("/services/fixture-onboarded/operation-contract-resolution").json()["contract"]
    assert resolved["id"] == contract["id"] and "iterations" in resolved["definition"]["execution_parameters"]["properties"]
    # The independently seeded ordinary designer uses normal login, no auth override.
    assert client.post("/auth/login", json={"email": "designer@example.test", "password": "PilotTest12345"}).status_code == 200
    nodes = [{"id": f"instance-{i}", "position": {"x": i * 200, "y": 0}, "data": {"node_kind": "service", "service": {"id": "fixture-onboarded"},
        "configuration": {"contract_id": contract["id"], "contract_version": "1.0.0", "parameters": {"iterations": value}}}} for i, value in enumerate([2, 4])]
    saved = client.post("/solutions", json={"name": "Independent instances", "nodes": nodes, "edges": []})
    assert saved.status_code == 200, saved.text
    solution = client.get(f"/solutions/{saved.json()['id']}").json()
    assert [n["data"]["configuration"]["parameters"]["iterations"] for n in solution["nodes"]] == [2, 4]
    request = WorkflowSubmitRequest(name=solution["name"], nodes=[{"node_id": n["id"], "service_id": "fixture-onboarded", "container_name": "ignored",
                    "operation_name": "RunFixture", "configuration": n["data"]["configuration"]} for n in nodes], edges=[])
    with SessionLocal() as db:
        compiled = compile_to_wp3_payload(request, db)
        assert [value["parameters"]["iterations"] for value in compiled["task_configurations"].values()] == [2, 4]
        assert db.query(AuditEvent).filter(AuditEvent.action == "service.parameters_reviewed").count() == 1
    # Compilation is not runtime-consumption evidence.


def test_normal_discovery_endpoint_requires_auth_and_node_ownership(publisher):
    client = publisher
    payload = {"document": SCHEMA, "source_reference": "fixture"}
    login(client, "outsider@example.test")
    for method, path, body in [("get", "", None), ("post", "/discover", payload), ("post", "/review", review_payload_forbidden())]:
        response = getattr(client, method)("/services/fixture-onboarded/parameter-onboarding" + path, **({"json": body} if body else {}))
        assert response.status_code == 403
    client.cookies.clear()
    assert client.post("/services/fixture-onboarded/parameter-onboarding/discover", json=payload).status_code == 401


def review_payload_forbidden():
    return {"discovery_revision": "stale", "operation_identity": "urn:fixture:run", "contract_version": "1.0.0", "parameters": [{"name": "iterations", "source_pointer": "#/properties/iterations", "definition": {"type": "integer", "title": "Iterations", "description": "Fixture"}, "algorithm_mapping": "Fixture"}],
            "runtime_support_confirmed": True, "normal_configuration_tested": True, "invalid_configuration_tested": True, "evidence_reference": "Fixture"}


@pytest.mark.parametrize("mutation", ["stale", "secret", "runtime", "invalid", "bounds", "mapping", "duplicate"])
def test_invalid_or_unconfirmed_review_does_not_create_contract(publisher, mutation):
    payload = review_payload(publisher)
    parameter = payload["parameters"][0]
    if mutation == "stale": payload["discovery_revision"] = "old"
    if mutation == "secret": parameter["name"] = "api_key"; parameter["source_pointer"] = "#/properties/api_key"
    if mutation == "runtime": payload["runtime_support_confirmed"] = False
    if mutation == "invalid": payload["invalid_configuration_tested"] = False
    if mutation == "bounds": parameter["definition"]["maximum"] = 0
    if mutation == "mapping": parameter["algorithm_mapping"] = " "
    if mutation == "duplicate": payload["parameters"].append(deepcopy(parameter))
    response = publisher.post("/services/fixture-onboarded/parameter-onboarding/review", json=payload)
    assert response.status_code in {409, 422}, response.text
    assert publisher.get("/services/fixture-onboarded/operation-contracts").json() == []


def test_rediscovery_invalidates_pending_review_but_preserves_published_contract(publisher):
    payload = review_payload(publisher)
    contract = review(publisher, payload)
    approve(publisher)
    assert publisher.post(f"/operation-contracts/{contract['id']}/activate").status_code == 200
    assert publisher.post("/services/fixture-onboarded/parameter-onboarding/discover", json={"document": SCHEMA, "source_reference": "new revision"}).status_code == 200
    payload["contract_version"] = "1.1.0"
    assert publisher.post("/services/fixture-onboarded/parameter-onboarding/review", json=payload).status_code == 409
    assert publisher.get("/services/fixture-onboarded/operation-contract-resolution").json()["contract"]["id"] == contract["id"]


def test_editing_reviewed_draft_requires_new_review_before_activation(publisher):
    contract = review(publisher)
    approve(publisher)
    update = {key: contract[key] for key in ["operation_identity", "runtime_operation_name", "contract_version", "schema_version", "source_kind", "source_reference", "definition"]}
    update["definition"]["execution_parameters"]["properties"]["iterations"]["maximum"] = 20
    assert publisher.put(f"/operation-contracts/{contract['id']}", json=update).status_code == 200
    assert publisher.post(f"/operation-contracts/{contract['id']}/activate").status_code == 409


def test_runtime_metadata_drift_requires_new_provider_review(publisher):
    contract = review(publisher)
    approve(publisher)
    with SessionLocal() as db:
        service = db.get(Service, "fixture-onboarded")
        service.image = "fixture:changed-runtime"
        db.commit()
    assert publisher.post(f"/operation-contracts/{contract['id']}/activate").status_code == 409


def test_review_and_provenance_are_one_transaction(publisher, monkeypatch):
    from app.routers import parameter_onboarding
    payload = review_payload(publisher)
    def fail_audit(*args, **kwargs):
        raise RuntimeError("Synthetic audit-write failure")
    monkeypatch.setattr(parameter_onboarding, "record_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit-write"):
        publisher.post("/services/fixture-onboarded/parameter-onboarding/review", json=payload)
    assert publisher.get("/services/fixture-onboarded/operation-contracts").json() == []
    assert state(publisher)["reviews"] == {}


def test_independent_service_uses_identical_onboarding_without_registered_ids(publisher):
    other = manifest("independently-onboarded-second-fixture")
    other["interface"]["operation_name"] = "AnotherOperation"
    other["interface"]["parameter_schema"] = {"type": "object", "properties": {
        "duration": {"type": "number", "title": "Duration", "description": "Synthetic fixture duration", "x-unit": "s", "minimum": 0.5, "default": 1.5}}}
    assert publisher.post("/services/import/confirm-manual", json={"manifest": other}).status_code == 200
    base = "/services/independently-onboarded-second-fixture"
    discovery = publisher.get(base + "/parameter-onboarding").json()["discovery"]
    candidate = discovery["candidates"][0]
    payload = {**review_payload(publisher), "discovery_revision": discovery["revision"], "operation_identity": "urn:fixture:second:operation",
               "parameters": [{"name": "duration", "source_pointer": candidate["source_pointer"], "definition": candidate["definition"], "algorithm_mapping": "Synthetic fixture duration argument"}]}
    response = publisher.post(base + "/parameter-onboarding/review", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["runtime_operation_name"] == "AnotherOperation"
    assert response.json()["definition"]["execution_parameters"]["properties"]["duration"]["unit"] == "s"


def test_new_review_preserves_existing_operation_slots_and_history(publisher):
    contract = review(publisher)
    approve(publisher)
    assert publisher.post(f"/operation-contracts/{contract['id']}/activate").status_code == 200
    with SessionLocal() as db:
        row = db.get(OperationContract, contract["id"])
        row.definition = {**row.definition, "compatibility_notes": ["Preserve the provider's existing operation semantics"]}
        db.commit()
    payload = review_payload(publisher); payload["contract_version"] = "1.1.0"
    new = review(publisher, payload)
    assert new["definition"]["compatibility_notes"] == ["Preserve the provider's existing operation semantics"]
    assert publisher.get("/services/fixture-onboarded/operation-contract-resolution").json()["contract"]["id"] == contract["id"]
