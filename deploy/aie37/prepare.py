"""Prepare a NEW private profile and immutable local image lock; never submit.

Requires the existing pinned images and the private Dutch catalogue export.
No credentials, provider allowances or existing volumes are copied or reset.
"""
import argparse
import json
from pathlib import Path
import secrets
import subprocess

BASES = {
    "ai-effect-local-seed-synth:ba598b2459f9": "sha256:f14731e7c4bf273561ad02ab2a42895069543b7b6e0f0ffa2dec4fb56599b992",
    "ai-effect-local-seed-benchmark:ba598b2459f9": "sha256:590a5263c2b715159fb961da07a4f9a2821775aceede3d9e2f757e3daa9dc914",
}
def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--source-metadata", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source_metadata.read_text(encoding="utf-8"))
    services = [s for s in source["services"] if s["operation_name"] in {"ConfigureAndSynthesize", "RunBenchmark"}]
    assert len(services) == 2 and all(s["status"] in {"approved", "validated"} for s in services)
    assert all(docker("image", "inspect", "--format", "{{.Id}}", tag) == digest for tag, digest in BASES.items())
    # Existing maintained runtime must carry its source inventory.
    image = "ai-effect-aie18-orchestrator:integration-v2"
    assert docker("image", "inspect", "--format", "{{.Id}}", image).startswith("sha256:")
    private = args.private_dir.resolve()
    private.mkdir(parents=True, exist_ok=False)
    password = secrets.token_hex(24)
    (private / "postgres.env").write_text(
        "POSTGRES_DB=design_aie37_qualification\nPOSTGRES_USER=aie37\nPOSTGRES_PASSWORD=" + password + "\n", encoding="utf-8")
    (private / "api.env").write_text(
        "DATABASE_URL=postgresql+psycopg://aie37:" + password + "@postgres:5432/design_aie37_qualification\n"
        "SESSION_COOKIE_NAME=ai_effect_aie37_session\nSECURE_COOKIES=false\n", encoding="utf-8")
    (private / "source-services.json").write_text(json.dumps(services, indent=2), encoding="utf-8")
    (private / "runtime.json").write_text("{}", encoding="utf-8")
    tags = ["postgres:16", "redis:7-alpine", image, *BASES]
    (private / "baseline-images.json").write_text(json.dumps({
        tag: docker("image", "inspect", "--format", "{{.Id}}", tag) for tag in tags}, indent=2), encoding="utf-8")
    print(json.dumps({"private_directory": str(private), "services": 2, "provider_enabled": False, "execution_submitted": False}))
