"""Read-only, explicitly associated captures; never query mutable wrapper caches.

The operator-created index is the trust boundary, mounted read-only separately
from the spending ledgers. No draft/solution content is used to infer history.
"""
import base64
import hashlib
import json
import re
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings

REVISION = "ba598b2459f9986dac4e37dcc5d7d3298f25dc3a"
SCOPE = "isolated-dutch-" + REVISION
IMAGES = {
    "seed-synth": "sha256:f14731e7c4bf273561ad02ab2a42895069543b7b6e0f0ffa2dec4fb56599b992",
    "seed-benchmark": "sha256:590a5263c2b715159fb961da07a4f9a2821775aceede3d9e2f757e3daa9dc914",
    "seed-orchestrator": "sha256:c37ce3f1ed74b06b2ee0f6da3661526f690b1d3ba23da1395209d448057082a6",
}
FILES = {
    "report": ("report.json", "Capture provenance", None),
    "tasks": ("tasks.json", "Captured task metadata", None),
    "configuration": ("configuration.json", "Generated configuration", "ConfigureAndSynthesize"),
    "grid": ("grid.json", "Grid data", "ConfigureAndSynthesize"),
    "network": ("network.pandapower.json", "Pandapower graph", "ConfigureAndSynthesize"),
    "benchmark": ("benchmark.json", "Benchmark results (safe export)", "RunBenchmark"),
}
MAX_BYTES = 4 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def enabled():
    if not settings.local_dutch_evidence_root or settings.local_dutch_evidence_scope != SCOPE:
        return False
    url = make_url(settings.database_url)
    return (url.host == "127.0.0.1" and url.database == "design_ai_acceptance_dutch_seed"
            and settings.orchestrator_base_url == "http://seed-orchestrator:8000")


def read_confined(root: Path, relative: str, checksum: str | None = None) -> bytes:
    """Only fixed server-selected names; resolve containment and reject symlinks.

    The dedicated mount is read-only. Read and hash the same bytes subsequently
    returned, rather than asking FileResponse to reopen a checked pathname.
    """
    base = root.resolve(strict=True)
    candidate = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise EvidenceError("Invalid evidence path")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(base):
        raise EvidenceError("Evidence outside permitted location")
    cursor = candidate
    while cursor != root:
        if cursor.is_symlink():
            raise EvidenceError("Evidence symlink rejected")
        cursor = cursor.parent
    if not resolved.is_file() or resolved.stat().st_size > MAX_BYTES:
        raise EvidenceError("Invalid evidence file")
    with resolved.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise EvidenceError("Evidence too large")
    if checksum is not None and (not re.fullmatch(r"[a-f0-9]{64}", checksum)
                                 or hashlib.sha256(data).hexdigest() != checksum):
        raise EvidenceError("Evidence integrity check failed")
    return data


def _same_tasks(recorded, live):
    fields = ("task_id", "node_key", "status", "created_at", "updated_at")
    return sorted([tuple(t.get(k) for k in fields) for t in recorded]) == sorted(
        [tuple(t.get(k) for k in fields) for t in live])


def load_capture(deployment, workflow=None, live_tasks=None):
    """Validate association on every metadata/download request, after authorization."""
    unavailable = {"state": "unavailable", "message": "References unavailable through this API; no associated local capture is configured.",
                   "execution_input": None, "artifacts": []}
    if not enabled():
        return unavailable, {}
    if not re.fullmatch(r"wf-[a-f0-9]{12}", deployment.workflow_id):
        return unavailable, {}
    root = Path(settings.local_dutch_evidence_root)
    try:
        index = json.loads(read_confined(root, "index.json"))
    except (OSError, ValueError):
        return {**unavailable, "message": "Local evidence index unavailable; references unavailable through this API."}, {}
    try:
        if index["scope"] != SCOPE:
            raise EvidenceError("Wrong runtime scope")
        entry = index["workflows"].get(deployment.workflow_id)
        if entry is None:
            return unavailable, {}
        if (entry["solution_id"] != deployment.solution_id
                or entry["owner_user_id"] != deployment.created_by_user_id
                or entry["source_revision"] != REVISION or entry["images"] != IMAGES):
            raise EvidenceError("Workflow association mismatch")
        folder = deployment.workflow_id + "/"

        def read(key):
            return read_confined(root, folder + FILES[key][0], entry["sha256"][key])

        report = json.loads(read("report"))
        tasks = json.loads(read("tasks"))
        if (report["workflow_id"] != deployment.workflow_id
                or report["status"]["workflow_id"] != deployment.workflow_id
                or report["status"]["status"] != "completed"
                or report["generator"]["source_revision"] != REVISION
                or report["generator"]["image_id"] != IMAGES["seed-synth"]
                or report["artifact_sha256"]["tasks.json"] != entry["sha256"]["tasks"]
                or len(tasks) != 2 or any(t["workflow_id"] != deployment.workflow_id or t["status"] != "completed" for t in tasks)):
            raise EvidenceError("Capture association mismatch")
        if workflow is not None and any(workflow.get(k) != report["status"].get(k)
                                        for k in ("workflow_id", "status", "created_at", "updated_at")):
            raise EvidenceError("Workflow execution metadata mismatch")
        if live_tasks is not None and not _same_tasks(tasks, live_tasks):
            raise EvidenceError("Task execution metadata mismatch")
        generator = next(t for t in tasks if t["node_key"] == "grid_synth_service:ConfigureAndSynthesize")
        benchmark_task = next(t for t in tasks if t["node_key"] == "benchmark-runner:RunBenchmark")
        refs = generator["input_refs"]
        if len(refs) != 1 or refs[0]["protocol"] != "inline" or refs[0]["format"] != "json":
            raise EvidenceError("Unsupported recorded input")
        submitted = json.loads(base64.b64decode(refs[0]["uri"], validate=True))
        if (set(submitted) != {"seed"} or type(submitted["seed"]) is not int
                or submitted["seed"] != report["seed"]
                or benchmark_task["input_refs"] != generator["output_refs"]):
            raise EvidenceError("Execution input mismatch")
        for key, original in (("configuration", "configuration.json"), ("grid", "grid.json"), ("network", "network.pandapower.json")):
            if key in entry["sha256"] and entry["sha256"][key] != report["generator"]["artifacts"][original]["sha256"]:
                raise EvidenceError("Artifact association mismatch")
        if entry["benchmark_source_sha256"] != report["artifact_sha256"]["benchmark-result.json"]:
            raise EvidenceError("Benchmark association mismatch")
        result = {"state": "available", "message": "Recorded local capture; production compatibility unverified.",
                  "source": "Captured WP3 Redis task state and wrapper gRPC/HTTP artifacts",
                  "source_revision": REVISION, "images": entry["images"],
                  "execution_input": submitted, "input_source": "Captured execution task input (not the editable design)",
                  "tasks": tasks, "grid": None, "benchmark": None, "artifacts": [],
                  "limitations": "Wrapper references address mutable caches and are not replayed. Benchmark export omits temporary container paths; temporary CSV files were not retained. Grid IDs and task IDs are not globally unique."}
        blobs = {}
        for key in ("configuration", "grid", "network", "benchmark"):
            _, label, operation = FILES[key]
            task = generator if operation == "ConfigureAndSynthesize" else benchmark_task
            original_name = FILES[key][0]
            recorded = (key in entry["sha256"] or (key == "benchmark" and "benchmark-result.json" in report["artifact_sha256"])
                        or (key != "benchmark" and original_name in report["generator"]["artifacts"]))
            artifact = {"id": key, "label": label, "task_id": task["task_id"],
                        "state": "inaccessible" if recorded else "not_recorded"}
            if key in entry["sha256"]:
                artifact.update(state="inaccessible", sha256=entry["sha256"][key])
                try:
                    data = read(key)
                    value = json.loads(data)
                    if key == "configuration" and value["config"]["seed"] != submitted["seed"]:
                        raise EvidenceError("Configuration seed mismatch")
                    if key == "grid":
                        grid = value["grid_data"]
                        if grid["seed"] != submitted["seed"] or grid["source_config"]["seed"] != submitted["seed"]:
                            raise EvidenceError("Grid seed mismatch")
                        result["grid"] = {"grid_id": grid["grid_id"], "nodes": int(grid["metadata"]["nodes"]),
                                          "edges": int(grid["metadata"]["edges"]), "seed": grid["seed"]}
                    if key == "benchmark":
                        if value["source_sha256"] != entry["benchmark_source_sha256"]:
                            raise EvidenceError("Benchmark source mismatch")
                        result["benchmark"] = value
                    blobs[key] = data
                    artifact.update(state="available", size_bytes=len(data),
                                    download_url=f"/api/deployments/by-workflow/{deployment.workflow_id}/artifacts/{key}")
                except (OSError, ValueError, KeyError, TypeError):
                    pass
            result["artifacts"].append(artifact)
        if result["grid"] and result["benchmark"]:
            grid, benchmark = result["grid"], result["benchmark"]["upstream"]
            if (grid["grid_id"], grid["nodes"], grid["edges"]) != (benchmark["grid_id"], benchmark["nodes"], benchmark["edges"]):
                raise EvidenceError("Grid/benchmark association mismatch")
        return result, blobs
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        return {"state": "inaccessible", "message": "Capture recorded but currently inaccessible or its association could not be validated.",
                "execution_input": None, "artifacts": []}, {}
