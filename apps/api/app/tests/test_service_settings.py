import base64
import json

import pytest
from fastapi import HTTPException

from app.models.service import Service
from app.schemas.workflow_submit import WorkflowSubmitEdge, WorkflowSubmitNode, WorkflowSubmitRequest
from app.services.service_settings import (
    SettingsDefinitionError,
    normalize_definition,
    resolve_values,
)
from app.services.workflow_compiler import compile_to_wp3_payload

CHRONICS_SETTINGS = {
    "channel": "parameters",
    "schema": {
        "type": "object",
        "properties": {
            "round_decimals": {"type": "integer", "title": "Decimal places", "default": 3, "minimum": 0, "maximum": 10},
            "compress": {"type": "boolean", "title": "Compress output", "default": False},
        },
    },
}

LOADER_SETTINGS = {
    "channel": "run_input",
    "schema": {
        "type": "object",
        "properties": {
            "max_rows": {"type": "integer", "default": 1000, "minimum": 1},
            "output_format": {"type": "string", "enum": ["json", "csv"], "default": "json"},
        },
    },
}


def _service(sid, container, operation, settings=None):
    return Service(
        id=sid, name=sid, provider="Test node", category="Test", description="Test service",
        input_type="Workflow Start", output_type="Workflow Output", container_name=container,
        image=f"{container}:latest", proto_uri=f"microservice/{container}.proto", operation_name=operation,
        internal_host=container, internal_port="8080", owner_node="test",
        interface_contract={"settings": normalize_definition(settings)} if settings else {},
    )


def _node(node_id, service, settings=None):
    return WorkflowSubmitNode(
        node_id=node_id, service_id=service.id, container_name=service.container_name,
        operation_name=service.operation_name, settings=settings,
    )


@pytest.fixture
def services(session_factory):
    items = [
        _service("set-chronics", "villas-chronics", "GenerateChronics", CHRONICS_SETTINGS),
        _service("set-loader", "data-loader", "ExecuteQuery", LOADER_SETTINGS),
        _service("set-fixed", "fixed-trainer", "TrainModel"),
    ]
    with session_factory() as db:
        for item in items:
            db.merge(item)
        db.commit()
    return {s.id: s for s in items}


class TestDefinition:
    def test_valid_definition_is_normalised(self):
        definition = normalize_definition(CHRONICS_SETTINGS)
        assert definition["channel"] == "parameters"
        assert definition["schema"]["additionalProperties"] is False

    @pytest.mark.parametrize(
        "bad, message",
        [
            ({"channel": "env", "schema": CHRONICS_SETTINGS["schema"]}, "channel"),
            ({"schema": {"type": "object", "properties": {}}}, "at least one"),
            ({"schema": {"properties": {"x": {"type": "date"}}}}, "type one of"),
            ({"schema": {"properties": {"x": {"type": "integer", "default": "3"}}}}, "default"),
            ({"schema": {"properties": {"x": {"type": "integer", "minimum": 5, "maximum": 1}}}}, "minimum"),
            ({"schema": {"properties": {"x": {"type": "integer", "pattern": "a"}}}}, "unsupported"),
        ],
    )
    def test_invalid_definitions_rejected(self, bad, message):
        with pytest.raises(SettingsDefinitionError, match=message):
            normalize_definition(bad)


class TestValues:
    def test_defaults_fill_missing_values(self):
        effective, errors = resolve_values(normalize_definition(CHRONICS_SETTINGS), {"round_decimals": 2})
        assert errors == []
        assert effective == {"round_decimals": 2, "compress": False}

    def test_out_of_range_and_unknown_values_reported(self):
        _, errors = resolve_values(normalize_definition(CHRONICS_SETTINGS), {"round_decimals": 42, "speed": 1})
        assert "'round_decimals' must be at most 10" in errors
        assert "'speed' is not a setting of this service" in errors

    def test_boolean_is_not_an_integer(self):
        _, errors = resolve_values(normalize_definition(CHRONICS_SETTINGS), {"round_decimals": True})
        assert errors == ["'round_decimals' must be of type integer"]


class TestCompiler:
    def test_parameters_channel_compiles_per_node(self, services, session_factory):
        chronics = services["set-chronics"]
        workflow = WorkflowSubmitRequest(name="w", nodes=[_node("n1", chronics, {"round_decimals": 2})], edges=[])
        with session_factory() as db:
            compiled = compile_to_wp3_payload(workflow, db)
        assert compiled["parameters"] == {"villas-chronics:GenerateChronics": {"round_decimals": 2, "compress": False}}
        node_meta = compiled["solution_studio_metadata"]["nodes"][0]
        assert node_meta["settings"]["values"]["round_decimals"] == 2

    def test_run_input_channel_targets_start_node_and_run_input_wins(self, services, session_factory):
        loader = services["set-loader"]
        workflow = WorkflowSubmitRequest(
            name="w", nodes=[_node("n1", loader, {"max_rows": 500})], edges=[],
            run_input={"output_format": "csv"},
        )
        with session_factory() as db:
            compiled = compile_to_wp3_payload(workflow, db)
        ref = compiled["node_inputs"]["data-loader:ExecuteQuery"][0]
        assert json.loads(base64.b64decode(ref["uri"])) == {"max_rows": 500, "output_format": "csv"}

    def test_run_input_channel_rejected_on_downstream_node(self, services, session_factory):
        chronics, loader = services["set-chronics"], services["set-loader"]
        workflow = WorkflowSubmitRequest(
            name="w",
            nodes=[_node("a", chronics), _node("b", loader, {"max_rows": 5})],
            edges=[WorkflowSubmitEdge(source="a", target="b")],
        )
        with session_factory() as db, pytest.raises(HTTPException) as error:
            compile_to_wp3_payload(workflow, db)
        assert error.value.status_code == 422
        assert "first step" in error.value.detail["errors"][0]

    def test_invalid_value_blocks_compile(self, services, session_factory):
        workflow = WorkflowSubmitRequest(
            name="w", nodes=[_node("n1", services["set-chronics"], {"round_decimals": -1})], edges=[]
        )
        with session_factory() as db, pytest.raises(HTTPException) as error:
            compile_to_wp3_payload(workflow, db)
        assert "must be at least 0" in error.value.detail["errors"][0]

    def test_fixed_settings_service_sends_nothing_and_warns(self, services, session_factory):
        workflow = WorkflowSubmitRequest(
            name="w", nodes=[_node("n1", services["set-fixed"], {"epochs": 3})], edges=[]
        )
        with session_factory() as db:
            compiled = compile_to_wp3_payload(workflow, db)
        assert "parameters" not in compiled and "node_inputs" not in compiled
        assert any("fixed settings" in w["message"] for w in compiled["solution_studio_metadata"]["warnings"])

    def test_workflow_without_settings_is_unchanged(self, services, session_factory):
        workflow = WorkflowSubmitRequest(name="w", nodes=[_node("n1", services["set-fixed"])], edges=[])
        with session_factory() as db:
            compiled = compile_to_wp3_payload(workflow, db)
        assert "parameters" not in compiled and "node_inputs" not in compiled


class TestEndpoints:
    def test_admin_declares_and_clears_settings(self, client, services):
        response = client.put("/services/set-fixed/settings", json=CHRONICS_SETTINGS)
        assert response.status_code == 200, response.text
        assert response.json()["settings"]["channel"] == "parameters"
        assert client.get("/services/set-fixed/settings").json()["settings"] is not None
        listed = next(s for s in client.get("/services").json() if s["id"] == "set-fixed")
        assert listed["interface_contract"]["settings"]["schema"]["properties"]["compress"]["default"] is False

        cleared = client.put("/services/set-fixed/settings", json=None)
        assert cleared.status_code == 200
        assert cleared.json()["settings"] is None

    def test_invalid_declaration_returns_422(self, client, services):
        response = client.put("/services/set-fixed/settings", json={"channel": "env", "schema": {}})
        assert response.status_code == 422

    def test_anonymous_cannot_declare(self, anonymous_client, services):
        response = anonymous_client.put("/services/set-fixed/settings", json=CHRONICS_SETTINGS)
        assert response.status_code in (401, 403)
