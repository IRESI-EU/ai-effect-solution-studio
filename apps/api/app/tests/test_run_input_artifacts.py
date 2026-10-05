import base64
import json

from fastapi import HTTPException
import pytest

from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.schemas.workflow_submit import WorkflowSubmitNode
from app.models.service import Service
from app.services.data_reference_service import preview_data_reference
from app.services.workflow_compiler import compile_to_wp3_payload


def test_run_input_compiles_to_wp3_inline_json():
    workflow = WorkflowSubmitRequest(
        name="Prompt workflow", nodes=[], edges=[], run_input={"prompt": "Use CHP for the load"}
    )
    compiled = compile_to_wp3_payload(workflow)
    reference = compiled["inputs"][0]
    assert reference["protocol"] == "inline"
    assert reference["format"] == "json"
    assert json.loads(base64.b64decode(reference["uri"])) == {"prompt": "Use CHP for the load"}


def test_empty_run_input_preserves_existing_default_behavior():
    workflow = WorkflowSubmitRequest(name="Default workflow", nodes=[], edges=[])
    assert "inputs" not in compile_to_wp3_payload(workflow)


def test_oversize_run_input_is_rejected():
    workflow = WorkflowSubmitRequest(name="Large", nodes=[], edges=[], run_input={"prompt": "x" * 65536})
    with pytest.raises(HTTPException) as error:
        compile_to_wp3_payload(workflow)
    assert error.value.status_code == 422


def test_catalogue_container_name_overrides_stale_saved_canvas_metadata(session_factory):
    with session_factory() as db:
        service = Service(
            id="svc-authoritative-runtime",
            name="Authoritative runtime",
            provider="Test node",
            category="Test",
            description="Test service",
            input_type="Workflow Start",
            output_type="Workflow Output",
            container_name="current-container",
            image="current-image:latest",
            proto_uri="microservice/current.proto",
            operation_name="RunCurrent",
            internal_host="current-host",
            internal_port="8080",
        )
        db.merge(service)
        db.commit()

        workflow = WorkflowSubmitRequest(
            name="Saved workflow",
            nodes=[
                WorkflowSubmitNode(
                    node_id="service-1",
                    service_id=service.id,
                    container_name="obsolete-container",
                    image="obsolete-image:latest",
                    proto_uri="obsolete.proto",
                    node_type="MLModel",
                    operation_name="RunObsolete",
                    input_message_name="Request",
                    output_message_name="Response",
                    internal_host="obsolete-host",
                    internal_port="9999",
                )
            ],
            edges=[],
        )

        compiled = compile_to_wp3_payload(workflow, db)

    assert compiled["blueprint"]["nodes"][0]["container_name"] == "current-container"
    assert compiled["dockerinfo"]["docker_info_list"][0] == {
        "container_name": "current-container",
        "ip_address": "current-host",
        "port": "8080",
    }


def test_svg_preview_maps_node_path_into_shared_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(tmp_path))
    drawing = tmp_path / "wf-demo" / "drawing.svg"
    drawing.parent.mkdir()
    drawing.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    preview = preview_data_reference("file", "/data/wf-demo/drawing.svg")
    assert preview["available"] is True
    assert base64.b64decode(preview["image_data_url"].split(",", 1)[1]) == drawing.read_bytes()


def test_svg_preview_rejects_outside_artifact_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(tmp_path / "artifacts"))
    outside = tmp_path / "private.svg"
    outside.write_text("<svg></svg>", encoding="utf-8")
    assert preview_data_reference("file", str(outside))["available"] is False
    assert preview_data_reference("file", "/data/../private.svg")["available"] is False


def test_json_preview_maps_node_path_into_shared_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(tmp_path))
    result = tmp_path / "wf-demo" / "result.json"
    result.parent.mkdir()
    result.write_text('{"status": "completed", "score": 0.92}', encoding="utf-8")

    preview = preview_data_reference("file", "/data/wf-demo/result.json")

    assert preview["available"] is True
    assert preview["kind"] == "json"
    assert preview["content"] == {"status": "completed", "score": 0.92}


def test_file_preview_searches_additional_artifact_roots(tmp_path, monkeypatch):
    primary = tmp_path / "primary"
    secondary = tmp_path / "denmark"
    primary.mkdir()
    result = secondary / "wf-demo" / "result.json"
    result.parent.mkdir(parents=True)
    result.write_text('{"drawings": [{"uri": "/data/wf-demo/drawing.svg"}]}', encoding="utf-8")
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(primary))
    monkeypatch.setenv("ARTIFACT_BASE_PATHS", str(secondary))

    preview = preview_data_reference("file", "/data/wf-demo/result.json")

    assert preview["available"] is True
    assert preview["content"]["drawings"][0]["uri"].endswith("drawing.svg")


def test_file_preview_rejects_paths_outside_artifact_roots(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    root.mkdir()
    outside = tmp_path / "private.json"
    outside.write_text('{"secret": true}', encoding="utf-8")
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(root))

    assert preview_data_reference("file", str(outside))["available"] is False
    assert preview_data_reference("file", "/data/../private.json")["available"] is False
