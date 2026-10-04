#!/usr/bin/env python3
"""Import and approve the pinned country-node packages in Solution Studio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


SERVER_ROOT = Path("/home/renew/ai-effect-country-nodes")

PACKAGES = (
    {
        "name": "Germany",
        "provider": "AI-EFFECT German Node",
        "blueprint": SERVER_ROOT / "ai-effect-wp3-main/use-cases/germany-node/export/blueprint.json",
        "dockerinfo": SERVER_ROOT / "ai-effect-wp3-main/use-cases/germany-node/export/dockerinfo.json",
        "runtime": {
            "data_provider1": ("data-provider", "8080"),
            "output_formatter1": ("output-formatter", "8080"),
            "villas_chronics1": ("villas-chronics", "8080"),
        },
    },
    {
        "name": "Portugal",
        "provider": "AI-EFFECT Portuguese Node",
        "blueprint": SERVER_ROOT / "ai-effect-wp3-main/use-cases/portugal-node-integrated/export/blueprint.json",
        "dockerinfo": SERVER_ROOT / "ai-effect-wp3-main/use-cases/portugal-node-integrated/export/dockerinfo.json",
        "runtime": {
            "data_generator1": ("pt-synthetic-data", "600"),
            "data_loader1": ("pt-data-provision", "600"),
            "feature_engineer1": ("pt-knowledge-store", "8000"),
            "model_trainer1": ("pt-synthetic-data", "600"),
        },
    },
    {
        "name": "Denmark",
        "provider": "AI-EFFECT Danish Node",
        "blueprint": SERVER_ROOT / "ai-effect-wp3-main/use-cases/denmark-node/export/blueprint.json",
        "dockerinfo": SERVER_ROOT / "ai-effect-wp3-main/use-cases/denmark-node/export/dockerinfo.json",
        "runtime": {
            "config_assistant1": ("config-assistant", "8080"),
            "draw_topology1": ("draw-topology", "8080"),
            "topology_generator1": ("topology-generator", "8080"),
        },
    },
    {
        "name": "Netherlands",
        "provider": "AI-EFFECT Dutch Node",
        "blueprint": SERVER_ROOT / "ai-effect-wp3-dutch/use-cases/dutch_node/ai4eu_pipeline_package/blueprint.json",
        "dockerinfo": SERVER_ROOT / "ai-effect-wp3-dutch/use-cases/dutch_node/ai4eu_pipeline_package/dockerinfo.json",
        "runtime": {
            "grid_synth_service": ("grid_synth_service", "8080"),
            "benchmark-runner": ("benchmark-runner", "8080"),
        },
    },
)


def request_json(url: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="GET" if payload is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def production_dockerinfo(path: Path, runtime: dict[str, tuple[str, str]]) -> dict:
    dockerinfo = json.loads(path.read_text(encoding="utf-8"))
    entries = dockerinfo.get("docker_info_list", [])
    seen = set()
    for entry in entries:
        container_name = entry.get("container_name")
        if container_name not in runtime:
            raise ValueError(f"No production runtime mapping for {container_name!r}")
        entry["ip_address"], entry["port"] = runtime[container_name]
        seen.add(container_name)
    missing = set(runtime) - seen
    if missing:
        raise ValueError(f"Runtime mapping not present in dockerinfo: {sorted(missing)}")
    return dockerinfo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:13000/api")
    parser.add_argument("--no-approve", action="store_true")
    args = parser.parse_args()

    for package in PACKAGES:
        blueprint = json.loads(package["blueprint"].read_text(encoding="utf-8"))
        dockerinfo = production_dockerinfo(package["dockerinfo"], package["runtime"])
        result = request_json(
            f"{args.api_base}/admin/import/wp3-package",
            {
                "provider": package["provider"],
                "category": f"{package['name']} Use Case",
                "trust_badge": "pending_review",
                "blueprint": blueprint,
                "dockerinfo": dockerinfo,
            },
        )
        service_ids = [service["id"] for service in result["services"]]
        if not args.no_approve:
            for service_id in service_ids:
                request_json(f"{args.api_base}/services/{service_id}/review/approve", {})
        state = "imported and approved" if not args.no_approve else "imported"
        print(f"{package['name']}: {len(service_ids)} services {state}")


if __name__ == "__main__":
    main()
