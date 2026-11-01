"""PostgreSQL claim/concurrency only; no actual dispatch, provider or capture."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from app.db import SessionLocal
from app.models.execution_submission import ExecutionSubmission
from app.models.user import User
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import execution_journey as journey, execution_submission


@pytest.mark.parametrize('same_attempt',[True,False])
def test_concurrent_claims_permit_one_attempt_for_one_grant(seeded,monkeypatch,same_attempt):
    workflow=WorkflowSubmitRequest(name='OFFLINE lock test',solution_id='source-dutch',nodes=[{
        'node_id':'test-source','service_id':'dutch-ConfigureAndSynthesize','container_name':'test',
        'operation_name':'ConfigureAndSynthesize','configuration':{'parameters':{'seed':43}}}],edges=[])
    grant={'id':'OFFLINE-lock-grant','source_solution_id':'source-dutch'}
    monkeypatch.setattr(journey,'authorization',lambda *a:grant)
    with SessionLocal() as db:
        user=db.get(User,'a')
        first=execution_submission.prepare(db,user,workflow,{},phase='reviewed',authorization=grant).id
        second=first if same_attempt else execution_submission.prepare(db,user,workflow,{},phase='reviewed',authorization=grant).id
    def claim(identifier):
        with SessionLocal() as db:
            user=db.get(User,'a');row=journey.load_attempt(identifier,db,user,lock=True)
            if row.phase!='reviewed':return False
            try:journey.claim(row,workflow,{},db,user);return True
            except HTTPException as exc:
                assert exc.status_code==409
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(claim,[first,second])).count(True)==1
    with SessionLocal() as db:
        assert db.query(ExecutionSubmission).filter(ExecutionSubmission.phase=='dispatching').count()==1
