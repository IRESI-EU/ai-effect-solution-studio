"""Isolated software-only proof wrappers; no LLM or physical control endpoints.

Evidence is written once per workflow/task after the real algorithm returns.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
from types import SimpleNamespace

sys.path.insert(0, "/app")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import uvicorn
from runtime_parameters import CONTRACTS, validate, capabilities
from parameter_values import effective_parameters

app = FastAPI()
LOCK = threading.Lock()
METHOD = os.environ.get("AIE18_OPERATION", "GenerateTopology")
ROOT = Path(os.environ.get("AIE18_EVIDENCE", "/evidence"))


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: str
    workflow_id: str = Field(pattern=r"^wf-[a-f0-9]{12}$")
    task_id: str = Field(pattern=r"^task_[a-f0-9]{8}$")
    inputs: list[dict] = Field(default_factory=list, max_length=1)
    configuration: dict | None = None


def input_value(refs):
    if not refs:
        return None
    ref = refs[0]
    if ref.get("protocol") != "inline" or ref.get("format") != "json" or len(ref.get("uri", "")) > 1000000:
        raise ValueError("The proof accepts bounded inline JSON input only")
    return json.loads(base64.b64decode(ref["uri"], validate=True))


def dutch(request, parameters):
    from common import synth_operations as ops
    from common.control_interface import ExecuteRequest as DutchRequest
    from google.protobuf.json_format import MessageToDict
    original = ops.PowerGridGenerator
    calls = []

    class ObservedGenerator(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.observed_seed = kwargs["seed"]

        def generate_grid(self, *args, **kwargs):
            result = super().generate_grid(*args, **kwargs)
            calls.append({"seed": self.observed_seed})
            return result

    # Existing algorithm classes and dependencies run unchanged. The isolated
    # synchronous handler serializes their module caches; no gRPC server exists.
    ops.PowerGridGenerator = ObservedGenerator
    try:
        inner = DutchRequest(method="ConfigureGrid", workflow_id=request.workflow_id, task_id=request.task_id,
            inputs=[{"protocol": "inline", "format": "json", "uri": base64.b64encode(encode(parameters)).decode()}])
        configured = ops.execute_ConfigureGrid(inner)
        if configured.status != "complete":
            raise ValueError("Pinned ConfigureGrid failed")
        config_raw = ops.get_task_manager().get_data(request.task_id)[0]
        config = json.loads(config_raw)
        synthesis = DutchRequest(method="SynthesizeGrid", workflow_id=request.workflow_id, task_id=request.task_id,
            inputs=[{"protocol": "inline", "format": "json", "uri": base64.b64encode(encode(config)).decode()}])
        result = ops.execute_SynthesizeGrid(synthesis)
        if result.status != "complete" or calls != [parameters]:
            raise ValueError("Algorithm did not return with the accepted seed")
        grid = MessageToDict(ops._cached_grid_response, preserving_proto_field_name=True)
        return grid, calls[0], "PowerGridGenerator.__init__(seed) and generate_grid returned"
    finally:
        ops.PowerGridGenerator = original


def danish(request, parameters):
    from dh_network_generator import Infrastructure, enumerate_networks
    value = input_value(request.inputs)
    config = value.get("run_config") if isinstance(value, dict) else None
    if not isinstance(config, dict) or set(config) != {"supplies", "loads"}:
        raise ValueError("Supply run_config with supplies and loads only; configure execution settings on the instance")
    if any(not isinstance(config[key], list) or not 1 <= len(config[key]) <= 5
           or any(not isinstance(v, str) or len(v) > 100 for v in config[key]) for key in config):
        raise ValueError("Provide bounded supply/load terminal lists")
    infra = Infrastructure.load(Path(__file__).with_name("syslab_heat_topology.yaml"))
    # These are exactly the arguments forwarded by the verified Danish service.
    solutions = enumerate_networks(infra, config["supplies"], config["loads"],
        allow_hx=parameters["allow_hx"], allow_bypass=parameters["allow_bypass"], max_results=parameters["how_many"])
    if not solutions:
        raise ValueError("No feasible software topology found")
    return {"run_config": config, "topology_count": len(solutions), "networks": [s.to_dict() for s in solutions]}, parameters, "enumerate_networks returned with allow_hx, allow_bypass, max_results"


@app.get("/health")
def health():
    return {"status": "ok", "runtime": "aie18-integration-v2", "evidence_schema": "aie18-v1", "operation": METHOD}


@app.get("/control/capabilities")
def control_capabilities():
    # Declaration only. Algorithm consumption still requires a completed manifest.
    return capabilities(METHOD)


@app.post("/control/execute")
def execute(request: ExecuteRequest):
    if request.method != METHOD:
        raise HTTPException(422, "Unsupported proof operation")
    try:
        if request.configuration is not None:
            parameters = validate(METHOD, request.configuration)
            if METHOD == "ConfigureAndSynthesize" and request.inputs:
                raise ValueError("Configured Dutch instances do not accept an additional workflow seed")
        else:
            legacy = input_value(request.inputs) if METHOD == "ConfigureAndSynthesize" else {}
            parameters = effective_parameters(CONTRACTS[METHOD]["execution_parameters"], legacy or {})
        with LOCK:
            directory = ROOT / request.workflow_id / request.task_id
            directory.mkdir(parents=True, exist_ok=True)
            if any(directory.iterdir()):
                raise ValueError("Execution evidence already exists; submissions are not retried")
            raw = encode(request.model_dump())
            (directory / "request.json").write_bytes(raw)
            try:
                output, consumed, instrumentation = (dutch if METHOD == "ConfigureAndSynthesize" else danish)(request, parameters)
            except Exception:
                (directory / "failed.json").write_bytes(encode({"state": "failed", "request_sha256": digest(raw)}))
                raise
            output_bytes = encode(output)
            (directory / "output.json").write_bytes(output_bytes)
            manifest = {"version": "aie18-v1", "workflow_id": request.workflow_id, "task_id": request.task_id,
                "instance_id": request.configuration["instance_id"] if request.configuration else None,
                "operation": METHOD, "contract": request.configuration,
                "wrapper_received": request.configuration["parameters"] if request.configuration else None,
                "algorithm_consumed": consumed, "instrumentation": instrumentation,
                "request_sha256": digest(raw), "output_sha256": digest(output_bytes),
                "wrapper_sha256": digest(Path(__file__).read_bytes()),
                "contracts_sha256": digest(Path(__file__).with_name("contracts.json").read_bytes())}
            (directory / "manifest.json").write_bytes(encode(manifest))
            return {"status": "complete", "output": {"protocol": "inline", "format": "json", "uri": base64.b64encode(output_bytes).decode()}}
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
