"""Real PostgreSQL atomic structural Apply and persistence; no runtime calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from threading import Barrier

from fastapi import HTTPException
from app.core.config import settings
from app.models.operation_contract import OperationContract
from app.models.solution import Solution
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai as service


def test_concurrent_structural_apply_undo_persistence(seeded, monkeypatch):
    definitions = json.loads((Path(__file__).resolve().parents[3] / "deploy/aie37/contracts.json").read_text())
    with seeded() as db:
        for operation, definition in definitions.items():
            db.add(OperationContract(id="contract-" + operation, service_id="dutch-" + operation, status="active", **definition))
        source = db.get(Solution, "source-dutch")
        nodes = [deepcopy(n) for n in source.nodes if n.get("data", {}).get("service", {}).get("operation_name") != "RunBenchmark"]
        generator = next(n for n in nodes if n.get("data", {}).get("service"))
        pin = {"contract_id": "contract-ConfigureAndSynthesize", "contract_version": "1.0.0"}
        generator["data"].update(operation_contract=pin, configuration={**pin, "parameters": {"seed": 42}})
        source.nodes = nodes
        source.edges = [{"id": "start", "source": next(n["id"] for n in nodes if n.get("type") == "input"), "target": generator["id"]},
                        {"id": "end", "source": generator["id"], "target": next(n["id"] for n in nodes if n.get("type") == "output")}]
        db.commit()
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps({"dutch": {"solution_id": "source-dutch", "structural_append_only": True}}))
    with seeded() as db:
        actor = db.get(User, "a")
        draft = service.start("dutch", db, actor)
        turn = AssistantTurn(message="OFFLINE fixture", template_key=None, expected_revision=0, edits=[{
            "kind": "append_bound_operation", "node_id": generator["id"], "value": json.dumps({"local_ref": "benchmark",
            "service_id": "dutch-RunBenchmark", "contract_id": "contract-RunBenchmark", "contract_version": "1.0.0",
            "source_slot": "captured_grid", "target_slot": "captured_grid"})}])
        pending = service.propose(draft["id"], turn, db, actor)
    barrier = Barrier(2)
    def apply():
        with seeded() as db:
            actor = db.get(User, "a")
            barrier.wait(timeout=10)
            try:
                return service.apply(draft["id"], 0, pending["pending"]["id"], db, actor)["revision"]
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(f.result(timeout=20) for f in [pool.submit(apply), pool.submit(apply)]) == [1, 409]
    with seeded() as db:
        actor = db.get(User, "a")
        assert service.undo(draft["id"], 1, db, actor)["design"] == draft["design"]
        pending = service.propose(draft["id"], turn.model_copy(update={"expected_revision": 2}), db, actor)
        applied = service.apply(draft["id"], 2, pending["pending"]["id"], db, actor)
        saved = service.save(draft["id"], 3, db, actor, explicit_save=True)
        solution = db.get(Solution, saved["saved_solution_id"])
        assert solution.nodes == applied["design"]["nodes"] and solution.edges == applied["design"]["edges"]
