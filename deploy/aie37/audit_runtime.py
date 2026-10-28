"""Read-only source/image audit. No service execution, account or budget action."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()
def sha(data):
    return hashlib.sha256(data).hexdigest()
def remote_hashes(container, prefix, names):
    code = ("import hashlib,json; from pathlib import Path; print(json.dumps({p:hashlib.sha256((Path(" +
            repr(prefix) + ")/p).read_bytes()).hexdigest() for p in " + repr(names) + "}))")
    return json.loads(docker("exec", container, "python", "-c", code))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--lock-file", default="images.lock.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = args.private_dir.resolve()
    lock_path = (private / args.lock_file).resolve()
    assert lock_path.parent == private
    lock = json.loads(lock_path.read_text())["services"]
    for name, pin in lock.items():
        assert docker("inspect", "--format", "{{.Image}}", "ai-effect-aie37-" + name + "-1") == pin["image"]
    files = sorted(str(p.relative_to(ROOT / "apps/api")).replace("\\", "/")
                   for p in (ROOT / "apps/api/app").rglob("*.py"))
    actual = remote_hashes("ai-effect-aie37-api-1", "/app", files)
    assert actual == {name: sha((ROOT / "apps/api" / name).read_bytes()) for name in files}
    runtime_files = ["runtime.py", "capture_algorithms.py", "contracts.json", "parameter_values.py", "dutch_capture_contract.py"]
    source_files = {name: ROOT / "deploy/aie37" / name for name in runtime_files}
    for name in ("parameter_values.py", "dutch_capture_contract.py"):
        source_files[name] = ROOT / "apps/api/app/services" / name
    expected = {name: sha(path.read_bytes()) for name, path in source_files.items()}
    for role in ("synth", "benchmark"):
        assert remote_hashes("ai-effect-aie37-seed-" + role + "-1", "/app/qualification", runtime_files) == expected
    maintained = json.loads(docker("exec", "ai-effect-aie37-seed-orchestrator-1", "cat", "/app/integration-source.json"))
    assert remote_hashes("ai-effect-aie37-seed-orchestrator-1", "/app", list(maintained["source_files"])) == maintained["source_files"]
    for tag, image in json.loads((private / "baseline-images.json").read_text()).items():
        assert docker("image", "inspect", "--format", "{{.Id}}", tag) == image
    result = {"images": lock, "api_source_files": len(files),
              "api_source_inventory_sha256": sha(json.dumps(actual, sort_keys=True).encode()),
              "capture_files_sha256": expected, "maintained_wp3_commit": maintained["wp3_commit"],
              "maintained_files_verified": len(maintained["source_files"]),
              "baseline_images_unchanged": True, "workflow_requests_made": 0}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({key: value for key, value in result.items() if key not in ("images", "capture_files_sha256")}))
