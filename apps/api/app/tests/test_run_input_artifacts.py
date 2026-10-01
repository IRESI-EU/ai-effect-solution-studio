import base64
import json

from fastapi import HTTPException
import pytest

from app.schemas.workflow_submit import WorkflowSubmitRequest
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
