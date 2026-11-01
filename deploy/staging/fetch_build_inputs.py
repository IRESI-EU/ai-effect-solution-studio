"""Fetch only content named by the committed Linux/amd64 input lock."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def fetch(url, destination, expected):
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Existing input has the wrong digest: {destination.name}")
        return
    with urlopen(url, timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != expected:
        raise RuntimeError(f"Downloaded input has the wrong digest: {destination.name}")
    with destination.open("xb") as output:
        output.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((Path(__file__).parent / "build/inputs.lock.json").read_text())
    for subdirectory in ("wheels", "tools"):
        (args.output / subdirectory).mkdir(parents=True, exist_ok=True)
    for wheel in lock["wheels"]:
        with urlopen(f"https://pypi.org/pypi/{wheel['package']}/{wheel['version']}/json", timeout=30) as response:
            metadata = json.load(response)
        matches = [entry for entry in metadata["urls"] if entry["filename"] == wheel["file"]
                   and entry["digests"]["sha256"] == wheel["sha256"]]
        if len(matches) != 1 or not matches[0]["url"].startswith("https://files.pythonhosted.org/"):
            raise RuntimeError(f"Locked wheel is unavailable: {wheel['file']}")
        fetch(matches[0]["url"], args.output / "wheels" / wheel["file"], wheel["sha256"])
    tool = lock["tool_archive"]
    fetch(tool["url"], args.output / "tools" / tool["file"], tool["sha256"])
    print(json.dumps({"verified_runtime_wheels": len(lock["wheels"]), "verified_pnpm": lock["pnpm"]}))
