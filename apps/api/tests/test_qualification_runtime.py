"""Disposable algorithm doubles: transport and failure behavior, not live proof."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from fastapi.testclient import TestClient
from app.services.dutch_capture_contract import task_id


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    folder = Path(__file__).resolve().parents[3] / "deploy/aie37"
    monkeypatch.syspath_prepend(str(folder))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "app/services"))
    monkeypatch.setenv("PILOT_CAPTURE_ROLE", "synth")
    # Algorithm/serialization helpers are explicit doubles in this portable
    # suite. Real protobuf parsing is checked against the pinned runtime.
    monkeypatch.setitem(sys.modules, "capture_algorithms", SimpleNamespace(
        ROLE="synth", PROVENANCE={"version": "fixture"}, task_id=task_id,
        compute_synth=lambda *_: pytest.fail("Supply an explicit algorithm double")))
    image_folder = tmp_path / "image"
    image_folder.mkdir()
    for name in ("runtime.py", "capture_algorithms.py", "contracts.json"):
        (image_folder / name).write_bytes((folder / name).read_bytes())
    (image_folder / "parameter_values.py").write_bytes((Path(__file__).resolve().parents[1] / "app/services/parameter_values.py").read_bytes())
    spec = importlib.util.spec_from_file_location("qualification_runtime_fixture", image_folder / "runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STORE.root = tmp_path / "evidence"
    return module


def request(module, seed=43):
    return module.ExecuteRequest(method="ConfigureAndSynthesize", workflow_id="wf-112233445566",
        task_id=module.capture.task_id("synth"), configuration={"contract_id": "test-contract",
        "contract_version": "1.0.0", "operation_identity": module.SPEC["operation_identity"],
        "schema_version": "1.0", "instance_id": "source", "parameters": {"seed": seed}})


def test_parameter_is_passed_to_algorithm_and_restored(runtime, monkeypatch):
    calls = []
    class Generator:
        def __init__(self, **kwargs): calls.append(kwargs)
        def generate_grid(self): return "grid"
    ops = SimpleNamespace(PowerGridGenerator=Generator)
    monkeypatch.setitem(sys.modules, "common", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "common.control_interface", SimpleNamespace(ExecuteRequest=lambda **kw: SimpleNamespace(**kw)))
    def compute(inner, operations):
        import base64
        parameters = json.loads(base64.b64decode(inner.inputs[0]["uri"]))
        operations.PowerGridGenerator(seed=parameters["seed"]).generate_grid()
        return {"configuration": runtime.encode({"config": parameters})}, None
    monkeypatch.setattr(runtime.capture, "compute_synth", compute)
    files, _ = runtime.compute_synth(request(runtime), ops)
    assert calls == [{"seed": 43}]
    assert json.loads(files["configuration"])["algorithm_consumed"] == {"seed": 43}
    assert ops.PowerGridGenerator is Generator


@pytest.mark.parametrize("mutation", ["missing", "null", "type", "range", "version", "extra-input"])
def test_invalid_configuration_does_not_invoke_algorithm(runtime, monkeypatch, mutation):
    value = request(runtime).model_dump()
    if mutation == "missing": value["configuration"] = None
    if mutation == "null": value["configuration"]["parameters"]["seed"] = None
    if mutation == "type": value["configuration"]["parameters"]["seed"] = True
    if mutation == "range": value["configuration"]["parameters"]["seed"] = 44
    if mutation == "version": value["configuration"]["contract_version"] = "3.0.0"
    if mutation == "extra-input": value["inputs"] = [{"protocol": "inline", "format": "json", "uri": "e30="}]
    monkeypatch.setattr(runtime.capture, "compute_synth", lambda *_: pytest.fail("No algorithm call permitted"))
    with pytest.raises(ValueError):
        runtime.compute_synth(runtime.ExecuteRequest(**value), SimpleNamespace())


def test_failure_is_preserved_and_same_identity_cannot_recompute(runtime, monkeypatch):
    monkeypatch.setitem(sys.modules, "common", SimpleNamespace(synth_operations=SimpleNamespace()))
    calls = []
    def fail(*_):
        calls.append("invoked")
        raise ValueError("Synthetic algorithm failure")
    monkeypatch.setattr(runtime, "compute_synth", fail)
    payload = request(runtime).model_dump()
    with TestClient(runtime.app) as client:
        assert client.post("/control/execute", json=payload).json()["status"] == "failed"
        assert client.post("/control/execute", json=payload).json()["status"] == "failed"
    assert calls == ["invoked"]
    assert list(runtime.STORE.root.rglob("failed.json"))
