"""Offline-only automatic capture checks; synthetic computations and no live runs."""
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core.config import settings
from app.db import SessionLocal
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.local_dutch_execution import LocalDutchExecution
from app.models.solution import Solution
from app.models.user import User
from app.routers import deployment_results as routes
from app.services import local_dutch_capture as capture
from app.services import local_dutch_evidence as historical
from app.services.dutch_capture_contract import (BASE_IMAGES, SOURCE_REVISION, VERSION, NODE_KEYS, NAMES,
    CaptureStore, confined_read, encode, output_ref, safe_benchmark, sha, task_id)

WF = "wf-aabbccddeeff"
BASE = f"/deployments/by-workflow/{WF}"


@pytest.fixture
def auto(environment, monkeypatch, tmp_path):
    root = tmp_path / "runtime"
    root.mkdir()
    pins = {"version": VERSION, "source_revision": SOURCE_REVISION, "adapter_sha256": "a" * 64, "contract_sha256": "b" * 64,
            "images": {role: {"id": "sha256:" + ("c" if role == "synth" else "d") * 64, "base_image": digest} for role, digest in BASE_IMAGES.items()}}
    runtime = tmp_path / "identity.json"
    runtime.write_bytes(encode(pins))
    for key, value in {"local_dutch_evidence_scope": historical.SCOPE, "local_dutch_evidence_root": str(tmp_path / "history"),
                       "local_dutch_auto_capture_root": str(root), "local_dutch_capture_runtime": str(runtime),
                       "orchestrator_base_url": "http://seed-orchestrator:8000", "database_url": "postgresql://unused@127.0.0.1/design_ai_acceptance_dutch_seed"}.items():
        monkeypatch.setattr(settings, key, value)
    with SessionLocal() as db:
        db.add(Solution(id="auto-solution", name="Disposable auto fixture", nodes=[], edges=[], status="draft", created_by_user_id="designer", design_metadata={"run_input": {"seed": 43}}))
        db.commit()
    payload = {"solution_id": "auto-solution", "name": "Automatic fixture", "run_input": {"seed": 43}, "nodes": [], "edges": []}
    compiled = {"blueprint": {"nodes": [{"container_name": key.split(":")[0], "operation_signature_list": [{"operation_signature": {"operation_name": key.split(":")[1]}}]} for key in NODE_KEYS.values()]},
                "dockerinfo": {"docker_info_list": [{"container_name": "grid_synth_service", "ip_address": "seed-synth", "port": "8080"},
                                                     {"container_name": "benchmark-runner", "ip_address": "seed-benchmark", "port": "8080"}]},
                "inputs": [{"protocol": "inline", "format": "json", "uri": base64.b64encode(b'{"seed":43}').decode()}]}
    calls = []
    compiled["blueprint"]["nodes"][0]["operation_signature_list"][0]["connected_to"] = [
        {"container_name": "benchmark-runner", "operation_signature": {"operation_name": "RunBenchmark"}}]
    def submit(_):
        with SessionLocal() as db:
            record = db.query(LocalDutchExecution).filter(LocalDutchExecution.workflow_id.is_(None)).one()
            assert record.phase == "prepared" and record.submitted["request"]["run_input"] == {"seed": 43}
        calls.append("submit")
        return {"workflow_id": WF, "status": "running"}
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *_: {"status": "ready"})
    monkeypatch.setattr(main, "compile_to_wp3_payload", lambda *_: deepcopy(compiled))
    monkeypatch.setattr(main, "submit_to_orchestrator", submit)
    workflow = {"workflow_id": WF, "status": "completed"}
    tasks = [{"task_id": task_id(role), "node_key": key, "status": "completed"} for role, key in NODE_KEYS.items()]
    monkeypatch.setattr(routes, "get_workflow_status", lambda _: deepcopy(workflow))
    monkeypatch.setattr(routes, "get_workflow_tasks", lambda _: {"tasks": deepcopy(tasks)})
    monkeypatch.setattr(main, "get_workflow_status", lambda _: deepcopy(workflow))
    monkeypatch.setattr(main, "get_workflow_tasks", lambda _: {"tasks": deepcopy(tasks)})
    response = environment.post("/workflows/submit-to-orchestrator", json=payload)
    assert response.status_code == 200, response.text
    return {"client": environment, "root": root, "pins": pins, "payload": payload, "compiled": compiled,
            "calls": calls, "workflow": workflow, "tasks": tasks, "monkeypatch": monkeypatch}


def produce(auto, wid=WF, stale_upstream=None):
    pins, root = auto["pins"], auto["root"]
    def provenance(role):
        return {"version": VERSION, "source_revision": SOURCE_REVISION, "base_image": BASE_IMAGES[role],
                "adapter_sha256": pins["adapter_sha256"], "contract_sha256": pins["contract_sha256"]}
    request = {"workflow_id": wid, "task_id": task_id("synth"), "method": "ConfigureAndSynthesize", "inputs": auto["compiled"]["inputs"]}
    graph = b'{"fixture":"network"}'
    grid = {"grid_data": {"grid_id": "shared-grid-id", "seed": 43, "source_config": {"seed": 43},
                          "metadata": {"nodes": "3", "edges": "2"}, "pandapower_json": graph.decode()}}
    synth_ref = CaptureStore(root / "synth", "synth", provenance("synth")).execute(request,
        lambda: ({"configuration": encode({"config": {"seed": 43}}), "grid": encode(grid), "network": graph}, None))
    synth_bytes = (root / "synth" / wid / task_id("synth") / "manifest.json").read_bytes()
    synth_manifest = json.loads(synth_bytes)
    upstream = {"workflow_id": wid, "task_id": task_id("synth"), "manifest_sha256": sha(synth_bytes), "grid_sha256": synth_manifest["files"]["grid"]["sha256"]}
    raw = encode({"kpis": {"carbon_intensity": [655]}, "episodes": [{"episode_index": 0, "steps": 11, "runtime_seconds": .2, "overload_violations": 0, "terminated": True}],
                  "metadata": {"scenario_count": 1, "upstream_grid_id": "shared-grid-id", "upstream_grid_nodes": 3, "upstream_grid_edges": 2, "upstream_grid_adapter": "benchmark-service"}})
    benchmark_request = {"workflow_id": wid, "task_id": task_id("benchmark"), "method": "RunBenchmark", "inputs": [stale_upstream or synth_ref]}
    CaptureStore(root / "benchmark", "benchmark", provenance("benchmark")).execute(benchmark_request,
        lambda: ({"benchmark_source": raw, "benchmark": encode(safe_benchmark(raw, upstream))}, upstream))
    return synth_ref


def test_snapshot_precedes_submission_and_association_is_automatic(auto):
    produce(auto)
    result = auto["client"].get(BASE + "/results").json()
    assert result["evidence"]["state"] == "available"
    assert result["evidence"]["execution_input"] == {"seed": 43}
    assert result["evidence"]["grid"]["nodes"] == 3
    assert auto["calls"] == ["submit"]
    for artifact in result["evidence"]["artifacts"]:
        response = auto["client"].get(artifact["download_url"].removeprefix("/api"))
        assert response.status_code == 200 and sha(response.content) == artifact["sha256"]
        assert response.headers["x-content-type-options"] == "nosniff"
    assert not (auto["root"] / "index.json").exists()


def test_duplicate_status_reads_do_not_duplicate_or_overwrite(auto):
    produce(auto)
    before = {str(p): p.read_bytes() for p in auto["root"].rglob("*.json")}
    for _ in range(3):
        assert auto["client"].post("/deployments/sync-statuses").status_code == 200
        assert auto["client"].get(BASE + "/results").json()["evidence"]["state"] == "available"
    assert before == {str(p): p.read_bytes() for p in auto["root"].rglob("*.json")}
    with SessionLocal() as db:
        assert db.query(LocalDutchExecution).count() == 1
        assert set(db.query(LocalDutchExecution).one().collection["manifests"]) == {"synth", "benchmark"}
    assert auto["calls"] == ["submit"]


def test_later_draft_edit_does_not_change_execution(auto):
    produce(auto)
    before = auto["client"].get(BASE + "/results").json()["evidence"]
    with SessionLocal() as db:
        db.get(Solution, "auto-solution").design_metadata = {"run_input": {"seed": 42}}
        db.commit()
    assert auto["client"].get(BASE + "/results").json()["evidence"] == before


def test_missing_then_delayed_output_keeps_execution_completed(auto):
    result = auto["client"].get(BASE + "/results").json()
    assert result["workflow"]["status"] == "completed"
    assert result["evidence"]["state"] == "delayed"
    assert result["evidence"]["execution_input"] == {"seed": 43}
    produce(auto)
    assert auto["client"].get(BASE + "/results").json()["evidence"]["state"] == "available"
    assert auto["calls"] == ["submit"]


def test_pending_progress_and_failed_collection_are_distinct(auto):
    auto["workflow"]["status"] = "running"
    auto["tasks"][0]["status"] = "running"
    assert auto["client"].get(BASE + "/results").json()["evidence"]["state"] == "pending"
    auto["workflow"]["status"] = "completed"
    auto["tasks"][0]["status"] = "completed"
    folder = auto["root"] / "synth" / WF / task_id("synth")
    folder.mkdir(parents=True)
    (folder / "failed.json").write_bytes(encode({"state": "failed"}))
    result = auto["client"].get(BASE + "/results").json()
    assert result["workflow"]["status"] == "completed"
    assert result["evidence"]["state"] == "collection_failed"


def test_failed_execution_does_not_label_unproduced_outputs_pending(auto):
    auto["workflow"]["status"] = "failed"
    auto["tasks"][0]["status"] = "failed"
    auto["tasks"][1]["status"] = "pending"
    result = auto["client"].get(BASE + "/results").json()
    assert result["tasks"][0]["status"] == "failed"
    assert result["evidence"]["state"] == "unavailable"
    assert all(a["state"] == "not_recorded" for a in result["evidence"]["artifacts"])
    assert auto["calls"] == ["submit"]


def test_same_seed_and_shared_grid_id_do_not_authorize_stale_upstream(auto):
    old_ref = produce(auto, "wf-112233445566")
    produce(auto, stale_upstream=old_ref)
    result = auto["client"].get(BASE + "/results").json()["evidence"]
    assert result["state"] == "collection_failed"
    assert result["benchmark"] is None
    assert auto["client"].get(BASE + "/artifacts/benchmark").status_code == 410


@pytest.mark.parametrize("key", ["workflow_id", "task_id", "request_sha256"])
def test_reject_mismatched_manifest(auto, key):
    produce(auto)
    path = auto["root"] / "synth" / WF / task_id("synth") / "manifest.json"
    value = json.loads(path.read_bytes())
    value[key] = "wrong"
    path.write_bytes(encode(value))
    assert auto["client"].get(BASE + "/results").json()["evidence"]["state"] == "collection_failed"


def test_changed_previously_accepted_capture_is_rejected(auto):
    produce(auto)
    auto["client"].get(BASE + "/results")
    path = auto["root"] / "synth" / WF / task_id("synth") / "manifest.json"
    value = json.loads(path.read_bytes())
    value["unrecognized_change"] = True
    path.write_bytes(encode(value))
    assert auto["client"].get(BASE + "/artifacts/network").status_code == 410


def test_overlapping_runs_and_idempotent_runtime_writer(auto):
    with ThreadPoolExecutor(max_workers=2) as pool:
        refs = list(pool.map(lambda wid: produce(auto, wid), [WF, "wf-112233445566"]))
    assert refs[0] != refs[1]
    assert produce(auto) == refs[0]  # Same request returns the prior output, no compute.
    folder = auto["root"] / "synth"
    store = CaptureStore(folder, "synth", {})
    changed = {"workflow_id": WF, "task_id": task_id("synth"), "method": "ConfigureAndSynthesize", "inputs": []}
    with pytest.raises(ValueError, match="different inputs"):
        store.execute(changed, lambda: pytest.fail("Must not recompute"))


@pytest.mark.parametrize("suffix", ["/results", "/artifacts/configuration", "/artifacts/benchmark"])
def test_ownership_and_anonymous_access(auto, suffix):
    produce(auto)
    with TestClient(app) as anonymous:
        assert anonymous.get(BASE + suffix).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: User(id="other", role="solution_designer", status="active")
    assert auto["client"].get(BASE + suffix).status_code == 403


def test_capture_path_and_symlink_restrictions(auto, tmp_path):
    produce(auto)
    with pytest.raises(ValueError):
        confined_read(auto["root"], "../identity.json")
    target = auto["root"] / "synth" / WF / task_id("synth") / "network.pandapower.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)
    assert auto["client"].get(BASE + "/artifacts/network").status_code == 410
    assert auto["client"].get(BASE + "/artifacts/request.json").status_code == 404


def test_runtime_failure_cannot_silently_retry(auto):
    request = {"workflow_id": WF, "task_id": task_id("synth"), "method": "ConfigureAndSynthesize", "inputs": []}
    store = CaptureStore(auto["root"] / "synth", "synth", {})
    def fail():
        raise RuntimeError("Simulated computation/capture failure")
    with pytest.raises(RuntimeError):
        store.execute(request, fail)
    with pytest.raises(FileNotFoundError):
        store.execute(request, lambda: pytest.fail("Must not retry execution"))
    assert (auto["root"] / "synth" / WF / task_id("synth") / "failed.json").is_file()


@pytest.mark.parametrize("mutation", ["chain", "input", "target"])
def test_invalid_local_submission_never_executes(auto, mutation):
    compiled = auto["compiled"]
    if mutation == "chain":
        compiled["blueprint"]["nodes"][0]["operation_signature_list"][0]["connected_to"] = []
    elif mutation == "input":
        compiled["inputs"][0]["uri"] = base64.b64encode(b'{"seed":42}').decode()
    else:
        compiled["dockerinfo"]["docker_info_list"][0]["ip_address"] = "different-runtime"
    assert auto["client"].post("/workflows/submit-to-orchestrator", json=auto["payload"]).status_code in (409, 422)
    assert auto["calls"] == ["submit"]
    with SessionLocal() as db:
        assert db.query(LocalDutchExecution).count() == 1
