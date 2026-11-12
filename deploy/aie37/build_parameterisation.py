"""Build only source layers over retained local dependencies; never start jobs.

Exports committed files, refuses dirty source or reused tags, and disables pulls
and build networking. All records go to an explicit private directory.
"""
import argparse
import hashlib
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
WP3 = "0221b7ecd4a2d5f072de640350ebc599df22131a"
DOCKER = ["docker", "--context", "desktop-linux"]
BASES = {
    "synth": ("ai-effect-local-seed-synth:ba598b2459f9", "sha256:f14731e7c4bf273561ad02ab2a42895069543b7b6e0f0ffa2dec4fb56599b992"),
    "benchmark": ("ai-effect-local-seed-benchmark:ba598b2459f9", "sha256:590a5263c2b715159fb961da07a4f9a2821775aceede3d9e2f757e3daa9dc914"),
    "wp3": ("ai-effect-aie18-orchestrator:integration-v2", "sha256:0cf40e15edc3508d26f907fc7619980d47f31f16b9ddf7be4429c832db717f06"),
}


def git(repo, *args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", "-C", str(repo), *args])


def clean_archive(data):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(data)) as original, tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as out:
        for item in original:
            if item.isfile():
                payload = original.extractfile(item).read()
                entry = tarfile.TarInfo(item.name)
                entry.size, entry.mode = len(payload), item.mode
                out.addfile(entry, io.BytesIO(payload))
    return gzip.compress(buffer.getvalue(), mtime=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp3-checkout", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    args = parser.parse_args()
    if git(ROOT, "status", "--porcelain").strip():
        raise RuntimeError("Commit the reviewed source before packaging")
    if git(args.wp3_checkout, "rev-parse", "HEAD").decode().strip() != WP3:
        raise RuntimeError("Wrong maintained WP3 revision")
    source = git(ROOT, "rev-parse", "HEAD").decode().strip()
    args.records.mkdir(parents=True, exist_ok=True)
    paths = ["deploy/aie37/runtime.py", "deploy/aie37/capture_algorithms.py",
        "deploy/aie37/contracts.json", "deploy/aie37/Runtime.Dockerfile",
        "apps/api/app/services/dutch_capture_contract.py", "apps/api/app/services/parameter_values.py"]
    contexts = {}
    archive = git(ROOT, "archive", source, *paths)
    contexts["synth"] = contexts["benchmark"] = clean_archive(archive)
    buffer = io.BytesIO()
    wp3_archive = git(args.wp3_checkout, "archive", WP3, "orchestrator/src")
    dockerfile = ("FROM " + BASES["wp3"][0] + "\n"
        "LABEL org.opencontainers.image.revision=" + WP3 + "\n"
        "COPY orchestrator/src/ /app/src/\n").encode()
    with tarfile.open(fileobj=io.BytesIO(wp3_archive)) as original, tarfile.open(fileobj=buffer, mode="w") as out:
        for entry in original:
            if entry.isfile():
                data = original.extractfile(entry).read()
                out.addfile(entry, io.BytesIO(data))
        entry = tarfile.TarInfo("Dockerfile")
        entry.size = len(dockerfile)
        out.addfile(entry, io.BytesIO(dockerfile))
    contexts["wp3"] = clean_archive(buffer.getvalue())
    result = {"portal_source": source, "wp3_source": WP3, "images": {}, "started": False}
    for role, (tag, identity) in BASES.items():
        actual = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", tag]))[0]["Id"]
        if actual != identity:
            raise RuntimeError("Retained input drift: " + role)
        output = "ai-effect-parameter-" + role + ":" + source[:12]
        if subprocess.run(DOCKER + ["image", "inspect", output], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("Refusing to overwrite " + output)
        command = DOCKER + ["build", "--pull=false", "--network=none", "--platform", "linux/amd64", "-t", output]
        if role != "wp3":
            command += ["-f", "deploy/aie37/Runtime.Dockerfile", "--build-arg", "BASE_IMAGE=" + tag,
                        "--build-arg", "CAPTURE_ROLE=" + role]
        with (args.records / (role + "-build.log")).open("xb") as log:
            subprocess.run(command + ["-"], input=contexts[role], stdout=log, stderr=subprocess.STDOUT, check=True)
        built = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", output]))[0]
        result["images"][role] = {"tag": output, "id": built["Id"], "base": identity,
            "context_sha256": hashlib.sha256(contexts[role]).hexdigest()}
        (args.records / "images.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
