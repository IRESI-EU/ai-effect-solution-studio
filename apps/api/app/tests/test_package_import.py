import io
import json
import zipfile
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import AuditEvent, User, UserSession
from app.services.package_solution_repair import repair_legacy_package_solution
from app.services.solution_design import count_service_nodes


@pytest.fixture(autouse=True)
def clean_package_records(session_factory):
    yield
    with session_factory() as db:
        db.query(Solution).filter(Solution.name == "Imported German draft").delete(synchronize_session=False)
        db.query(Service).filter(Service.id.like("pkg-%")).delete(synchronize_session=False)
        db.commit()


def package_bytes(*, enclosing=False, two_operations=False, unsafe=False, connected=True):
    prefix = "germany/" if enclosing else ""
    blueprint = {
        "type": "pipeline-topology/v2", "name": "German package", "nodes": [
            {
                "container_name": "data_provider1", "image": "provider:1.2.3",
                "node_type": "DataSource", "proto_uri": "microservice/data_provider1.proto",
                "operation_signature_list": [{
                    "operation_signature": {"operation_name": "ProvideData", "input_message_name": "ProvideDataRequest", "output_message_name": "ProvideDataResponse"},
                    "connected_to": ([{"container_name": "formatter1", "operation_signature": {"operation_name": "FormatOutput"}}] if connected else []),
                }] + ([{
                    "operation_signature": {"operation_name": "ProvideOther", "input_message_name": "ProvideDataRequest", "output_message_name": "ProvideDataResponse"},
                    "connected_to": [],
                }] if two_operations else []),
            },
            {
                "container_name": "formatter1", "image": "formatter:2.0", "node_type": "DataSink",
                "proto_uri": "microservice/formatter1.proto",
                "operation_signature_list": [{"operation_signature": {"operation_name": "FormatOutput", "input_message_name": "ProvideDataResponse", "output_message_name": "FormatOutputResponse"}, "connected_to": []}],
            },
        ]
    }
    dockerinfo = {"docker_info_list": [
        {"container_name": "data_provider1", "ip_address": "data-provider", "port": "8080"},
        {"container_name": "formatter1", "ip_address": "output-formatter", "port": "8080"},
    ]}
    provider_proto = 'syntax = "proto3"; service P { rpc ProvideData(ProvideDataRequest) returns (ProvideDataResponse); rpc ProvideOther(ProvideDataRequest) returns (ProvideDataResponse); } message ProvideDataRequest {} message ProvideDataResponse {}'
    formatter_proto = 'syntax = "proto3"; service F { rpc FormatOutput(ProvideDataResponse) returns (FormatOutputResponse); } message ProvideDataResponse {} message FormatOutputResponse {}'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(prefix + "blueprint.json", json.dumps(blueprint))
        archive.writestr(prefix + "dockerinfo.json", json.dumps(dockerinfo))
        archive.writestr(prefix + "microservice/data_provider1.proto", provider_proto)
        archive.writestr(prefix + "microservice/formatter1.proto", formatter_proto)
        if unsafe:
            archive.writestr("../escape.txt", "blocked")
    return buffer.getvalue()


def upload(client, content):
    return client.post("/services/import/package/preview", files={"file": ("germany.zip", content, "application/zip")})


def selections(preview, *, select_formatter=True):
    result = []
    for service in preview["services"]:
        result.append({
            "key": service["key"], "selected": select_formatter or service["key"] != "formatter1",
            "service_id": service["proposed_id"], "name": service["name"],
            "description": service["description"], "category": service["category"],
            "operation_name": service["operations"][0]["operation_name"],
            "internal_host": service["internal_host"], "internal_port": service["internal_port"],
            "health_path": "/health",
        })
    return result


def test_package_preview_and_atomic_confirmation_preserve_runtime_contracts(client, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "service_contract_path", str(tmp_path / "contracts"))
    preview_response = upload(client, package_bytes(enclosing=True))
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert len(preview["services"]) == 2
    provider = preview["services"][0]
    assert provider["container_name"] == "data_provider1"
    assert provider["internal_host"] == "data-provider"
    assert provider["operations"][0]["input_message_name"] == "ProvideDataRequest"
    assert provider["operations"][0]["compatible_with_proto"] is True

    confirmed = client.post("/services/import/package/confirm", json={
        "upload_token": preview["upload_token"], "services": selections(preview),
        "create_solution": True, "solution_name": "Imported German draft",
        "registration_only_acknowledged": True,
    })
    assert confirmed.status_code == 200, confirmed.text
    result = confirmed.json()
    assert len(result["services"]) == 2
    assert result["solution"]["status"] == "draft"
    with session_factory() as db:
        provider_record = db.get(Service, provider["proposed_id"])
        assert provider_record.container_name == "data_provider1"
        assert provider_record.internal_host == "data-provider"
        assert provider_record.operation_name == "ProvideData"
        assert provider_record.input_message_name == "ProvideDataRequest"
        assert provider_record.status == "pending_review"
        assert Path(provider_record.proto_uri).read_text().startswith('syntax = "proto3"')
        solution = db.query(Solution).filter(Solution.name == "Imported German draft").one()
        assert count_service_nodes(solution.nodes) == 2
        assert all(node.get("position") for node in solution.nodes)
        service_nodes = [node for node in solution.nodes if (node.get("data") or {}).get("node_kind") == "service"]
        assert [node["data"]["service"]["id"] for node in service_nodes] == [
            provider["proposed_id"], preview["services"][1]["proposed_id"]
        ]
        assert len({edge["id"] for edge in solution.edges}) == 3
        assert sum((edge.get("data") or {}).get("connection_kind") == "service_connection" for edge in solution.edges) == 1
        assert sum((edge.get("data") or {}).get("connection_kind") == "workflow_boundary" for edge in solution.edges) == 2

        provider_record.name = "Current provider name"
        db.commit()

    reopened = client.get(f"/solutions/{result['solution']['id']}")
    assert reopened.status_code == 200
    saved = reopened.json()
    assert count_service_nodes(saved["nodes"]) == 2
    assert next(node for node in saved["nodes"] if (node.get("data") or {}).get("node_kind") == "service")["data"]["service"]["name"] == "Current provider name"
    saved_again = client.put(f"/solutions/{result['solution']['id']}", json={"nodes": saved["nodes"], "edges": saved["edges"]})
    assert saved_again.status_code == 200
    assert client.get(f"/solutions/{result['solution']['id']}").json()["nodes"] == saved["nodes"]


def test_repeat_upload_reports_conflicts_and_never_overwrites(client, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "service_contract_path", str(tmp_path / "contracts"))
    first = upload(client, package_bytes()).json()
    response = client.post("/services/import/package/confirm", json={
        "upload_token": first["upload_token"], "services": selections(first),
        "registration_only_acknowledged": True,
    })
    assert response.status_code == 200
    second = upload(client, package_bytes()).json()
    assert all(service["duplicate_conflicts"] for service in second["services"])
    duplicate = client.post("/services/import/package/confirm", json={
        "upload_token": second["upload_token"], "services": selections(second),
        "registration_only_acknowledged": True,
    })
    assert duplicate.status_code == 409
    with session_factory() as db:
        assert db.query(Service).filter(Service.id.in_([s["proposed_id"] for s in second["services"]])).count() == 2


def test_multiple_operations_require_explicit_selection(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "service_contract_path", str(tmp_path / "contracts"))
    preview = upload(client, package_bytes(two_operations=True)).json()
    provider = preview["services"][0]
    assert [item["operation_name"] for item in provider["operations"]] == ["ProvideData", "ProvideOther"]
    assert provider["selected_operation"] is None
    assert preview["operation_compatibility"] == "needs_selection"


def test_independent_selected_service_can_register_without_solution(client, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "service_contract_path", str(tmp_path / "contracts"))
    preview = upload(client, package_bytes(connected=False)).json()
    response = client.post("/services/import/package/confirm", json={
        "upload_token": preview["upload_token"], "services": selections(preview, select_formatter=False),
        "create_solution": False, "registration_only_acknowledged": True,
    })
    assert response.status_code == 200
    assert response.json()["solution"] is None


def test_unsafe_archive_is_rejected_without_writes(client, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "service_contract_path", str(tmp_path / "contracts"))
    response = upload(client, package_bytes(unsafe=True))
    assert response.status_code == 422
    assert "Unsafe archive path" in response.text
    with session_factory() as db:
        assert db.query(Service).filter(Service.id.like("pkg-%")).count() == 0


@pytest.fixture
def solution_owners(session_factory, isolated_database_schema):
    """Real authenticated owners, confined to the suite's disposable database."""
    users = [str(uuid4()), str(uuid4())]
    password = token_urlsafe(24)
    with session_factory() as db:
        for identifier in users:
            db.add(User(id=identifier, email=f"{identifier}@example.test",
                        display_name="Historical fixture", role="solution_designer",
                        status="active", password_hash=hash_password(password)))
        db.commit()
    try:
        with TestClient(app) as owner, TestClient(app) as other:
            for browser, identifier in zip((owner, other), users, strict=True):
                login = browser.post("/auth/login", json={
                    "email": f"{identifier}@example.test", "password": password,
                })
                assert login.status_code == 200, login.text
            yield owner, other, users[0]
    finally:
        with session_factory() as db:
            db.query(Solution).filter(Solution.created_by_user_id.in_(users)).delete(synchronize_session=False)
            db.query(AuditEvent).filter(AuditEvent.actor_user_id.in_(users)).delete(synchronize_session=False)
            db.query(UserSession).filter(UserSession.user_id.in_(users)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(users)).delete(synchronize_session=False)
            db.commit()


def missing_service_design():
    return {
        "name": "Missing package service", "status": "draft", "edges": [],
        "nodes": [{"id": "arbitrary", "position": {"x": 1, "y": 2}, "data": {
            "node_kind": "service", "service": {"id": "missing-service"}, "label": "Missing"
        }}],
    }


def owned_solution_state(session_factory, owner_id):
    with session_factory() as db:
        rows = db.query(Solution).filter(Solution.created_by_user_id == owner_id).order_by(Solution.id).all()
        return [
            {column.name: getattr(row, column.name) for column in Solution.__table__.columns}
            for row in rows
        ], db.query(AuditEvent).filter(AuditEvent.actor_user_id == owner_id).count()


def assert_missing_service(response):
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "solution_service_missing",
        "message": "This solution references services that no longer exist.",
        "service_ids": ["missing-service"],
        "recommended_action": "Restore the missing catalogue records or remove their nodes from the solution before editing.",
    }


@pytest.mark.parametrize("method", ["post", "put"])
def test_missing_service_writes_are_rejected_without_partial_mutation(solution_owners, session_factory, method):
    owner, other, owner_id = solution_owners
    created = owner.post("/solutions", json={"name": "Valid empty draft", "nodes": [], "edges": []})
    assert created.status_code == 200, created.text
    identifier = created.json()["id"]
    before = owned_solution_state(session_factory, owner_id)
    url = "/solutions" if method == "post" else f"/solutions/{identifier}"
    assert_missing_service(getattr(owner, method)(url, json=missing_service_design()))
    assert owned_solution_state(session_factory, owner_id) == before
    assert owner.get(f"/solutions/{identifier}").json()["name"] == "Valid empty draft"
    forbidden = other.put(f"/solutions/{identifier}", json=missing_service_design())
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "You can only modify your own solutions"
    assert owned_solution_state(session_factory, owner_id) == before


def test_missing_service_reference_returns_actionable_load_error(solution_owners, session_factory):
    owner, other, owner_id = solution_owners
    identifier = str(uuid4())
    # Historical catalogue loss cannot be created through today's validating API.
    # Seed only the isolated test database, with a real owner and fixture cleanup.
    with session_factory() as db:
        assert db.get(Service, "missing-service") is None
        db.add(Solution(id=identifier, created_by_user_id=owner_id, **missing_service_design()))
        db.commit()
    before = owned_solution_state(session_factory, owner_id)
    forbidden = other.get(f"/solutions/{identifier}")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "You can only access your own solutions"
    assert_missing_service(owner.get(f"/solutions/{identifier}"))
    assert owned_solution_state(session_factory, owner_id) == before


def test_legacy_package_repair_snapshots_original_and_preserves_services(client, session_factory):
    preview = upload(client, package_bytes()).json()
    confirmed = client.post("/services/import/package/confirm", json={
        "upload_token": preview["upload_token"], "services": selections(preview),
        "registration_only_acknowledged": True,
    }).json()
    service_ids = [item["id"] for item in confirmed["services"]]
    with session_factory() as db:
        owner_id = db.get(Service, service_ids[0]).created_by_user_id
        legacy = Solution(
            id="legacy-package-repair", name="Legacy package draft", status="draft",
            created_by_user_id=owner_id,
            nodes=[
                {"id": "data_provider1", "service_id": service_ids[0]},
                {"id": "formatter1", "service_id": service_ids[1]},
            ],
            edges=[{"source": "data_provider1", "target": "formatter1"}],
        )
        db.add(legacy)
        db.add(AuditEvent(
            id="legacy-import-audit", actor_user_id=owner_id, action="solution.package_imported",
            target_type="solution", target_id=legacy.id,
        ))
        db.commit()
        before = {service.id: (service.status, service.internal_host) for service in db.query(Service).filter(Service.id.in_(service_ids))}
        dry_run = repair_legacy_package_solution(db, legacy.id)
        assert dry_run == {
            "status": "repair_ready", "solution_id": legacy.id, "name": legacy.name,
            "services": 2, "internal_connections": 1, "boundary_connections": 2,
        }
        repaired = repair_legacy_package_solution(db, legacy.id, apply=True)
        assert repaired["status"] == "repaired"
        db.refresh(legacy)
        assert count_service_nodes(legacy.nodes) == 2
        assert {service.id: (service.status, service.internal_host) for service in db.query(Service).filter(Service.id.in_(service_ids))} == before
        snapshot = db.query(AuditEvent).filter(AuditEvent.target_id == legacy.id, AuditEvent.action == "solution.package_repair_snapshot").one()
        assert "data_provider1" in snapshot.details
