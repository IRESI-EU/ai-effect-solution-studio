"""OFFLINE admission tests. All dispatch/authority endpoints are doubles.

SQLite checks do not establish the PostgreSQL reviewer-row lock's concurrency.
"""
from copy import deepcopy
import pytest
from app.core.config import settings
from app.db import SessionLocal
from app.models.execution_submission import ExecutionSubmission
from app.models.deployment import Deployment
from test_portuguese_chain import chained, workflow, training_profile


@pytest.fixture
def supervised(chained, monkeypatch):
    client, payload = chained
    training_profile(monkeypatch)
    monkeypatch.setattr(settings, "portuguese_supervised_mode", True)
    monkeypatch.setattr(settings, "portuguese_supervised_authorization_id", "offline-one-attempt")
    from app import main
    from app.services import portuguese_supervision as gate, orchestrator_adapter
    calls = []
    def boundary(action, value):
        calls.append(action)
        request = value["request"] if action == "bind" else value
        return {k: request[k] for k in ("authorization_id", "owner_id", "request_sha256")} | {
            "status": "bound" if action == "bind" else "ready", "policy_sha256": "a" * 64,
            **({"workflow_id": value["workflow_id"]} if action == "bind" else {})}
    monkeypatch.setattr(gate, "boundary", boundary)
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *a: {"status": "ready", "checks": []})
    monkeypatch.setattr(main, "require_binding_transport", lambda *a: {"status": "ready"})
    monkeypatch.setattr(orchestrator_adapter, "require_parameter_transport", lambda *a: {"status": "ready"})
    def dispatch(*a):
        calls.append("dispatch")
        return {"workflow_id": "wf-eeeeeeeeeeee", "status": "running"}
    monkeypatch.setattr(main, "submit_to_orchestrator", dispatch)
    saved = client.post("/solutions", json=payload).json()
    return client, workflow(saved), calls


def test_readiness_is_readonly_and_confirmation_dispatches_once(supervised):
    client, body, calls = supervised
    response = client.post("/workflows/runtime-preflight", json=body)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).count() == 0
    assert calls == ["check"]
    first = client.post("/workflows/submit-to-orchestrator", json=body)
    assert first.status_code == 200, first.text
    second = client.post("/workflows/submit-to-orchestrator", json=body)
    assert second.status_code == 200 and second.json()["replayed"]
    assert first.json()["workflow_id"] == second.json()["workflow_id"]
    assert calls.count("dispatch") == calls.count("bind") == 1
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).count() == db.query(Deployment).count() == 1


@pytest.mark.parametrize("reason", ["closed authority", "stopped processor", "expired lease", "authorization journal unavailable"])
def test_unavailable_boundary_denies_before_enqueue(supervised, monkeypatch, reason):
    client, body, calls = supervised
    from fastapi import HTTPException
    from app.services import portuguese_supervision as gate
    def denied(*a): raise HTTPException(409, reason)
    monkeypatch.setattr(gate, "boundary", denied)
    for path in ("runtime-preflight", "submit-to-orchestrator"):
        assert client.post("/workflows/" + path, json=body).status_code == 409
    assert "dispatch" not in calls
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count() == 0


@pytest.mark.parametrize("mutation", ["settings", "input", "binding", "pins", "revision"])
def test_drift_fails_before_dispatch(supervised, mutation):
    client, original, calls = supervised
    body = deepcopy(original)
    if mutation == "settings": body["nodes"][0]["configuration"]["parameters"]["epochs"] = 100
    if mutation == "input": body["run_input"] = {"dataset_ref": "unauthorized"}
    if mutation == "binding": body["edges"][0]["binding"]["target_slot"] = "other"
    if mutation == "pins": body["nodes"][0]["operation_contract"]["contract_version"] = "0.3.0"
    if mutation == "revision": body["expected_updated_at"] = "old"
    assert client.post("/workflows/submit-to-orchestrator", json=body).status_code == 409
    assert "dispatch" not in calls


def test_failed_or_lost_dispatch_is_not_retried(supervised, monkeypatch):
    client, body, calls = supervised
    from app import main
    def uncertain(*a):
        calls.append("dispatch")
        raise RuntimeError("Connection lost after possible acceptance")
    monkeypatch.setattr(main, "submit_to_orchestrator", uncertain)
    for _ in range(2): assert client.post("/workflows/submit-to-orchestrator", json=body).status_code == 409
    assert calls.count("dispatch") == 1
    with SessionLocal() as db: assert db.query(ExecutionSubmission).one().phase == "submission_unknown"


def test_processor_loss_after_acceptance_keeps_identity_without_redispatch(supervised, monkeypatch):
    client, body, calls = supervised
    from app.services import portuguese_supervision as gate
    from fastapi import HTTPException
    original = gate.boundary
    def lost(action, value):
        if action == "bind": raise HTTPException(409, "Processor disappeared")
        return original(action, value)
    monkeypatch.setattr(gate, "boundary", lost)
    for _ in range(2): assert client.post("/workflows/submit-to-orchestrator", json=body).status_code == 409
    assert calls.count("dispatch") == 1
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).one().workflow_id == "wf-eeeeeeeeeeee"
        assert db.query(Deployment).one().status == "submitted"


def test_other_reviewer_cannot_submit(supervised):
    client, body, calls = supervised
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.models.user import User
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, "other")
        try: assert client.post("/workflows/submit-to-orchestrator", json=body).status_code == 403
        finally: app.dependency_overrides.pop(get_current_user)
    assert not calls


def test_transport_fails_closed_and_never_follows_redirects(environment, monkeypatch):
    from app.services import portuguese_supervision as gate
    from fastapi import HTTPException
    monkeypatch.setattr(settings, "portuguese_supervised_mode", True)
    monkeypatch.setattr(settings, "portuguese_supervised_authorization_id", "test")
    monkeypatch.setattr(settings, "portuguese_supervised_adapter_url", "http://pt-adapter:8080")
    monkeypatch.setattr(settings, "orchestrator_services_api_key", "private-test")
    seen = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, **kw):
            seen.append((self.trust_env, kw["allow_redirects"]))
            class Response: status_code = 302
            return Response()
    monkeypatch.setattr(gate.requests, "Session", Session)
    with pytest.raises(HTTPException): gate.boundary("check", {})
    assert seen == [(False, False)]
