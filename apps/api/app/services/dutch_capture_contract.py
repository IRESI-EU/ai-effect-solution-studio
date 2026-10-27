"""Versioned local capture contract, shared by Studio and derived Dutch images.

No model/provider calls, database access or discovery. Only explicit IDs and
fixed filenames are accepted. Runtime writers use dedicated named volumes;
Studio mounts those volumes read-only.
"""
import hashlib
import json
import os
from pathlib import Path
import re

VERSION = "dutch-local-capture-v1"
SOURCE_REVISION = "ba598b2459f9986dac4e37dcc5d7d3298f25dc3a"
BASE_IMAGES = {
    "synth": "sha256:f14731e7c4bf273561ad02ab2a42895069543b7b6e0f0ffa2dec4fb56599b992",
    "benchmark": "sha256:590a5263c2b715159fb961da07a4f9a2821775aceede3d9e2f757e3daa9dc914",
}
NODE_KEYS = {"synth": "grid_synth_service:ConfigureAndSynthesize", "benchmark": "benchmark-runner:RunBenchmark"}
NAMES = {"configuration": "configuration.json", "grid": "grid.json", "network": "network.pandapower.json",
         "benchmark": "benchmark.json", "benchmark_source": "benchmark-source.json"}
MAX_BYTES = 4 * 1024 * 1024


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def task_id(role):
    return "task_" + sha(NODE_KEYS[role].encode())[:8]


def validate_ids(workflow, task):
    if not re.fullmatch(r"wf-[a-f0-9]{12}", workflow) or not re.fullmatch(r"task_[a-f0-9]{8}", task):
        raise ValueError("Invalid execution identity")


def confined_read(root, relative, checksum=None):
    root = Path(root)
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Invalid capture path")
    path = root / relative
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)):
        raise ValueError("Capture outside permitted root")
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError("Capture symlink rejected")
        cursor = cursor.parent
    if not resolved.is_file() or resolved.stat().st_size > MAX_BYTES:
        raise ValueError("Invalid capture file")
    with resolved.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or (checksum is not None and sha(data) != checksum):
        raise ValueError("Capture hash mismatch")
    return data


def output_ref(workflow, task, manifest_bytes):
    validate_ids(workflow, task)
    return {"protocol": "file", "format": "json", "uri": f"pilot-dutch://{workflow}/{task}/{sha(manifest_bytes)}"}


def parse_ref(ref, workflow):
    if ref.get("protocol") != "file" or ref.get("format") != "json":
        raise ValueError("Expected immutable local capture reference")
    match = re.fullmatch(r"pilot-dutch://(wf-[a-f0-9]{12})/(task_[a-f0-9]{8})/([a-f0-9]{64})", ref.get("uri", ""))
    if not match or match[1] != workflow:
        raise ValueError("Upstream workflow mismatch")
    return match[1], match[2], match[3]


def safe_benchmark(raw_bytes, upstream):
    raw = json.loads(raw_bytes)
    meta = raw["metadata"]
    return {"export": "Recorded benchmark; temporary container paths omitted", "source_sha256": sha(raw_bytes),
            "kpis": raw["kpis"], "episodes": raw["episodes"], "scenario_count": meta["scenario_count"],
            "upstream": {**upstream, "grid_id": meta["upstream_grid_id"], "nodes": meta["upstream_grid_nodes"],
                         "edges": meta["upstream_grid_edges"], "adapter": meta["upstream_grid_adapter"]}}


class CaptureStore:
    """First writer claims an execution; completion is published atomically last.

    A duplicate invocation returns its recorded reference, never recomputes. A
    different request with the same workflow/task identity is rejected. A crash
    or failed invocation cannot be silently retried or replace earlier evidence.
    """
    def __init__(self, root, role, provenance):
        self.root, self.role, self.provenance = Path(root), role, provenance

    def execute(self, request, compute):
        workflow, task = request["workflow_id"], request["task_id"]
        validate_ids(workflow, task)
        if task != task_id(self.role) or request["method"] != NODE_KEYS[self.role].split(":")[1]:
            raise ValueError("Unsupported operation identity")
        folder = self.root / workflow / task
        if (not folder.resolve().is_relative_to(self.root.resolve())
                or folder.is_symlink() or folder.parent.is_symlink()):
            raise ValueError("Capture symlink rejected")
        folder.mkdir(parents=True, exist_ok=True)
        request_bytes = encode(request)
        try:
            with (folder / "request.json").open("xb") as stream:
                stream.write(request_bytes)
        except FileExistsError:
            if confined_read(self.root, f"{workflow}/{task}/request.json") != request_bytes:
                raise ValueError("Execution identity reused with different inputs")
            manifest = confined_read(self.root, f"{workflow}/{task}/manifest.json")
            return output_ref(workflow, task, manifest)
        try:
            values, upstream = compute()
            files = {}
            for key, data in values.items():
                if key not in NAMES or len(data) > MAX_BYTES:
                    raise ValueError("Unsupported capture artifact")
                with (folder / NAMES[key]).open("xb") as stream:
                    stream.write(data)
                files[key] = {"sha256": sha(data), "bytes": len(data)}
            manifest = encode({"version": VERSION, "workflow_id": workflow, "task_id": task, "role": self.role,
                               "method": request["method"], "request_sha256": sha(request_bytes), "status": "complete",
                               "files": files, "upstream": upstream, "provenance": self.provenance})
            temporary = folder / "manifest.pending"
            with temporary.open("xb") as stream:
                stream.write(manifest)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, folder / "manifest.json")
            return output_ref(workflow, task, manifest)
        except Exception:
            with (folder / "failed.json").open("xb") as stream:
                stream.write(encode({"state": "failed", "message": "Execution or capture failed; no automatic retry"}))
            raise
