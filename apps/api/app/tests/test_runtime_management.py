import socket
from uuid import uuid4

import requests

from app.models.service import Service
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.workflow_compiler import compile_to_wp3_payload


def add_service(session_factory, *, service_id: str, owner_node: str = "germany", status: str = "pending_review"):
    with session_factory() as db:
        db.add(
            Service(
                id=service_id,
                name=f"Runtime test {service_id}",
                provider="German Node",
                category="Test",
                description="Runtime management regression",
                input_type="Workflow Start",
                output_type="Next Input",
                status=status,
                trust_badge="validated" if status == "approved" else "pending_review",
                lifecycle_status="active",
                container_name="logical-service",
                internal_host="old-runtime",
                internal_port="8080",
                health_path="/health",
                image="example/runtime:1",
                proto_uri="microservice/runtime.proto",
                contract_uri="contracts/runtime.proto",
                operation_name="RunRuntime",
                input_message_name="RunRuntimeRequest",
                output_message_name="RunRuntimeResponse",
                interface_type="control",
                orchestration_mode="native",
                owner_node=owner_node,
            )
        )
        db.commit()


def technical_payload(**overrides):
    payload = {
        "internal_host": "network-runtime",
        "internal_port": "8080",
        "health_path": "/health",
        "operation_name": "RunRuntime",
        "input_message_name": "RunRuntimeRequest",
        "output_message_name": "RunRuntimeResponse",
        "contract_uri": "contracts/runtime.proto",
        "proto_uri": "microservice/runtime.proto",
    }
    payload.update(overrides)
    return payload


def test_authorized_edit_preserves_logical_identity_and_compiler_address(client, session_factory):
    service_id = f"runtime-edit-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id)

    response = client.put(f"/services/{service_id}/technical-metadata", json=technical_payload())
    assert response.status_code == 200
    service = response.json()
    assert service["container_name"] == "logical-service"
    assert service["internal_host"] == "network-runtime"
    assert service["interface_contract"]["runtime_verification"]["status"] == "not_verified"

    with session_factory() as db:
        workflow = WorkflowSubmitRequest(
            name="compile-only",
            nodes=[{"node_id": "one", "service_id": service_id, "container_name": "ignored", "operation_name": "ignored"}],
            edges=[],
        )
        compiled = compile_to_wp3_payload(workflow, db)
    assert compiled["blueprint"]["nodes"][0]["container_name"] == "logical-service"
    assert compiled["dockerinfo"]["docker_info_list"][0]["ip_address"] == "network-runtime"


def test_runtime_edit_requires_authentication(anonymous_client, session_factory):
    service_id = f"runtime-unauthorized-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id)
    response = anonymous_client.put(f"/services/{service_id}/technical-metadata", json=technical_payload())
    assert response.status_code == 401


def test_node_manager_cannot_edit_another_nodes_runtime(client, anonymous_client, session_factory):
    service_id = f"runtime-other-node-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id, owner_node="germany")
    email = f"pt-runtime-{uuid4().hex[:8]}@example.org"
    registration = anonymous_client.post(
        "/auth/register",
        json={
            "display_name": "Portuguese Runtime Manager",
            "email": email,
            "password": "RuntimeManagerPassword123",
            "requested_role": "node_manager",
            "node": "portugal",
        },
    )
    assert registration.status_code == 201
    approval = client.post(
        f"/admin/users/{registration.json()['id']}/approve",
        json={"role": "node_manager", "node": "portugal"},
    )
    assert approval.status_code == 200
    assert anonymous_client.post(
        "/auth/login", json={"email": email, "password": "RuntimeManagerPassword123"}
    ).status_code == 200
    response = anonymous_client.put(
        f"/services/{service_id}/technical-metadata", json=technical_payload()
    )
    assert response.status_code == 403


def test_invalid_runtime_address_is_rejected(client, session_factory):
    service_id = f"runtime-invalid-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id)
    response = client.put(
        f"/services/{service_id}/technical-metadata",
        json=technical_payload(internal_host="http://bad-host/path"),
    )
    assert response.status_code == 422
    assert "malformed internal host" in response.json()["detail"]


def test_verification_reports_dns_failure_and_approval_is_not_false_readiness(
    client, session_factory, monkeypatch
):
    service_id = f"runtime-dns-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id)

    def fail_dns(*_args, **_kwargs):
        try:
            raise socket.gaierror(-2, "Name or service not known")
        except socket.gaierror as exc:
            raise requests.ConnectionError("resolution failed") from exc

    monkeypatch.setattr("app.services.runtime_preflight.requests.get", fail_dns)
    approved = client.post(f"/services/{service_id}/review/approve")
    assert approved.status_code == 200
    payload = approved.json()
    assert payload["status"] == "approved"
    assert payload["interface_contract"]["runtime_verification"]["status"] == "failed"
    assert payload["interface_contract"]["runtime_verification"]["failure_reason"] == "dns_failure"

    verified = client.post(f"/services/{service_id}/runtime/verify")
    assert verified.status_code == 200
    assert verified.json()["status"] == "failed"
    assert verified.json()["failure_reason"] == "dns_failure"

    preflight = client.post(
        "/workflows/runtime-preflight",
        json={
            "name": "blocked",
            "nodes": [{"node_id": "one", "service_id": service_id, "container_name": "logical-service", "operation_name": "RunRuntime"}],
            "edges": [],
        },
    )
    assert preflight.status_code == 200
    assert preflight.json()["status"] == "blocked"
    assert preflight.json()["checks"][0]["failure_reason"] == "dns_failure"


def test_successful_verification_records_connectivity_not_contract_certification(
    client, session_factory, monkeypatch
):
    service_id = f"runtime-ready-{uuid4().hex[:8]}"
    add_service(session_factory, service_id=service_id, status="approved")

    class Response:
        status_code = 204

    monkeypatch.setattr("app.services.runtime_preflight.requests.get", lambda *_args, **_kwargs: Response())
    response = client.post(f"/services/{service_id}/runtime/verify")
    assert response.status_code == 200
    assert response.json()["status"] == "verified"
    assert response.json()["http_status"] == 204
