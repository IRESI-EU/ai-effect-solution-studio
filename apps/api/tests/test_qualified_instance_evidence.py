"""OFFLINE regressions for preserved-run evidence; all runtime/provider work is doubled."""
from copy import deepcopy
import json
import pytest
from fastapi import HTTPException
from app import main
from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.models.execution_submission import ExecutionSubmission
from app.models.local_dutch_execution import LocalDutchExecution
from app.models.solution import Solution
from app.models.user import User
from app.services import local_dutch_capture as capture, orchestrator_adapter
from app.routers import deployment_results
from app.services.dutch_capture_contract import BASE_IMAGES, NODE_KEYS, SOURCE_REVISION, VERSION, CaptureStore, encode, safe_benchmark, sha, task_id
from test_goal_to_results import qualified, prepared, execute, WF


@pytest.fixture
def recorded(qualified, monkeypatch):
    q = qualified
    base, draft, review = prepared(q, monkeypatch)
    assert execute(q, base, review).status_code == 200  # OFFLINE submit double only.
    snapshot = q["db"].query(LocalDutchExecution).one().submitted
    root = q["path"] / "capture"
    def provenance(role):
        return {"version": VERSION, "source_revision": SOURCE_REVISION, "base_image": BASE_IMAGES[role],
            "adapter_sha256": q["pins"]["adapter_sha256"], "contract_sha256": q["pins"]["contract_sha256"]}
    graph = b'{"OFFLINE graph":true}'
    grid = {"grid_data": {"grid_id": "OFFLINE-grid", "seed": 43, "source_config": {"seed": 43},
        "metadata": {"nodes": "3", "edges": "2"}, "pandapower_json": graph.decode()}}
    reference = CaptureStore(root / "synth", "synth", provenance("synth")).execute(
        {"workflow_id": WF, "task_id": task_id("synth"), "method": "ConfigureAndSynthesize", "inputs": [],
         "configuration": snapshot["task_configurations"][NODE_KEYS["synth"]]},
        lambda: ({"configuration": encode({"config": {"seed": 43}, "algorithm_consumed": {"seed": 43}}),
                  "grid": encode(grid), "network": graph}, None))
    manifest = (root / "synth" / WF / task_id("synth") / "manifest.json").read_bytes()
    upstream = {"workflow_id": WF, "task_id": task_id("synth"), "manifest_sha256": sha(manifest),
        "grid_sha256": json.loads(manifest)["files"]["grid"]["sha256"]}
    raw = encode({"kpis": {}, "episodes": [], "metadata": {"scenario_count": 1,
        "upstream_grid_id": "OFFLINE-grid", "upstream_grid_nodes": 3, "upstream_grid_edges": 2,
        "upstream_grid_adapter": "benchmark-service"}})
    benchmark = CaptureStore(root / "benchmark", "benchmark", provenance("benchmark")).execute(
        {"workflow_id": WF, "task_id": task_id("benchmark"), "method": "RunBenchmark", "inputs": [reference]},
        lambda: ({"benchmark_source": raw, "benchmark": encode(safe_benchmark(raw, upstream))}, upstream))
    q["tasks"][0].update(input_refs=[], output_refs=[reference])
    q["tasks"][1].update(input_refs=[reference], output_refs=[benchmark])
    monkeypatch.setattr(orchestrator_adapter, "get_workflow_status", lambda _: deepcopy(q["workflow"]))
    monkeypatch.setattr(orchestrator_adapter, "get_workflow_tasks", lambda _: {"tasks": deepcopy(q["tasks"])})
    q.update(root=root, draft=draft, proof_url=f"/workflows/{WF}/instance-evidence", results_url=f"/deployments/by-workflow/{WF}/results")
    return q


def proof(q):
    response = q["client"].get(q["proof_url"])
    assert response.status_code == 200, response.text
    return response.json()


def by_instance(value):
    return {role: item for item in value["instances"] for role, key in NODE_KEYS.items() if item["node_key"] == key}


def test_demo_flag_uses_same_capture_and_separate_instance_verdicts(recorded):
    q = recorded
    assert settings.design_ai_enabled and not capture.qualification_enabled()
    values = proof(q); nodes = by_instance(values)
    assert values["state"] == "available" and values["workflow_id"] == WF
    assert values["submission_id"] == q["db"].query(ExecutionSubmission).one().id
    assert nodes["synth"]["algorithm_consumed"] == {"seed": 43}
    assert not nodes["synth"]["input_binding_verified"]
    assert nodes["benchmark"]["algorithm_consumed"] is None and nodes["benchmark"]["input_binding_verified"]
    result = q["client"].get(q["results_url"]).json()
    assert result["evidence"]["source"] == values["source"]
    assert values["historical"] and result["evidence"]["historical"]
    assert nodes["synth"]["task_id"] == task_id("synth") and nodes["benchmark"]["task_id"] == task_id("benchmark")
    assert len(q["calls"]) == 1


def test_pending_benchmark_does_not_hide_generator_or_inherit_its_success(recorded):
    q = recorded; q["workflow"]["status"] = "running"; q["tasks"][1]["status"] = "running"
    nodes = by_instance(proof(q))
    assert nodes["synth"]["state"] == "available" and nodes["synth"]["algorithm_consumed"] == {"seed": 43}
    assert nodes["benchmark"]["state"] == "pending" and not nodes["benchmark"].get("input_binding_verified")
    q["workflow"]["status"] = "completed"; q["tasks"][1]["status"] = "completed"
    assert q["client"].get(q["results_url"]).json()["evidence"]["state"] == "available"
    assert by_instance(proof(q))["benchmark"]["input_binding_verified"]


@pytest.mark.parametrize("damage", ["missing", "corrupt", "unreadable"])
def test_one_invalid_capture_does_not_verify_both_instances(recorded, monkeypatch, damage):
    q = recorded; assert proof(q)["state"] == "available"
    path = q["root"] / "benchmark" / WF / task_id("benchmark") / "benchmark.json"
    if damage == "missing": path.unlink()
    elif damage == "corrupt": path.write_bytes(b"{}")
    else:
        original = capture.confined_read
        def denied(root, relative, checksum=None):
            if relative.endswith("/benchmark.json"): raise PermissionError("OFFLINE unreadable capture double")
            return original(root, relative, checksum)
        monkeypatch.setattr(capture, "confined_read", denied)
    values = proof(q); nodes = by_instance(values)
    assert nodes["synth"]["state"] == "available"
    assert nodes["benchmark"]["state"] == ("invalid" if damage == "corrupt" else "inaccessible")
    assert not nodes["benchmark"].get("input_binding_verified") and nodes["benchmark"]["message"]
    assert q["client"].get(f"/deployments/by-workflow/{WF}/artifacts/benchmark").status_code == 410


@pytest.mark.parametrize("damage", ["capture_workflow", "submission", "instance_task", "observation_task", "observation_workflow", "task_workflow", "submission_missing"])
def test_conflicting_workflow_submission_and_task_associations_are_rejected(recorded, monkeypatch, damage):
    q = recorded
    if damage == "capture_workflow":
        path = q["root"] / "synth" / WF / task_id("synth") / "manifest.json"
        value = json.loads(path.read_bytes()); value["workflow_id"] = "wf-ffeeddccbbaa"; path.write_bytes(encode(value))
    elif damage in ["submission", "submission_missing"]:
        row = q["db"].query(LocalDutchExecution).one()
        value = deepcopy(row.submitted)
        if damage == "submission":value["request"]["submission_id"] = "different-submission"
        else:value["request"].pop("submission_id")
        row.submitted = value; q["db"].commit()
        monkeypatch.setattr(capture, "collect", lambda *_args, **_kwargs: pytest.fail("Conflicting submission must not inspect artifacts"))
    elif damage == "instance_task":
        row = q["db"].query(ExecutionSubmission).one()
        value = deepcopy(row.submitted); value["compiled"]["solution_studio_metadata"]["execution_instances"][0]["task_id"] = task_id("benchmark")
        row.submitted = value; row.submitted_sha256 = sha(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()); q["db"].commit()
    elif damage == "task_workflow":
        q["tasks"][0]["workflow_id"] = "wf-ffeeddccbbaa"
    elif damage == "observation_workflow":
        q["workflow"]["workflow_id"] = "wf-ffeeddccbbaa"
    else:
        assert proof(q)["state"] == "available"
        row = q["db"].query(LocalDutchExecution).one()
        value = deepcopy(row.collection); value["terminal_observation"]["tasks"][0]["task_id"] = "task_ffffffff"
        value["terminal_observation_sha256"] = sha(encode(value["terminal_observation"]))
        row.collection = value; q["db"].commit()
        q["tasks"][0]["task_id"] = "task_ffffffff"
    value = proof(q)
    assert value["state"] != "available"
    assert not any(item.get("algorithm_consumed") for item in value["instances"])
    assert value.get("message")


def test_historical_observation_needs_no_live_runtime_but_files_are_rechecked(recorded, monkeypatch):
    q = recorded; assert proof(q)["state"] == "available"
    def no_live(_): pytest.fail("Recorded terminal evidence must not depend on live runtime")
    for module in [orchestrator_adapter, deployment_results]:
        monkeypatch.setattr(module, "get_workflow_status", no_live)
        monkeypatch.setattr(module, "get_workflow_tasks", no_live)
    value = proof(q)
    assert value["state"] == "available" and value["observation_source"] == "recorded terminal observation for this run"
    assert q["client"].get(q["results_url"]).json()["status_source"] == value["observation_source"]
    (q["root"] / "synth" / WF / task_id("synth") / "grid.json").write_bytes(b"corrupt")
    assert proof(q)["state"] != "available"


def test_outage_without_valid_recorded_observation_is_not_verified(recorded, monkeypatch):
    q = recorded
    def outage(_): raise HTTPException(503, "OFFLINE outage double")
    monkeypatch.setattr(orchestrator_adapter, "get_workflow_status", outage)
    value = proof(q)
    assert value["state"] != "available"
    assert all(item["state"] == "unavailable" and not item.get("algorithm_consumed") for item in value["instances"])


def test_legacy_qualification_and_current_saved_edits_do_not_change_history(recorded, monkeypatch):
    q = recorded; monkeypatch.setattr(settings, "design_ai_enabled", False)
    assert capture.qualification_enabled()
    assert proof(q)["state"] == "available"
    solution = q["db"].get(Solution, q["draft"]["saved_solution_id"])
    nodes = deepcopy(solution.nodes)
    next(node for node in nodes if node.get("data", {}).get("service", {}).get("operation_name") == "ConfigureAndSynthesize")["data"]["configuration"]["parameters"]["seed"] = 42
    solution.nodes = nodes; q["db"].commit()
    assert by_instance(proof(q))["synth"]["algorithm_consumed"] == {"seed": 43}


def test_ownership_is_checked_before_capture_inspection(recorded, monkeypatch):
    q = recorded
    monkeypatch.setattr(capture, "collect", lambda *_args, **_kwargs: pytest.fail("Must authorize before capture inspection"))
    main.app.dependency_overrides[get_current_user] = lambda: q["db"].get(User, "other")
    try:
        assert q["client"].get(q["proof_url"]).status_code == 403
        assert q["client"].get(f"/workflows/{WF}/submitted-configuration").status_code == 403
        assert q["client"].get(q["results_url"]).status_code == 403
        assert q["client"].get(f"/deployments/by-workflow/{WF}/artifacts/grid").status_code == 403
    finally:
        main.app.dependency_overrides.pop(get_current_user)



def test_other_profile_cannot_enable_qualified_historical_reader(recorded, monkeypatch):
    q = recorded
    monkeypatch.setattr(settings, "database_url", "postgresql://test@postgres/design_aie38_offline_20261028")
    monkeypatch.setattr(capture, "collect", lambda *_args, **_kwargs: pytest.fail("Other profile must not read qualified captures"))
    value = proof(q)
    assert value["state"] == "unavailable" and "not enabled" in value["message"]


def test_semantically_invalid_grid_does_not_publish_consumed_parameters(recorded):
    q = recorded
    folder = q["root"] / "synth" / WF / task_id("synth")
    grid = json.loads((folder / "grid.json").read_bytes()); grid["grid_data"]["seed"] = 42
    raw = encode(grid); (folder / "grid.json").write_bytes(raw)
    manifest = json.loads((folder / "manifest.json").read_bytes()); manifest["files"]["grid"]["sha256"] = sha(raw)
    (folder / "manifest.json").write_bytes(encode(manifest))
    result = q["client"].get(q["results_url"]).json()["evidence"]
    assert result["state"] != "available" and not result.get("algorithm_consumed")
    assert "verified at" not in result["input_source"]
    assert not by_instance(proof(q))["synth"].get("algorithm_consumed")
