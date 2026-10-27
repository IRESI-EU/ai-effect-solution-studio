import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db import Base, engine
from app.main import app
from app.models.design_ai import DesignDraft
from app.models.solution import Solution
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai as service

MIGRATION = Path(__file__).resolve().parents[3] / "deploy/migrations/003_design_ai_pilot.sql"


def turn(revision=0, name="Reviewed design"):
    return AssistantTurn(message="Test-only rename",template_key=None,expected_revision=revision,edits=[{"kind":"rename","value":name,"node_id":None}])


def started(factory):
    with factory() as db:
        return service.start("denmark",db,db.get(User,"a"))


def proposed(factory, draft, proposal=None):
    with factory() as db:
        return service.propose(draft["id"],proposal or turn(draft["revision"]),db,db.get(User,"a"))


def test_empty_database_boots_in_fresh_process(fresh_database):
    url,target = fresh_database
    assert inspect(target).get_table_names() == []
    env={**os.environ,"DATABASE_URL":url.render_as_string(hide_password=False)}
    result=subprocess.run([sys.executable,"-c","from app.main import app; from fastapi.testclient import TestClient; c=TestClient(app); assert c.get('/health').status_code==200; print(c.get('/design-ai/config').json()['enabled'])"],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
    assert "design_ai_drafts" in inspect(target).get_table_names()
    assert "design_metadata" in {c["name"] for c in inspect(target).get_columns("solutions")}


def test_populated_upgrade_preserves_all_existing_records(seeded):
    # Make this disposable database match the complete pre-feature schema.
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE design_ai_drafts"))
        connection.execute(text("ALTER TABLE solutions DROP COLUMN design_metadata"))
        tables=["services","solutions","deployments","users","operation_contracts"]
        before={name:connection.execute(text(f"SELECT to_jsonb(t) FROM {name} t ORDER BY id")).scalars().all() for name in tables}
        connection.execute(text(MIGRATION.read_text()))
        connection.execute(text(MIGRATION.read_text()))  # idempotent reapplication
        after={name:connection.execute(text(f"SELECT to_jsonb(t) - 'design_metadata' FROM {name} t ORDER BY id")).scalars().all() for name in tables}
    assert before == after
    with seeded() as db:
        assert service.start("dutch",db,db.get(User,"a"))["revision"] == 0


def test_stale_identity_map_cannot_overwrite_newer_revision(seeded):
    draft=proposed(seeded,started(seeded))
    with seeded() as stale:
        cached=service.load_draft(draft["id"],stale,stale.get(User,"a"))
        assert cached.revision == 0
        with seeded() as fresh:
            actor=fresh.get(User,"a")
            service.apply(draft["id"],0,draft["pending"]["id"],fresh,actor)
            service.undo(draft["id"],1,fresh,actor)
        with pytest.raises(HTTPException) as error:
            service.apply(draft["id"],0,draft["pending"]["id"],stale,stale.get(User,"a"))
        assert error.value.status_code == 409
    with seeded() as verify:
        assert verify.get(DesignDraft,draft["id"]).revision == 2


def test_concurrent_applies_have_one_winner(seeded):
    draft=proposed(seeded,started(seeded))
    barrier=Barrier(2)
    def apply():
        with seeded() as db:
            actor=db.get(User,"a")
            barrier.wait(timeout=10)
            try:
                return service.apply(draft["id"],0,draft["pending"]["id"],db,actor)["revision"]
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(apply) for _ in range(2)]
        assert sorted(f.result(timeout=20) for f in futures) == [1,409]


def test_chat_proposal_uses_server_snapshot_and_rejects_concurrent_edit(seeded,monkeypatch):
    from app.services.design_ai_provider import get_provider
    draft=proposed(seeded,started(seeded))
    class ConcurrentProvider:
        async def respond(self,context):
            assert context['draft']['revision']==0
            with seeded() as writer:
                service.apply(draft['id'],0,draft['pending']['id'],writer,writer.get(User,'a'))
            return turn(1,'Must not replace the winning edit')
    monkeypatch.setitem(app.dependency_overrides,get_provider,lambda:ConcurrentProvider())
    with TestClient(app) as client:
        assert client.post('/auth/login',json={'email':'a@example.test','password':'LocalAcceptance123'}).status_code==200
        response=client.post('/design-ai/chat',json={'message':'Rename this draft','draft_id':draft['id'],'revision':0})
        assert response.status_code==409
    with seeded() as db:
        row=db.get(DesignDraft,draft['id'])
        assert row.revision==1 and row.state['design']['name']=='Reviewed design'
        assert row.state['pending'] is None


def test_concurrent_saves_create_one_solution(seeded):
    draft=started(seeded)
    barrier=Barrier(2)
    def save():
        with seeded() as db:
            actor=db.get(User,"a")
            barrier.wait(timeout=10)
            return service.save(draft["id"],0,db,actor,explicit_save=True)["saved_solution_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(save) for _ in range(2)]
        values=[f.result(timeout=20) for f in futures]
    assert len(set(values)) == 1
    with seeded() as db:
        assert db.query(Solution).count() == 3


def test_failed_write_rolls_back_solution_and_session_state(seeded):
    draft=started(seeded)
    with engine.begin() as conn:
        conn.execute(text("""CREATE FUNCTION reject_ai_save() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.action = 'solution.ai_draft_saved' THEN RAISE EXCEPTION 'isolated failure injection'; END IF; RETURN NEW; END $$;
        CREATE TRIGGER reject_save BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_ai_save();"""))
    try:
        with TestClient(app) as client:
            assert client.post('/auth/login',json={'email':'a@example.test','password':'LocalAcceptance123'}).status_code==200
            response=client.post(f"/design-ai/drafts/{draft['id']}/save",json={'revision':0})
            assert response.status_code == 422
        with seeded() as db:
            assert db.query(Solution).count() == 2
            row=db.get(DesignDraft,draft["id"])
            assert row.state["saved_solution_id"] is None and row.state["dirty"]
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TRIGGER reject_save ON audit_events; DROP FUNCTION reject_ai_save();"))


def test_restart_owner_isolation_undo_and_builder_handoff(seeded):
    draft=proposed(seeded,started(seeded))
    with seeded() as db:
        source_before=deepcopy(service.content(db.get(Solution,"source-denmark")))
        actor=db.get(User,"a")
        current=service.apply(draft["id"],0,draft["pending"]["id"],db,actor)
        restored=service.undo(draft["id"],1,db,actor)
        assert restored["design"]==draft["design"]
        next_proposal=service.propose(draft["id"],turn(2),db,actor)
        service.apply(draft["id"],2,next_proposal["pending"]["id"],db,actor)
        saved=service.save(draft["id"],3,db,actor,explicit_save=True)
        with pytest.raises(HTTPException) as error:
            service.load_draft(draft["id"],db,db.get(User,"b"))
        assert error.value.status_code==404
        assert service.content(db.get(Solution,"source-denmark"))==source_before
    code="""import json,sys
from app.main import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
 assert c.post('/auth/login',json={'email':'a@example.test','password':'LocalAcceptance123'}).status_code==200
 draft=c.get('/design-ai/drafts/'+sys.argv[1]).json()
 assert draft['revision']==3 and draft['can_undo'] and not draft['dirty']
 solution=c.get('/solutions/'+sys.argv[2]).json()
 assert solution['name']=='Reviewed design' and solution['status']=='draft'
 assert solution['nodes']==draft['design']['nodes'] and solution['edges']==draft['design']['edges']
 print('Restart and Builder API handoff passed')
"""
    env={**os.environ,"DESIGN_AI_ENABLED":"true","DESIGN_AI_TEMPLATES":settings.design_ai_templates}
    result=subprocess.run([sys.executable,"-c",code,draft["id"],saved["saved_solution_id"]],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert "passed" in result.stdout


def test_feature_disable_rollback_keeps_saved_builder_design(seeded, monkeypatch):
    draft=started(seeded)
    with seeded() as db:
        saved=service.save(draft["id"],0,db,db.get(User,"a"),explicit_save=True)
    monkeypatch.setattr(settings,"design_ai_enabled",False)
    with TestClient(app) as client:
        client.post('/auth/login',json={'email':'a@example.test','password':'LocalAcceptance123'})
        assert client.get('/design-ai/drafts/'+draft['id']).status_code==404
        assert client.get('/solutions/'+saved['saved_solution_id']).status_code==200
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE design_ai_drafts"))
    # create_all on a later API startup recreates empty session storage.
    Base.metadata.create_all(engine)
    with seeded() as db:
        assert db.query(DesignDraft).count()==0
        assert db.get(Solution,saved['saved_solution_id']).design_metadata['origin']=='design_ai'


def test_synthetic_verified_input_survives_postgres_and_restart(seeded,monkeypatch):
    policies=json.loads(settings.design_ai_templates)
    policies['denmark']['run_input']={'service_id':'denmark-BuildRunConfig','operation_name':'BuildRunConfig',
        'evidence_reference':'Synthetic contract fixture only; not real Danish wrapper verification',
        'json_schema':{'type':'object','properties':{'prompt':{'type':'string'}},'required':['prompt'],'additionalProperties':False}}
    monkeypatch.setattr(settings,'design_ai_templates',json.dumps(policies))
    draft=started(seeded)
    assert not draft['validation']['valid']
    proposal=AssistantTurn(message='Synthetic input test',template_key=None,expected_revision=0,
        edits=[{'kind':'set_run_input','value':'{"prompt":"Synthetic topology study"}','node_id':None}])
    candidate=proposed(seeded,draft,proposal)
    with seeded() as db:
        actor=db.get(User,'a')
        service.apply(draft['id'],0,candidate['pending']['id'],db,actor)
        saved=service.save(draft['id'],1,db,actor,explicit_save=True)
    code="""import sys
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
 assert c.post('/auth/login',json={'email':'a@example.test','password':'LocalAcceptance123'}).status_code==200
 value=c.get('/solutions/'+sys.argv[1]).json()
 assert value['design_metadata']['run_input']=={'prompt':'Synthetic topology study'}
 print('Input persistence passed')
"""
    result=subprocess.run([sys.executable,'-c',code,saved['saved_solution_id']],env={**os.environ,'DESIGN_AI_ENABLED':'true','DESIGN_AI_TEMPLATES':settings.design_ai_templates},capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
