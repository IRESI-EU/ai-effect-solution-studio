from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.operation_contract import (
    OperationContractCreate,
    OperationContractUpdate,
)
from app.services.operation_contract_registry import (
    activate_contract,
    create_contract,
    deprecate_contract,
    update_contract,
    withdraw_contract,
)


TEST_PREFIX = "operation-contract-isolated-test"


def valid_definition():
    return {
        "operation_role": "transformer",
        "inputs": [
            {
                "name": "dataset",
                "required": True,
                "semantic_concept": "urn:ai-effect:concept:test-dataset",
                "value_representation": "data_reference",
                "data_reference_protocols": ["file", "https"],
                "content_types": ["application/json"],
                "schema_ref": "https://example.test/schemas/input-v1.json",
                "min_cardinality": 1,
                "max_cardinality": 1,
                "source_requirement": "upstream_operation",
                "compatibility_notes": [],
            }
        ],
        "outputs": [
            {
                "name": "result",
                "semantic_concept": "urn:ai-effect:concept:test-result",
                "value_representation": "data_reference",
                "data_reference_protocols": ["file", "https"],
                "content_types": ["application/json"],
                "schema_ref": "https://example.test/schemas/output-v1.json",
                "min_cardinality": 1,
                "max_cardinality": 1,
                "compatibility_notes": [],
            }
        ],
        "adapter_capabilities": [],
        "compatibility_notes": [],
    }


def contract_payload(
    *,
    identity=None,
    version="1.0.0",
    definition=None,
    runtime_operation_name="RunTest",
):
    return {
        "operation_identity": identity
        or f"urn:ai-effect:test:{uuid4().hex}",
        "runtime_operation_name": runtime_operation_name,
        "contract_version": version,
        "schema_version": "1.0",
        "source_kind": "manual",
        "source_reference": TEST_PREFIX,
        "definition": definition or valid_definition(),
    }


def create_service(
    session_factory,
    *,
    status="approved",
    lifecycle_status="active",
    trust_badge="validated",
    service_id=None,
):
    service_id = service_id or f"{TEST_PREFIX}-{uuid4().hex}"
    with session_factory() as db:
        db.add(
            Service(
                id=service_id,
                name="Operation contract test service",
                provider="Test provider",
                category="Test",
                status=status,
                lifecycle_status=lifecycle_status,
                version="1.0.0",
                description="Temporary isolated test service.",
                input_type="Legacy Input",
                output_type="Legacy Output",
                trust_badge=trust_badge,
                container_name="test-container",
                image="example.test/test:1.0.0",
                proto_uri="test.proto",
                node_type="MLModel",
                operation_name="RunTest",
                input_message_name="Request",
                output_message_name="Response",
                internal_host="test-container",
                internal_port="8080",
                repository_url="https://example.test/repository",
                repository_branch="test",
                manifest_path="ai-effect.service.json",
                interface_type="control",
                interface_contract={"type": "control"},
                orchestration_mode="native",
                adapter_type=None,
                health_path="/health",
                contract_uri="ai-effect.service.json",
            )
        )
        db.commit()
    return service_id


def create_contract_via_api(client, service_id, payload=None):
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=payload or contract_payload(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_contract_direct(session_factory, service_id, payload=None):
    with session_factory() as db:
        return create_contract(
            service_id,
            OperationContractCreate.model_validate(
                payload or contract_payload()
            ),
            db,
        ).id


def read_contract(session_factory, contract_id):
    with session_factory() as db:
        contract = db.get(OperationContract, contract_id)
        assert contract is not None
        return {
            "status": contract.status,
            "runtime_operation_name": contract.runtime_operation_name,
            "activated_at": contract.activated_at,
            "deprecated_at": contract.deprecated_at,
            "withdrawn_at": contract.withdrawn_at,
        }


def test_suite_uses_named_isolated_database(isolated_test_database_name):
    assert isolated_test_database_name.endswith("_test")


@pytest.mark.parametrize(
    "path,method,json_body",
    [
        ("/services/missing/operation-contracts", "get", None),
        (
            "/services/missing/operation-contracts",
            "post",
            contract_payload(),
        ),
        ("/services/missing/operation-contract-resolution", "get", None),
    ],
)
def test_missing_service_endpoints_return_404(client, path, method, json_body):
    request = getattr(client, method)
    response = request(path) if json_body is None else request(path, json=json_body)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path,method,json_body",
    [
        ("/operation-contracts/missing", "get", None),
        (
            "/operation-contracts/missing",
            "put",
            contract_payload(),
        ),
        ("/operation-contracts/missing/activate", "post", None),
        ("/operation-contracts/missing/deprecate", "post", None),
        ("/operation-contracts/missing/withdraw", "post", None),
    ],
)
def test_missing_contract_endpoints_return_404(client, path, method, json_body):
    request = getattr(client, method)
    response = request(path) if json_body is None else request(path, json=json_body)
    assert response.status_code == 404


def test_unknown_resolution_changes_to_active(
    client,
    session_factory,
):
    service_id = create_service(session_factory)
    unknown = client.get(
        f"/services/{service_id}/operation-contract-resolution"
    )
    assert unknown.status_code == 200
    assert unknown.json() == {
        "resolution": "unknown",
        "reason": "no_active_contract",
        "contract": None,
    }

    contract = create_contract_via_api(client, service_id)
    activated = client.post(
        f"/operation-contracts/{contract['id']}/activate"
    )
    assert activated.status_code == 200

    resolved = client.get(
        f"/services/{service_id}/operation-contract-resolution"
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolution"] == "active"
    assert resolved.json()["reason"] is None
    assert resolved.json()["contract"]["id"] == contract["id"]


@pytest.mark.parametrize(
    "identity",
    [
        "https://example.test/operations/analyze",
        "urn:ai-effect:operation:analyze-data",
    ],
)
def test_valid_uri_and_urn_are_accepted(client, session_factory, identity):
    service_id = create_service(session_factory)
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(identity=identity),
    )
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "identity",
    [
        "urn:bad",
        "urn:-invalid:operation",
        "urn:ai-effect:bad%G1",
        "urn:ai-effect:trailing%",
        "https://example.test/bad%G1",
        "https://example.test/has space",
        "https://example.test:bad-port/operation",
    ],
)
def test_malformed_operation_identity_is_rejected(
    client,
    session_factory,
    identity,
):
    service_id = create_service(session_factory)
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(identity=identity),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "version",
    ["1.2.3-alpha.1", "1.2.3+build.2026", "1.2.3-alpha+build.7"],
)
def test_valid_semantic_version_variants_are_accepted(
    client,
    session_factory,
    version,
):
    service_id = create_service(session_factory)
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(version=version),
    )
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("version", ["01.0.0", "1.01.0", "1.0.01", "1.0"])
def test_invalid_semantic_versions_are_rejected(
    client,
    session_factory,
    version,
):
    service_id = create_service(session_factory)
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(version=version),
    )
    assert response.status_code == 422


def test_unknown_top_level_field_is_rejected(client, session_factory):
    service_id = create_service(session_factory)
    payload = contract_payload()
    payload["contract_verison"] = "1.0.0"
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=payload,
    )
    assert response.status_code == 422


def test_unknown_definition_field_is_rejected(client, session_factory):
    service_id = create_service(session_factory)
    payload = contract_payload()
    payload["definition"]["unknown_definition_field"] = True
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("slot_collection", ["inputs", "outputs"])
def test_unknown_nested_slot_field_is_rejected(
    client,
    session_factory,
    slot_collection,
):
    service_id = create_service(session_factory)
    payload = contract_payload()
    payload["definition"][slot_collection][0]["unknown_slot_field"] = True
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "collection,field",
    [
        ("inputs", "data_reference_protocols"),
        ("outputs", "data_reference_protocols"),
        ("inputs", "content_types"),
        ("outputs", "content_types"),
    ],
)
def test_blank_protocols_and_content_types_are_rejected(
    client,
    session_factory,
    collection,
    field,
):
    service_id = create_service(session_factory)
    definition = valid_definition()
    definition[collection][0][field].append(" ")
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(definition=definition),
    )
    assert response.status_code == 422


def test_null_max_cardinality_is_accepted(client, session_factory):
    service_id = create_service(session_factory)
    definition = valid_definition()
    definition["inputs"][0]["max_cardinality"] = None
    definition["outputs"][0]["max_cardinality"] = None
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(definition=definition),
    )
    assert response.status_code == 201, response.text


def test_invalid_source_requirement_is_rejected(client, session_factory):
    service_id = create_service(session_factory)
    definition = valid_definition()
    definition["inputs"][0]["source_requirement"] = "somewhere"
    response = client.post(
        f"/services/{service_id}/operation-contracts",
        json=contract_payload(definition=definition),
    )
    assert response.status_code == 422


def test_duplicate_slots_cardinality_and_schema_version_are_rejected(
    client,
    session_factory,
):
    cases = []

    duplicate_input = valid_definition()
    duplicate_input["inputs"].append(deepcopy(duplicate_input["inputs"][0]))
    cases.append(contract_payload(definition=duplicate_input))

    duplicate_output = valid_definition()
    duplicate_output["outputs"].append(
        deepcopy(duplicate_output["outputs"][0])
    )
    cases.append(contract_payload(definition=duplicate_output))

    invalid_cardinality = valid_definition()
    invalid_cardinality["inputs"][0]["min_cardinality"] = 2
    invalid_cardinality["inputs"][0]["max_cardinality"] = 1
    cases.append(contract_payload(definition=invalid_cardinality))

    invalid_required = valid_definition()
    invalid_required["inputs"][0]["min_cardinality"] = 0
    cases.append(contract_payload(definition=invalid_required))

    invalid_optional = valid_definition()
    invalid_optional["inputs"][0]["required"] = False
    invalid_optional["inputs"][0]["min_cardinality"] = 1
    cases.append(contract_payload(definition=invalid_optional))

    no_source = valid_definition()
    no_source["inputs"][0]["source_requirement"] = "none"
    cases.append(contract_payload(definition=no_source))

    invalid_schema = contract_payload()
    invalid_schema["schema_version"] = "2.0"
    cases.append(invalid_schema)

    for payload in cases:
        service_id = create_service(session_factory)
        response = client.post(
            f"/services/{service_id}/operation-contracts",
            json=payload,
        )
        assert response.status_code == 422


def test_duplicate_contract_version_is_rejected(client, session_factory):
    service_id = create_service(session_factory)
    identity = f"urn:ai-effect:test:{uuid4().hex}"
    payload = contract_payload(identity=identity)
    create_contract_via_api(client, service_id, payload)
    duplicate = client.post(
        f"/services/{service_id}/operation-contracts",
        json=payload,
    )
    assert duplicate.status_code == 409


def test_put_replaces_editable_metadata_but_cannot_change_service(
    client,
    session_factory,
):
    service_id = create_service(session_factory)
    contract = create_contract_via_api(client, service_id)
    update = contract_payload(
        identity=contract["operation_identity"],
        version=contract["contract_version"],
        runtime_operation_name="RunUpdatedTest",
    )
    response = client.put(
        f"/operation-contracts/{contract['id']}",
        json=update,
    )
    assert response.status_code == 200, response.text
    assert response.json()["runtime_operation_name"] == "RunUpdatedTest"
    assert response.json()["service_id"] == service_id

    update["service_id"] = "another-service"
    forbidden = client.put(
        f"/operation-contracts/{contract['id']}",
        json=update,
    )
    assert forbidden.status_code == 422


@pytest.mark.parametrize("status", ["approved", "validated"])
def test_approved_and_legacy_validated_services_can_activate(
    client,
    session_factory,
    status,
):
    service_id = create_service(session_factory, status=status)
    contract = create_contract_via_api(client, service_id)
    response = client.post(
        f"/operation-contracts/{contract['id']}/activate"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"


@pytest.mark.parametrize(
    "status,lifecycle_status,trust_badge",
    [
        ("pending_review", "active", "pending_review"),
        ("rejected", "active", "validated"),
        ("approved", "active", "rejected"),
        ("approved", "archived", "validated"),
    ],
)
def test_ineligible_services_cannot_activate(
    client,
    session_factory,
    status,
    lifecycle_status,
    trust_badge,
):
    service_id = create_service(
        session_factory,
        status=status,
        lifecycle_status=lifecycle_status,
        trust_badge=trust_badge,
    )
    contract = create_contract_via_api(client, service_id)
    response = client.post(
        f"/operation-contracts/{contract['id']}/activate"
    )
    assert response.status_code == 409


def test_activation_deprecates_previous_and_leaves_one_active(
    client,
    session_factory,
):
    service_id = create_service(session_factory)
    identity = f"urn:ai-effect:test:{uuid4().hex}"
    first = create_contract_via_api(
        client,
        service_id,
        contract_payload(identity=identity, version="1.0.0"),
    )
    second = create_contract_via_api(
        client,
        service_id,
        contract_payload(identity=identity, version="2.0.0"),
    )
    assert client.post(
        f"/operation-contracts/{first['id']}/activate"
    ).status_code == 200
    assert client.post(
        f"/operation-contracts/{second['id']}/activate"
    ).status_code == 200

    contracts = client.get(
        f"/services/{service_id}/operation-contracts"
    ).json()
    active = [item for item in contracts if item["status"] == "active"]
    deprecated = [
        item for item in contracts if item["status"] == "deprecated"
    ]
    assert [item["id"] for item in active] == [second["id"]]
    assert [item["id"] for item in deprecated] == [first["id"]]
    assert deprecated[0]["deprecated_at"] is not None


def test_deprecated_contract_cannot_be_activated(client, session_factory):
    service_id = create_service(session_factory)
    contract = create_contract_via_api(client, service_id)
    assert client.post(
        f"/operation-contracts/{contract['id']}/activate"
    ).status_code == 200
    assert client.post(
        f"/operation-contracts/{contract['id']}/deprecate"
    ).status_code == 200
    assert client.post(
        f"/operation-contracts/{contract['id']}/activate"
    ).status_code == 409


def test_all_mutations_from_withdrawn_are_rejected(client, session_factory):
    service_id = create_service(session_factory)
    contract = create_contract_via_api(client, service_id)
    assert client.post(
        f"/operation-contracts/{contract['id']}/withdraw"
    ).status_code == 200

    assert client.put(
        f"/operation-contracts/{contract['id']}",
        json=contract_payload(
            identity=contract["operation_identity"],
            version=contract["contract_version"],
        ),
    ).status_code == 409
    for action in ("activate", "deprecate", "withdraw"):
        assert client.post(
            f"/operation-contracts/{contract['id']}/{action}"
        ).status_code == 409


def test_active_must_be_deprecated_before_withdrawal(
    client,
    session_factory,
):
    service_id = create_service(session_factory)
    contract = create_contract_via_api(client, service_id)
    assert client.post(
        f"/operation-contracts/{contract['id']}/activate"
    ).status_code == 200
    assert client.post(
        f"/operation-contracts/{contract['id']}/withdraw"
    ).status_code == 409
    assert client.post(
        f"/operation-contracts/{contract['id']}/deprecate"
    ).status_code == 200
    withdrawn = client.post(
        f"/operation-contracts/{contract['id']}/withdraw"
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["withdrawn_at"] is not None


def test_direct_registry_lifecycle_functions(session_factory):
    service_id = create_service(session_factory)
    contract_id = create_contract_direct(session_factory, service_id)

    with session_factory() as db:
        activated = activate_contract(contract_id, db)
        assert activated.status == "active"
    with session_factory() as db:
        deprecated = deprecate_contract(contract_id, db)
        assert deprecated.status == "deprecated"
    with session_factory() as db:
        withdrawn = withdraw_contract(contract_id, db)
        assert withdrawn.status == "withdrawn"


def test_forced_commit_failure_rolls_back_and_session_recovers(
    session_factory,
):
    service_id = create_service(session_factory)
    contract_id = create_contract_direct(session_factory, service_id)

    with session_factory() as db:
        with patch.object(
            db,
            "commit",
            side_effect=SQLAlchemyError("forced commit failure"),
        ):
            with pytest.raises(SQLAlchemyError):
                activate_contract(contract_id, db)
        assert not db.in_transaction()
        assert db.query(Service).filter(Service.id == service_id).one().id == service_id

    state = read_contract(session_factory, contract_id)
    assert state["status"] == "draft"
    assert state["activated_at"] is None


def test_full_service_record_is_unchanged_by_contract_lifecycle(
    session_factory,
):
    service_id = create_service(session_factory)
    with session_factory() as db:
        service = db.get(Service, service_id)
        columns = inspect(Service).columns
        before = {column.key: deepcopy(getattr(service, column.key)) for column in columns}

    contract_id = create_contract_direct(session_factory, service_id)
    with session_factory() as db:
        activate_contract(contract_id, db)
    with session_factory() as db:
        deprecate_contract(contract_id, db)
    with session_factory() as db:
        withdraw_contract(contract_id, db)

    with session_factory() as db:
        service = db.get(Service, service_id)
        after = {
            column.key: deepcopy(getattr(service, column.key))
            for column in inspect(Service).columns
        }
    assert after == before


def _run_concurrently(first, second):
    barrier = Barrier(2)

    def wrapped(operation):
        barrier.wait()
        try:
            return ("ok", operation())
        except HTTPException as exc:
            return ("http_error", exc.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(wrapped, first),
            executor.submit(wrapped, second),
        ]
        return [future.result(timeout=15) for future in futures]


def test_concurrent_activation_leaves_exactly_one_active(session_factory):
    service_id = create_service(session_factory)
    first_id = create_contract_direct(
        session_factory,
        service_id,
        contract_payload(version="1.0.0"),
    )
    second_id = create_contract_direct(
        session_factory,
        service_id,
        contract_payload(version="2.0.0"),
    )

    def activate(contract_id):
        with session_factory() as db:
            return activate_contract(contract_id, db).id

    results = _run_concurrently(
        lambda: activate(first_id),
        lambda: activate(second_id),
    )
    assert [result[0] for result in results] == ["ok", "ok"]

    with session_factory() as db:
        contracts = (
            db.query(OperationContract)
            .filter(OperationContract.service_id == service_id)
            .all()
        )
    assert sum(contract.status == "active" for contract in contracts) == 1
    assert sum(contract.status == "deprecated" for contract in contracts) == 1


def test_activation_racing_with_withdrawal_cannot_overwrite_winner(
    session_factory,
):
    service_id = create_service(session_factory)
    contract_id = create_contract_direct(session_factory, service_id)

    def activate():
        with session_factory() as db:
            return activate_contract(contract_id, db).status

    def withdraw():
        with session_factory() as db:
            return withdraw_contract(contract_id, db).status

    results = _run_concurrently(activate, withdraw)
    assert sorted(result[0] for result in results) == ["http_error", "ok"]
    assert next(result[1] for result in results if result[0] == "http_error") == 409
    assert read_contract(session_factory, contract_id)["status"] in {
        "active",
        "withdrawn",
    }


def test_activation_racing_with_update_preserves_successful_update(
    session_factory,
):
    service_id = create_service(session_factory)
    original = contract_payload(runtime_operation_name="OriginalOperation")
    contract_id = create_contract_direct(
        session_factory,
        service_id,
        original,
    )
    update_payload = contract_payload(
        identity=original["operation_identity"],
        version=original["contract_version"],
        runtime_operation_name="UpdatedOperation",
    )

    def activate():
        with session_factory() as db:
            return activate_contract(contract_id, db).status

    def update():
        with session_factory() as db:
            return update_contract(
                contract_id,
                OperationContractUpdate.model_validate(update_payload),
                db,
            ).runtime_operation_name

    results = _run_concurrently(activate, update)
    activation_result = results[0]
    update_result = results[1]
    assert activation_result == ("ok", "active")

    final_state = read_contract(session_factory, contract_id)
    assert final_state["status"] == "active"
    if update_result[0] == "ok":
        assert final_state["runtime_operation_name"] == "UpdatedOperation"
    else:
        assert update_result == ("http_error", 409)
        assert final_state["runtime_operation_name"] == "OriginalOperation"
