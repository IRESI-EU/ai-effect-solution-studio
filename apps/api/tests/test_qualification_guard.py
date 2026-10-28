"""Offline one-submission guard fixtures, never actual orchestrator requests."""
from copy import deepcopy
import pytest
from fastapi import HTTPException
from app.db import SessionLocal
from app.models.service import Service
from app.models.user import User
from app.models.local_dutch_execution import LocalDutchExecution
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import local_dutch_capture as capture
from test_automatic_dutch_capture import auto


def test_failed_or_completed_permission_cannot_be_replaced(auto, monkeypatch):
    monkeypatch.setattr(capture, "qualification_enabled", lambda: True)
    payload = {**auto["payload"], "run_input": None}
    compiled = deepcopy(auto["compiled"])
    compiled["inputs"] = []
    compiled["task_configurations"] = {"grid_synth_service:ConfigureAndSynthesize": {"parameters": {"seed": 43}}}
    compiled["solution_studio_metadata"] = {"capability_bindings": {"status": "verified"}}
    with SessionLocal() as db:
        db.add(Service(id="aie37-synth", name="Guard fixture", provider="Test", category="Test",
                       input_type="None", output_type="Grid", description="Disposable guard fixture"))
        db.commit()
        record = db.query(LocalDutchExecution).one()
        record.phase, record.workflow_id = "submission_failed", None
        db.commit()
        with pytest.raises(HTTPException) as blocked:
            capture.prepare_submission(db, db.get(User, "designer"), WorkflowSubmitRequest(**payload), compiled)
        assert blocked.value.status_code == 409
        assert db.query(LocalDutchExecution).count() == 1
        assert record.phase == "submission_failed"
    assert auto["calls"] == ["submit"]  # Only the original fixture's mocked submit.


def test_other_workflow_cannot_bypass_qualification_cap(auto, monkeypatch):
    monkeypatch.setattr(capture, "qualification_enabled", lambda: True)
    compiled = deepcopy(auto["compiled"])
    compiled["blueprint"]["nodes"] = compiled["blueprint"]["nodes"][:1]
    with SessionLocal() as db, pytest.raises(HTTPException) as blocked:
        capture.prepare_submission(db, db.get(User, "designer"), WorkflowSubmitRequest(**auto["payload"]), compiled)
    assert blocked.value.status_code == 422
