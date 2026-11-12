"""Source-only, offline local packaging. Does not start/deploy any service.

Requires the four retained content-addressed inputs; never pulls or retags them.
Exports tracked build inputs only, with no private configuration or bootstrap.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ["docker", "--context", "desktop-linux"]
INPUTS = [
    "sha256:8a998103f1ea42cb1a8fd461e8e3fbf32c992d98b60c3147917f9cac95a758e1",
    "sha256:2c9ec04228b8e223d8fcd6adf86188b5a591e814c43eb25317ac95d33a20c36a",
    "python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e",
    "node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d",
]
DEPENDENCY_TAGS = {
    "ai-effect-staging-api:0458b93949a4": INPUTS[0],
    "ai-effect-staging-web:0458b93949a4": INPUTS[1],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--roles", choices=("api","web"), nargs="+", default=["api","web"],
                        help="Build only changed components; retain other verified images without relabeling")
    args = parser.parse_args()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("Commit the reviewed candidate before building")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    selected_inputs=[INPUTS[i] for i in range(4) if ("api" if i in {0,2} else "web") in args.roles]
    for reference in selected_inputs:
        subprocess.run(DOCKER + ["image", "inspect", reference], stdout=subprocess.DEVNULL, check=True)
    for tag, expected in DEPENDENCY_TAGS.items():
        if ("api" if "-api:" in tag else "web") not in args.roles:continue
        actual = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", tag]))[0]["Id"]
        if actual != expected:
            raise RuntimeError("Retained dependency tag drift: " + tag)
    args.records.mkdir(parents=True, exist_ok=True)
    scope = ["apps/api/app", "apps/web", "examples", "deploy/migrations", "deploy/restricted-beta",
             "deploy/staging/build/requirements.lock", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml"]
    archive = subprocess.check_output(["git", "archive", source, *scope], cwd=ROOT)
    # Do not include API tests in the runtime/context. No generated/untracked
    # file, environment file, synthetic bootstrap or local archive is exported.
    buf = io.BytesIO()
    manifest = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as original, tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as out:
        for member in original.getmembers():
            if not member.isfile() or member.name.startswith("apps/api/app/tests/"):
                continue
            data = original.extractfile(member).read()
            manifest[member.name] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = member.mode
            out.addfile(info, io.BytesIO(data))
    context = gzip.compress(buf.getvalue(), mtime=0)
    result = {"source_commit":source,"platform":"linux/amd64","inputs":selected_inputs,
              "context_sha256":hashlib.sha256(context).hexdigest(),"manifest":manifest,"images":[],"services_started":False}
    (args.records / "build-inputs.json").write_text(json.dumps(result, indent=2))
    for role in args.roles:
        tag = "ai-effect-beta-candidate-" + role + ":" + source[:12]
        if subprocess.run(DOCKER + ["image", "inspect", tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("Refusing to overwrite " + tag)
        with (args.records / (role + "-build.log")).open("xb") as log:
            subprocess.run(DOCKER + ["build", "--platform", "linux/amd64", "--pull=false", "--network=none",
                "--build-arg", "PORTAL_SOURCE_COMMIT=" + source, "-f", "deploy/restricted-beta/" + role.capitalize() + ".Dockerfile", "-t", tag, "-"],
                input=context, stdout=log, stderr=subprocess.STDOUT, check=True)
        image = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", tag]))[0]
        assert image["Config"]["Labels"]["org.opencontainers.image.revision"] == source
        result["images"].append({"role":role,"tag":tag,"image_id":image["Id"]})
        (args.records / "images.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != "manifest"}))


if __name__ == "__main__":
    main()
