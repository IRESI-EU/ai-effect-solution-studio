"""Bounded local adapter around the existing Dutch node algorithms.

No gRPC cache server, arbitrary reference resolver, LLM or hardware endpoint.
CaptureStore claims each workflow/task once and preserves failures.
"""
import base64
import json
from pathlib import Path
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

import capture_algorithms as capture
from dutch_capture_contract import BASE_IMAGES, VERSION, SOURCE_REVISION, CaptureStore, encode, sha
from parameter_values import effective_parameters, match_wrapper_configuration

CONTRACTS = json.loads(Path(__file__).with_name("contracts.json").read_text())
ROLE = capture.ROLE
METHOD = {"synth": "ConfigureAndSynthesize", "benchmark": "RunBenchmark"}[ROLE]
SPEC = CONTRACTS[METHOD]
DEFINITION = SPEC["definition"]
ADAPTER_SHA = sha(b"".join(Path(__file__).with_name(name).read_bytes()
    for name in ("runtime.py", "capture_algorithms.py", "parameter_values.py", "contracts.json")))
capture.PROVENANCE = {**capture.PROVENANCE, "adapter_sha256": ADAPTER_SHA}
STORE = CaptureStore("/run-evidence", ROLE, capture.PROVENANCE)
LOCK = threading.Lock()
app = FastAPI()


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: str
    workflow_id: str = Field(pattern=r"^wf-[a-f0-9]{12}$")
    task_id: str = Field(pattern=r"^task_[a-f0-9]{8}$")
    inputs: list[dict] = Field(default_factory=list, max_length=1)
    configuration: dict | None = None


@app.get("/health")
def health():
    return {"status": "ok", "runtime": "aie37-dutch-v1", "operation": METHOD, "adapter_sha256": ADAPTER_SHA}


@app.get("/control/capabilities")
def capabilities():
    operation = {"operation_name": METHOD, "operation_identity": SPEC["operation_identity"],
        "contract_version": SPEC["contract_version"], "binding_transport": "whole-output-v1",
        "io_contract_sha256": sha(encode(DEFINITION))}
    if "execution_parameters" in DEFINITION:
        operation["execution_parameters"] = DEFINITION["execution_parameters"]
    return {"capability_schema_version": "1.0", "transports": ["http-parameters-v1"],
            "operations": [operation]}


def compute_synth(request, ops):
    if request.inputs or request.configuration is None:
        raise ValueError("Use saved instance parameters, without an additional workflow seed")
    match_wrapper_configuration(METHOD, request.configuration, capabilities())
    parameters = effective_parameters(DEFINITION["execution_parameters"], request.configuration["parameters"])
    from common.control_interface import ExecuteRequest as InnerRequest
    inner = InnerRequest(method=METHOD, workflow_id=request.workflow_id, task_id=request.task_id,
        inputs=[{"protocol": "inline", "format": "json", "uri": base64.b64encode(encode(parameters)).decode()}])
    original, calls = ops.PowerGridGenerator, []
    class ObservedGenerator(original):
        def __init__(self, *args, **kwargs):
            self.observed_seed = kwargs["seed"]
            super().__init__(*args, **kwargs)
        def generate_grid(self, *args, **kwargs):
            output = super().generate_grid(*args, **kwargs)
            calls.append({"seed": self.observed_seed})
            return output
    ops.PowerGridGenerator = ObservedGenerator
    try:
        files, upstream = capture.compute_synth(inner, ops)
        if calls != [parameters]:
            raise ValueError("Algorithm consumption does not match the saved setting")
        configuration = json.loads(files["configuration"])
        files["configuration"] = encode({**configuration, "algorithm_consumed": calls[0],
            "instrumentation": "PowerGridGenerator.__init__(seed); generate_grid returned"})
        return files, upstream
    finally:
        ops.PowerGridGenerator = original


@app.post("/control/execute")
def execute(request: ExecuteRequest):
    if request.method != METHOD:
        raise HTTPException(422, "Unsupported operation")
    with LOCK:
        try:
            if ROLE == "synth":
                from common import synth_operations as ops
                compute = lambda: compute_synth(request, ops)
            else:
                if request.configuration is not None:
                    raise ValueError("This benchmark publishes no configurable parameters")
                from common import benchmark_operations as ops
                compute = lambda: capture.compute_benchmark(request, ops)
            reference = STORE.execute(request.model_dump(), compute)
            return {"status": "complete", "output": reference}
        except Exception:
            return {"status": "failed", "error": "Local execution or evidence capture failed. Failure is preserved; do not resubmit."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
