"""Isolated derived-image entrypoint. Baseline operations/dependencies unchanged.

Only the two supported control operations are served. No mutable-cache gRPC
execution endpoint is started. Configuration and grid snapshots are consumed
directly under a process lock; benchmark input names an immutable workflow/task
manifest in the dedicated read-only upstream volume.
"""
import base64
import json
import os
import sys
from pathlib import Path
import threading

from google.protobuf.json_format import MessageToDict, ParseDict

sys.path.insert(0, "/app")

from dutch_capture_contract import (BASE_IMAGES, VERSION, SOURCE_REVISION, CaptureStore,
                                    confined_read, encode, parse_ref, safe_benchmark, sha, task_id)

ROLE = os.environ["PILOT_CAPTURE_ROLE"]
ROOT = Path("/run-evidence")
CODE_SHA = sha(Path(__file__).read_bytes())
CONTRACT_SHA = sha(Path(__file__).with_name("dutch_capture_contract.py").read_bytes())
PROVENANCE = {"version": VERSION, "base_image": BASE_IMAGES[ROLE], "source_revision": SOURCE_REVISION,
              "adapter_sha256": CODE_SHA, "contract_sha256": CONTRACT_SHA}
LOCK = threading.Lock()


def compute_synth(request, ops):
    from common.control_interface import ExecuteRequest
    if request.inputs:
        if len(request.inputs) != 1 or request.inputs[0].get("protocol") != "inline" or request.inputs[0].get("format") != "json":
            raise ValueError("Unsupported local input")
        submitted = json.loads(base64.b64decode(request.inputs[0]["uri"], validate=True))
        if set(submitted) != {"seed"} or type(submitted["seed"]) is not int or submitted["seed"] not in (42, 43):
            raise ValueError("Unsupported local seed")
    config_response = ops.execute_ConfigureGrid(request)
    if config_response.status != "complete":
        raise ValueError("Configuration execution failed")
    config_raw = ops.get_task_manager().get_data(request.task_id)[0]
    config = json.loads(config_raw)
    synth_request = ExecuteRequest(method="SynthesizeGrid", workflow_id=request.workflow_id, task_id=request.task_id,
        inputs=[{"protocol": "inline", "format": "json", "uri": base64.b64encode(encode(config)).decode()}])
    response = ops.execute_SynthesizeGrid(synth_request)
    if response.status != "complete":
        raise ValueError("Synthesis execution failed")
    grid = MessageToDict(ops._cached_grid_response, preserving_proto_field_name=True)
    return {"configuration": encode({"config": config}), "grid": encode(grid),
            "network": grid["grid_data"]["pandapower_json"].encode()}, None


def compute_benchmark(request, ops):
    if len(request.inputs) != 1:
        raise ValueError("Exactly one captured grid input is required")
    workflow, task, digest = parse_ref(request.inputs[0], request.workflow_id)
    if task != task_id("synth"):
        raise ValueError("Wrong upstream task")
    prefix = f"{workflow}/{task}/"
    manifest_bytes = confined_read("/upstream-evidence", prefix + "manifest.json", digest)
    manifest = json.loads(manifest_bytes)
    if (manifest["workflow_id"], manifest["task_id"], manifest["role"], manifest["status"]) != (workflow, task, "synth", "complete"):
        raise ValueError("Upstream association mismatch")
    if manifest["provenance"] != {**PROVENANCE, "base_image": BASE_IMAGES["synth"]}:
        raise ValueError("Upstream runtime identity mismatch")
    grid_bytes = confined_read("/upstream-evidence", prefix + "grid.json", manifest["files"]["grid"]["sha256"])
    grid = ParseDict(json.loads(grid_bytes), ops.data_synthesizer_pb2.GetGridDataResponse())
    original_split = ops._split_inputs
    try:
        # No gRPC executor is running in this derived image. The only handler is
        # serialized under LOCK, so the baseline operation receives this grid.
        ops._split_inputs = lambda _: (None, grid)
        response = ops.execute_RunBenchmark(request)
    finally:
        ops._split_inputs = original_split
    if response.status != "complete":
        raise ValueError("Benchmark execution failed")
    raw = ops.get_task_manager().get_data(request.task_id)[0]
    raw = raw.encode() if isinstance(raw, str) else raw
    upstream = {"workflow_id": workflow, "task_id": task, "manifest_sha256": digest,
                "grid_sha256": manifest["files"]["grid"]["sha256"]}
    return {"benchmark_source": raw, "benchmark": encode(safe_benchmark(raw, upstream))}, upstream


def main():
    from common.control_interface import DataReference, ExecuteResponse, run
    if ROLE == "synth":
        from common import synth_operations as ops
        operation, compute = "ConfigureAndSynthesize", compute_synth
    elif ROLE == "benchmark":
        from common import benchmark_operations as ops
        operation, compute = "RunBenchmark", compute_benchmark
    else:
        raise ValueError("Unsupported capture role")
    store = CaptureStore(ROOT, ROLE, PROVENANCE)

    def execute(request):
        with LOCK:
            try:
                ref = store.execute(request.model_dump(), lambda: compute(request, ops))
                return ExecuteResponse(status="complete", output=DataReference(**ref))
            except Exception:
                # Do not leak container paths, raw exceptions or credentials.
                return ExecuteResponse(status="failed", error="Local execution/capture failed; inspect the isolated runtime. No retry was made.")

    run({operation: execute}, "Isolated Dutch automatic capture (derived runtime)")


if __name__ == "__main__":
    main()
