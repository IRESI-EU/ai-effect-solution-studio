"""Build separate, uniquely tagged local images; never starts application services."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ["docker", "--context", "desktop-linux"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    args = parser.parse_args()
    args.records.mkdir(parents=True, exist_ok=True)
    scope = ["apps", "deploy/staging", "deploy/migrations", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".dockerignore"]
    changes = subprocess.check_output(["git", "status", "--porcelain", "--", *scope], cwd=ROOT, text=True).strip()
    if changes:
        raise RuntimeError("Commit/review the application and build inputs before identifying an image source")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {"source_commit": source, "platform": "linux/amd64", "services_started": False, "images": []}
    for role, dockerfile in [("api", "Api.Dockerfile"), ("web", "Web.Dockerfile")]:
        tag = "ai-effect-staging-" + role + ":" + source[:12]
        exists = subprocess.run(DOCKER + ["image", "inspect", tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if exists.returncode == 0:
            raise RuntimeError("Refusing to overwrite an existing tag: " + tag)
        log = args.records / (role + "-image-build.log")
        with log.open("xb") as stream:
            # Only frozen web dependency acquisition needs registry networking;
            # its test/typegen/typecheck/build RUN steps explicitly use none.
            subprocess.run(DOCKER + ["build", "--platform", "linux/amd64", "--pull=false", "--network", "default" if role == "web" else "none",
                "--build-context", "locked_inputs=" + str(args.inputs.resolve()),
                "--build-arg", "PORTAL_SOURCE_COMMIT=" + source,
                "--metadata-file", str((args.records / (role + "-build-metadata.json")).resolve()),
                "-f", "deploy/staging/build/" + dockerfile, "-t", tag, "."],
                cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
        value = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", tag], text=True))[0]
        if value["Config"]["Labels"]["org.opencontainers.image.revision"] != source:
            raise RuntimeError("Built image source label differs")
        result["images"].append({"role": role, "tag": tag, "image_id": value["Id"], "platform": value["Os"] + "/" + value["Architecture"]})
    for role, image in [("postgres", "sha256:5d143123fdf80462d1778cd4f24b9f7ca13c87174bca19141fb194c5a1ebca59"),
                        ("gateway", "sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10")]:
        value = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", image], text=True))[0]
        result["images"].append({"role": role, "image_id": value["Id"], "platform": value["Os"] + "/" + value["Architecture"]})
    (args.records / "images.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
