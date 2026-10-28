"""Record exact local images before startup. Never executes an algorithm."""
import json
from pathlib import Path
import subprocess
import sys
import re
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[2]
private = Path(sys.argv[1]).resolve()
def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()
baseline = json.loads((private / "baseline-images.json").read_text())
assert all(docker("image", "inspect", "--format", "{{.Id}}", tag) == value for tag, value in baseline.items())
tags = {"postgres": "postgres:16", "redis": "redis:7-alpine",
    "seed-orchestrator": "ai-effect-aie18-orchestrator:integration-v2",
    "worker": "ai-effect-aie18-orchestrator:integration-v2",
    "seed-synth": "ai-effect-aie37-synth:qualification-v1",
    "seed-benchmark": "ai-effect-aie37-benchmark:qualification-v1",
    "api": "ai-effect-aie37-api:qualification-v3"}  # gitleaks:allow -- local Docker image tag, not a credential
pins = {name: docker("image", "inspect", "--format", "{{.Id}}", tag) for name, tag in tags.items()}
def digest(path):
    return sha256(path.read_bytes()).hexdigest()
adapter = sha256(b"".join((ROOT / path).read_bytes() for path in [
    "deploy/aie37/runtime.py", "deploy/aie37/capture_algorithms.py",
    "apps/api/app/services/parameter_values.py", "deploy/aie37/contracts.json"])).hexdigest()
value = {"version": "dutch-local-capture-v1", "source_revision": "ba598b2459f9986dac4e37dcc5d7d3298f25dc3a",
    "adapter_sha256": adapter, "contract_sha256": digest(ROOT / "apps/api/app/services/dutch_capture_contract.py"),
    "images": {role: {"id": pins["seed-" + role], "base_image": baseline["ai-effect-local-seed-" +
               role + ":ba598b2459f9"]} for role in ("synth", "benchmark")}}
(private / "runtime.json").write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")
lock_name = sys.argv[2] if len(sys.argv) > 2 else "images.lock.json"
assert re.fullmatch(r"images\.lock(?:\.v[1-9][0-9]*)?\.json", lock_name)
lock = private / lock_name
assert not lock.exists(), "Keep the original image lock; updates require a separate attributable review"
lock.write_text(json.dumps({"services": {name: {"image": image, "pull_policy": "never"} for name, image in pins.items()}}, indent=2), encoding="utf-8")
print(json.dumps({"runtime_recorded": True, "adapter_sha256": adapter, "images": pins, "workflow_submitted": False}))
