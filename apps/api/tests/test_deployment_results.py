"""Focused offline capture/authorization checks; no provider or runtime requests."""
import base64
from copy import deepcopy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import SessionLocal
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.deployment import Deployment
from app.models.solution import Solution
from app.models.user import User
from app.routers import deployment_results as routes
from app.services import local_dutch_evidence as evidence

WF = "wf-123456abcdef"
BASE = f"/deployments/by-workflow/{WF}"


@pytest.fixture
def capture(environment, monkeypatch, tmp_path):
    root = tmp_path / "captures"
    folder = root / WF
    folder.mkdir(parents=True)
    workflow = {"workflow_id": WF, "status": "completed", "created_at": "2026-10-18T12:00:00Z", "updated_at": "2026-10-18T12:00:10Z"}
    refs = [{"protocol": "grpc", "format": "GetGridData", "uri": "seed-synth:50051"}]
    tasks = [{"task_id": "task-one", "workflow_id": WF, "node_key": "grid_synth_service:ConfigureAndSynthesize", "status": "completed",
              "created_at": workflow["created_at"], "updated_at": workflow["updated_at"],
              "input_refs": [{"protocol": "inline", "format": "json", "uri": base64.b64encode(b'{"seed":43}').decode()}], "output_refs": refs},
             {"task_id": "task-two", "workflow_id": WF, "node_key": "benchmark-runner:RunBenchmark", "status": "completed",
              "created_at": workflow["created_at"], "updated_at": workflow["updated_at"], "input_refs": refs,
              "output_refs": [{"protocol": "grpc", "format": "GetBenchmarkResult", "uri": "seed-benchmark:50051"}]}]
    checksums = {}

    def write(key, value):
        data = json.dumps(value).encode()
        (folder / evidence.FILES[key][0]).write_bytes(data)
        checksums[key] = hashlib.sha256(data).hexdigest()

    write("tasks", tasks)
    write("configuration", {"config": {"seed": 43}})
    write("grid", {"grid_data": {"seed": 43, "source_config": {"seed": 43}, "grid_id": "fixture-grid", "metadata": {"nodes": "3", "edges": "2"}}})
    write("network", {"fixture": "graph, never executed"})
    bench_source = "a" * 64
    write("benchmark", {"source_sha256": bench_source, "kpis": {"carbon_intensity": [655]}, "episodes": [{"runtime_seconds": 0.2}],
                        "scenario_count": 1, "upstream": {"grid_id": "fixture-grid", "nodes": 3, "edges": 2}})
    report = {"workflow_id": WF, "status": workflow, "seed": 43,
              "generator": {"source_revision": evidence.REVISION, "image_id": evidence.IMAGES["seed-synth"],
                            "artifacts": {evidence.FILES[k][0]: {"sha256": checksums[k]} for k in ("configuration", "grid", "network")}},
              "artifact_sha256": {"tasks.json": checksums["tasks"], "benchmark-result.json": bench_source}}
    write("report", report)
    entry = {"solution_id": "executed-solution", "owner_user_id": "designer", "source_revision": evidence.REVISION,
             "images": evidence.IMAGES, "sha256": checksums, "benchmark_source_sha256": bench_source}
    index = {"scope": evidence.SCOPE, "workflows": {WF: entry}}

    def reindex():
        (root / "index.json").write_text(json.dumps(index))

    reindex()
    monkeypatch.setattr(settings, "local_dutch_evidence_root", str(root))
    monkeypatch.setattr(settings, "local_dutch_evidence_scope", evidence.SCOPE)
    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://unused@127.0.0.1/design_ai_acceptance_dutch_seed")
    monkeypatch.setattr(settings, "orchestrator_base_url", "http://seed-orchestrator:8000")
    monkeypatch.setattr(routes, "get_workflow_status", lambda _: deepcopy(workflow))
    monkeypatch.setattr(routes, "get_workflow_tasks", lambda _: {"tasks": deepcopy(tasks)})
    with SessionLocal() as db:
        db.add(Solution(id="executed-solution", name="Disposable fixture", status="draft", nodes=[], edges=[],
                        created_by_user_id="designer", design_metadata={"run_input": {"seed": 43}}))
        db.flush()
        db.add(Deployment(id="deployment", workflow_id=WF, solution_id="executed-solution", name="Fixture run", status="completed", created_by_user_id="designer"))
        db.commit()
    return {"client": environment, "root": root, "folder": folder, "entry": entry, "index": index,
            "write": write, "reindex": reindex, "workflow": workflow, "tasks": tasks}


def test_own_capture_and_safe_exact_download(capture):
    client = capture["client"]
    result = client.get(BASE + "/results")
    assert result.status_code == 200
    value = result.json()["evidence"]
    assert value["execution_input"] == {"seed": 43}
    assert value["grid"] == {"grid_id": "fixture-grid", "nodes": 3, "edges": 2, "seed": 43}
    for item in value["artifacts"]:
        response = client.get(item["download_url"].removeprefix("/api"))
        assert response.status_code == 200
        assert response.content == (capture["folder"] / evidence.FILES[item["id"]][0]).read_bytes()
        assert hashlib.sha256(response.content).hexdigest() == item["sha256"]
        assert response.headers["content-disposition"].startswith("attachment;")
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_history_independent_of_later_draft_edits(capture):
    before = capture["client"].get(BASE + "/results").json()["evidence"]
    with SessionLocal() as db:
        solution = db.get(Solution, "executed-solution")
        solution.design_metadata = {"run_input": {"seed": 42}}
        solution.nodes = [{"id": "later draft edit"}]
        db.commit()
    after = capture["client"].get(BASE + "/results").json()["evidence"]
    assert before == after
    assert after["execution_input"]["seed"] == 43


@pytest.mark.parametrize("field,value", [("solution_id", "another-solution"), ("owner_user_id", "other"), ("source_revision", "different")])
def test_reject_mismatched_association(capture, field, value):
    capture["entry"][field] = value
    capture["reindex"]()
    result = capture["client"].get(BASE + "/results").json()["evidence"]
    assert result["state"] == "inaccessible" and result["execution_input"] is None
    assert capture["client"].get(BASE + "/artifacts/grid").status_code == 410


def test_reject_wrong_workflow_in_tasks_even_when_rehashed(capture):
    tasks = deepcopy(capture["tasks"])
    tasks[0]["workflow_id"] = "wf-000000000000"
    capture["write"]("tasks", tasks)
    report = json.loads((capture["folder"] / "report.json").read_bytes())
    report["artifact_sha256"]["tasks.json"] = capture["entry"]["sha256"]["tasks"]
    capture["write"]("report", report)
    capture["reindex"]()
    assert capture["client"].get(BASE + "/results").json()["evidence"]["state"] == "inaccessible"


def test_reject_deterministic_task_ids_from_a_different_execution(capture, monkeypatch):
    tasks = deepcopy(capture["tasks"])
    tasks[0]["created_at"] = "2026-10-19T12:00:00Z"
    monkeypatch.setattr(routes, "get_workflow_tasks", lambda _: {"tasks": tasks})
    assert capture["client"].get(BASE + "/artifacts/network").status_code == 410


def test_missing_reference_inaccessible_and_not_recorded_are_distinct(capture):
    (capture["folder"] / "grid.json").unlink()
    capture["entry"]["sha256"].pop("network")
    report = json.loads((capture["folder"] / "report.json").read_bytes())
    report["generator"]["artifacts"].pop("network.pandapower.json")
    capture["write"]("report", report)
    capture["reindex"]()
    value = capture["client"].get(BASE + "/results").json()["evidence"]
    assert value["execution_input"] == {"seed": 43} and value["grid"] is None
    states = {a["id"]: a["state"] for a in value["artifacts"]}
    assert states["grid"] == "inaccessible" and states["network"] == "not_recorded"
    assert capture["client"].get(BASE + "/artifacts/grid").status_code == 410
    assert capture["client"].get(BASE + "/artifacts/network").status_code == 404
    capture["index"]["workflows"].clear()
    capture["reindex"]()
    assert capture["client"].get(BASE + "/results").json()["evidence"]["state"] == "unavailable"


def test_recorded_artifact_without_curated_file_is_inaccessible(capture):
    capture["entry"]["sha256"].pop("network")
    capture["reindex"]()
    result = capture["client"].get(BASE + "/results").json()["evidence"]
    assert next(a for a in result["artifacts"] if a["id"] == "network")["state"] == "inaccessible"
    assert capture["client"].get(BASE + "/artifacts/network").status_code == 410


def test_missing_index_does_not_claim_a_capture_is_recorded(capture):
    (capture["root"] / "index.json").unlink()
    result = capture["client"].get(BASE + "/results").json()["evidence"]
    assert result["state"] == "unavailable" and result["execution_input"] is None


@pytest.mark.parametrize("status", ["running", "failed"])
def test_no_capture_never_invents_results_or_inputs(capture, status):
    capture["index"]["workflows"].clear()
    capture["reindex"]()
    capture["workflow"]["status"] = status
    result = capture["client"].get(BASE + "/results").json()
    assert result["workflow"]["status"] == status
    assert result["evidence"]["state"] == "unavailable"
    assert result["evidence"]["execution_input"] is None


def test_hash_tampering_is_inaccessible(capture):
    (capture["folder"] / "network.pandapower.json").write_text('{"changed":true}')
    assert capture["client"].get(BASE + "/artifacts/network").status_code == 410


@pytest.mark.parametrize("route", ["/results", "/artifacts/grid"])
def test_other_user_rejected_before_reading_evidence_or_orchestrator(capture, monkeypatch, route):
    def forbidden(*_):
        raise AssertionError("Must authorize before reading evidence/runtime")
    monkeypatch.setattr(routes, "current_state", forbidden)
    app.dependency_overrides[get_current_user] = lambda: User(id="other", role="solution_designer", status="active")
    assert capture["client"].get(BASE + route).status_code == 403


@pytest.mark.parametrize("route", ["/results", "/artifacts/grid"])
def test_unauthenticated_rejected(capture, route):
    with TestClient(app) as anonymous:
        assert anonymous.get(BASE + route).status_code == 401


def test_legacy_metadata_endpoints_also_enforce_ownership(capture):
    app.dependency_overrides[get_current_user] = lambda: User(id="other", role="solution_designer", status="active")
    for suffix in ("", "/tasks"):
        assert capture["client"].get(f"/orchestrator/workflows/{WF}" + suffix).status_code == 403


@pytest.mark.parametrize("relative", ["../outside.json", "../../studio.env", "/etc/passwd", "C:/Windows/win.ini"])
def test_path_restrictions(capture, relative):
    with pytest.raises((evidence.EvidenceError, OSError)):
        evidence.read_confined(capture["root"], relative)
    assert capture["client"].get(BASE + "/artifacts/studio.env").status_code == 404


def test_symlink_escape_rejected(capture, tmp_path):
    outside = tmp_path / "unrelated.json"
    outside.write_bytes((capture["folder"] / "grid.json").read_bytes())
    target = capture["folder"] / "grid.json"
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("Windows symlink creation requires a privilege; Linux container check required")
    assert capture["client"].get(BASE + "/artifacts/grid").status_code == 410


@pytest.mark.parametrize("field,value", [("local_dutch_evidence_scope", ""), ("orchestrator_base_url", "http://production:8000"), ("database_url", "postgresql://unused@127.0.0.1/another_database")])
def test_disabled_outside_explicit_local_scope(capture, monkeypatch, field, value):
    monkeypatch.setattr(settings, field, value)
    assert capture["client"].get(BASE + "/results").json()["evidence"]["state"] == "unavailable"
