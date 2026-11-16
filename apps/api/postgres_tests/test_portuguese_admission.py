"""Real PostgreSQL admission serialization; all execution/HTTP boundaries doubled.

Uses only the existing suite's newly allocated disposable *_test database.
Does not enable a retained profile, create journal authority or dispatch work.
Portable tests separately cover the HTTP profile/ownership/closed-mode guards.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from threading import Event, Lock
import time

from fastapi import HTTPException
import pytest
from sqlalchemy import text
from app.core.config import settings
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import User
from app.schemas.operation_contract import OperationContractWrite
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import portuguese_supervision as gate

CONTRACTS = json.loads((Path(__file__).resolve().parents[3] / "deploy/portuguese_sandbox/chain_contracts.json").read_text())


@pytest.mark.parametrize("same_solution", [True, False])
@pytest.mark.parametrize("uncertain_dispatch", [False, True])
def test_reviewer_row_serializes_one_authority_across_confirmations(seeded, monkeypatch, same_solution, uncertain_dispatch):
    from app import main
    from app.services import orchestrator_adapter
    monkeypatch.setattr(settings, "portuguese_evidence_owner_id", "a")
    monkeypatch.setattr(settings, "portuguese_supervised_authorization_id", "OFFLINE-pg-authority-double")
    with seeded() as db:
        for c in CONTRACTS:
            value = OperationContractWrite.model_validate({k:v for k,v in c.items() if k not in {"id", "service_id"}})
            db.add(Service(id=c["service_id"], name=value.runtime_operation_name, provider="OFFLINE PostgreSQL fixture",
                category="experimental-portuguese", description="Synthetic lock test only", status="approved", lifecycle_status="active",
                input_type="reference", output_type="reference", operation_name=value.runtime_operation_name,
                container_name="pt-chain-"+value.runtime_operation_name, internal_host="adapter", internal_port="8080",
                image="sha256:offline-fixture", interface_type="control", orchestration_mode="sidecar", adapter_type="platform-experimental"))
            db.flush()
            values = value.model_dump(); values["definition"] = value.definition.model_dump(mode="json", exclude_none=True)
            db.add(OperationContract(id=c["id"], service_id=c["service_id"], status="active", **values))
        nodes = []
        for method, identity in (("TrainModel", "train"), ("GenerateData", "generate")):
            c = next(c for c in CONTRACTS if c["runtime_operation_name"] == method)
            pin = {"contract_id": c["id"], "contract_version": "0.2.0"}
            nodes.append({"id": identity, "data": {"node_kind": "service", "service": {"id": c["service_id"]},
                "operation_contract": pin, "configuration": {**pin, "parameters":
                    {"epochs":2, "batch_size":4} if method == "TrainModel" else {"number_of_examples":10}}}})
        edge = {"id":"handoff", "source":"train", "target":"generate", "data":{"binding":{"source_slot":"model_ref", "target_slot":"model_ref"}}}
        for identity in ("pg-pt-first", "pg-pt-second"):
            db.add(Solution(id=identity, name="OFFLINE PG lock fixture", nodes=deepcopy(nodes), edges=[edge], status="draft",
                created_by_user_id="a", design_metadata={"run_input":{"dataset_ref":"approved-data"}}))
        db.commit()
        def request(identity):
            row = db.get(Solution, identity)
            return WorkflowSubmitRequest.model_validate({"name": row.name, "solution_id": row.id, "expected_updated_at": row.updated_at.isoformat(),
                "nodes":[{"node_id":n["id"], "service_id":n["data"]["service"]["id"], "container_name":"registry", "operation_name":"registry",
                    "configuration":n["data"]["configuration"], "operation_contract":n["data"]["operation_contract"]} for n in nodes],
                "edges":[{"source":"train", "target":"generate", "binding":edge["data"]["binding"]}], "run_input":{"dataset_ref":"approved-data"}})
        first = request("pg-pt-first"); second = first if same_solution else request("pg-pt-second")
    # Dependencies and authority are explicit doubles; compilation and saved
    # snapshot validation remain real. Any unanticipated HTTP is forbidden.
    def forbidden(*a, **kw): raise AssertionError("No live network in PostgreSQL admission test")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    monkeypatch.setattr(main, "run_runtime_preflight", lambda *a: {"status":"ready", "checks":[]})
    monkeypatch.setattr(main, "require_binding_transport", lambda *a: {"status":"ready"})
    monkeypatch.setattr(orchestrator_adapter, "require_parameter_transport", lambda *a: {"status":"ready"})
    entered, release = Event(), Event(); counts = {"dispatch":0}; count_lock = Lock(); pids = {}
    def boundary(action, value):
        if action == "check" and not entered.is_set():
            entered.set()
            assert release.wait(10), "Test failed to release the first admission"
        frozen = value["request"] if action == "bind" else value
        return {k:frozen[k] for k in ("authorization_id", "owner_id", "request_sha256")} | {
            "status":"bound" if action == "bind" else "ready", "policy_sha256":"a"*64,
            **({"workflow_id":value["workflow_id"]} if action == "bind" else {})}
    def dispatch(*a):
        with count_lock: counts["dispatch"] += 1
        if uncertain_dispatch: raise RuntimeError("OFFLINE uncertain response double")
        return {"workflow_id":"wf-aaaaaaaaaaaa", "status":"running"}
    monkeypatch.setattr(gate, "boundary", boundary); monkeypatch.setattr(main, "submit_to_orchestrator", dispatch)
    def confirm(which, body):
        with seeded() as db:
            pids[which] = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            try: return gate.submit(body, db, db.get(User, "a"))
            except HTTPException as exc:
                assert exc.status_code == 409
                return {"denied":409}
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(confirm, "first", first)
        try:
            assert entered.wait(10)
            b = pool.submit(confirm, "second", second)
            deadline = time.monotonic()+5; observed_block = False
            with seeded() as observer:
                while time.monotonic() < deadline:
                    if "second" in pids:
                        blockers = observer.execute(text("SELECT pg_blocking_pids(:pid)"), {"pid":pids["second"]}).scalar_one()
                        if pids["first"] in blockers:
                            observed_block = True; break
                    time.sleep(.02)
            assert observed_block, "Second admission did not wait on the actual reviewer-row lock"
        finally: release.set()
        results = [a.result(timeout=10), b.result(timeout=10)]
    assert counts["dispatch"] == 1
    with seeded() as db:
        rows = db.query(ExecutionSubmission).all(); assert len(rows) == 1
        assert rows[0].phase == ("submission_unknown" if uncertain_dispatch else "submitted")
        assert db.query(Deployment).filter(Deployment.workflow_id=="wf-aaaaaaaaaaaa").count() == (0 if uncertain_dispatch else 1)
    if uncertain_dispatch:
        assert results == [{"denied":409}, {"denied":409}]
        assert confirm("replay", first) == {"denied":409}
    else:
        assert results[0]["workflow_id"] == "wf-aaaaaaaaaaaa"
        assert confirm("replay", first)["replayed"] is True
        if not same_solution: assert results[1] == {"denied":409}
    assert counts["dispatch"] == 1
