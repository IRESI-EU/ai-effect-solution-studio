#!/usr/bin/env python3
"""Run each country workflow through Solution Studio and the WP3 orchestrator."""

from __future__ import annotations

import argparse
import base64
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from import_release_candidate import PACKAGES


def request_json(url: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="GET" if payload is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{error.code} from {url}: {detail}") from error


def service_id(container_name: str, operation_name: str) -> str:
    return f"svc-imported-{container_name}-{operation_name}".lower().replace("_", "-")


def run_input(case_name: str) -> dict | None:
    if case_name == "Germany":
        return None
    if case_name == "Portugal":
        return {
            "file_path": "/app/real_data.csv",
            "max_rows": 1000,
            "rename_columns": {"datetime": "timestamp"},
        }
    if case_name == "Denmark":
        return {
            "run_name": "chp_dumploads",
            "supplies": ["310-D::CHP"],
            "loads": ["716-D::Dumpload", "330-D::Heat dumpload"],
            "allow_hx": True,
            "allow_bypass": False,
            "max_extra_pipes": 1,
            "load_topology": "any",
        }
    if case_name == "Dutch":
        algorithm_path = (
            PACKAGES[-1]["blueprint"].parent.parent
            / "benchmarking/algorithms/algorithm_template.py"
        )
        algorithm = base64.b64encode(algorithm_path.read_bytes()).decode("ascii")
        return {
            "seed": 42,
            "loading_level": "M",
            "benchmark": {
                "max_steps": 100,
                "kpis": ["survival", "violations", "latency"],
                "scenarios": [
                    {"env_name": "l2rpn_case14_sandbox", "time_series_ids": [0]}
                ],
            },
            "algorithm": {"source_b64": algorithm},
        }
    raise ValueError(f"Unsupported case: {case_name}")


def studio_workflow(package: dict) -> dict:
    blueprint = json.loads(package["blueprint"].read_text(encoding="utf-8"))
    nodes = []
    edges = []
    for node in blueprint.get("nodes", []):
        operation_info = (node.get("operation_signature_list") or [{}])[0]
        operation = operation_info.get("operation_signature", {})
        container_name = node["container_name"]
        operation_name = operation["operation_name"]
        nodes.append(
            {
                "node_id": container_name,
                "service_id": service_id(container_name, operation_name),
                "container_name": container_name,
                "proto_uri": node.get("proto_uri"),
                "image": node.get("image"),
                "node_type": node.get("node_type", "MLModel"),
                "operation_name": operation_name,
                "input_message_name": operation.get("input_message_name"),
                "output_message_name": operation.get("output_message_name"),
            }
        )
        for target in operation_info.get("connected_to", []):
            edges.append({"source": container_name, "target": target["container_name"]})
    return {
        "name": f"{package['name']} production acceptance",
        "nodes": nodes,
        "edges": edges,
        "run_input": run_input(package["name"]),
    }


def summarize_tasks(tasks: dict) -> list[dict]:
    return [
        {
            "node": task.get("node_key"),
            "status": task.get("status"),
            "error": task.get("error"),
            "outputs": len(task.get("output_refs") or []),
        }
        for task in tasks.get("tasks", [])
    ]


def validate(package: dict, api_base: str, timeout: int) -> None:
    workflow = studio_workflow(package)
    preflight = request_json(f"{api_base}/workflows/runtime-preflight", workflow)
    if preflight.get("status") != "ready":
        raise RuntimeError(f"{package['name']} preflight blocked: {json.dumps(preflight)}")
    print(f"{package['name']}: preflight ready ({len(workflow['nodes'])} services)")

    submission = request_json(f"{api_base}/workflows/submit-to-orchestrator", workflow)
    workflow_id = submission.get("workflow_id")
    if not workflow_id:
        raise RuntimeError(f"{package['name']} submission returned no workflow_id: {submission}")
    print(f"{package['name']}: submitted {workflow_id}")

    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        status = request_json(f"{api_base}/orchestrator/workflows/{workflow_id}")
        current = str(status.get("status", "unknown")).lower()
        if current != last_status:
            print(f"{package['name']}: {current}")
            last_status = current
        if current == "completed":
            tasks = request_json(f"{api_base}/orchestrator/workflows/{workflow_id}/tasks")
            summary = summarize_tasks(tasks)
            if not summary or any(task["status"] != "completed" for task in summary):
                raise RuntimeError(f"{package['name']} task verification failed: {summary}")
            print(f"{package['name']}: PASS {json.dumps(summary)}")
            return
        if current in {"failed", "error", "cancelled"}:
            tasks = request_json(f"{api_base}/orchestrator/workflows/{workflow_id}/tasks")
            raise RuntimeError(f"{package['name']} failed: {summarize_tasks(tasks)}")
        time.sleep(2)
    tasks = request_json(f"{api_base}/orchestrator/workflows/{workflow_id}/tasks")
    raise TimeoutError(f"{package['name']} timed out: {summarize_tasks(tasks)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:13000/api")
    parser.add_argument(
        "--case",
        action="append",
        choices=[package["name"] for package in PACKAGES],
        dest="cases",
    )
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    selected = set(args.cases or [package["name"] for package in PACKAGES])
    for package in PACKAGES:
        if package["name"] in selected:
            validate(package, args.api_base, args.timeout)


if __name__ == "__main__":
    main()
