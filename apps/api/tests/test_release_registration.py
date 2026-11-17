"""Target design authority on a non-sandbox identity. No provider/runtime calls."""
from copy import deepcopy
import json
import pytest
from fastapi import HTTPException
from app.core.config import settings
from app.db import SessionLocal
from app.models.user import User
from app.services import design_ai, registered_parameters
from app.services.shared_allowance import database_scope
from test_portuguese_chain import chained
from test_registered_portuguese import registered, advertised, create, configure


@pytest.fixture
def target(registered,monkeypatch):
    monkeypatch.setattr(settings,'database_url','postgresql+psycopg://release@postgres/independent_beta_review')
    monkeypatch.setattr(settings,'portuguese_evidence_owner_id','')
    monkeypatch.setattr(settings,'portuguese_training_dataset_ref','')
    monkeypatch.setattr(settings,'design_ai_registration_environment','isolated-release-review')
    policy=json.loads(settings.design_ai_templates)
    policy['portugal']['registered_parameters']['deployment_design_input']={
        'environment':'isolated-release-review','database_scope':database_scope(settings.database_url),
        'dataset_ref':'target-reviewed-csv','label':'Release review CSV (design only)'}
    monkeypatch.setattr(settings,'design_ai_templates',json.dumps(policy))
    return registered


def test_target_defaults_apply_undo_reapply_save_builder_and_independent_identity(target):
    client,source=target
    assert advertised(target)['required_inputs'][0]['choices']==[{'dataset_ref':'target-reviewed-csv','label':'Release review CSV (design only)'}]
    draft=create(target);second=create(target)
    assert {n['id'] for n in draft['design']['nodes']}.isdisjoint(n['id'] for n in second['design']['nodes'])
    before=deepcopy(draft['design']);path='/design-ai/drafts/'+draft['id']
    pending=configure(client,draft,run_input={'dataset_ref':'target-reviewed-csv'}).json()['pending']
    assert pending['input_review']['after']=='Release review CSV (design only)'
    apply=lambda rev,p:client.post(path+'/apply',json={'revision':rev,'proposal_id':p['id']})
    installed=apply(0,pending).json()
    undone=client.post(path+'/undo',json={'revision':1}).json()
    assert undone['design']==before and undone['pending']
    applied=apply(2,undone['pending']).json();assert applied['design']==installed['design']
    saved=client.post(path+'/save',json={'revision':3});assert saved.status_code==200,saved.text
    solution=client.get('/solutions/'+saved.json()['draft']['saved_solution_id']).json()
    assert solution['nodes']==applied['design']['nodes'] and solution['edges']==applied['design']['edges']
    assert solution['design_metadata']['run_input']=={'dataset_ref':'target-reviewed-csv'}
    assert solution['design_metadata']['execution_policy']=='design_only_registered_parameters'
    request=registered_parameters.workflow(applied['design']).model_dump(mode='json',exclude_unset=True)
    assert client.post('/workflows/compile',json=request).status_code==200
    assert client.post('/workflows/compile',json={**request,'run_input':{'dataset_ref':'approved-data'}}).status_code==422
    assert client.post('/workflows/compile',json={**request,'run_input':None}).status_code==422
    for route in ('runtime-preflight','submit-to-orchestrator'):
        r=client.post('/workflows/'+route,json=request);assert r.status_code==403,r.text
    assert client.get('/solutions/'+source['id']).json()==source
    assert not client.get('/deployments').json()


@pytest.mark.parametrize('drift',['environment','database','reviewer','pins','input'])
def test_target_scope_drift_and_unapproved_input_fail_closed(target,monkeypatch,drift):
    client,_=target;draft=create(target)
    if drift=='environment':monkeypatch.setattr(settings,'design_ai_registration_environment','other-target')
    elif drift=='database':monkeypatch.setattr(settings,'database_url','postgresql+psycopg://release@postgres/other_database')
    else:
        policy=json.loads(settings.design_ai_templates);reg=policy['portugal']['registered_parameters']
        if drift=='reviewer':reg['reviewer_id']='other'
        if drift=='pins':reg['contract_definitions']['pt-chain-train-v2']='0'*64
        if drift=='input':reg['deployment_design_input']['dataset_ref']='different-ref'
        monkeypatch.setattr(settings,'design_ai_templates',json.dumps(policy))
    if drift!='input':assert client.get('/design-ai/registered-workflows').json()==[]
    result=configure(client,draft,run_input={'dataset_ref':'target-reviewed-csv'})
    assert result.status_code in (403,409,422),result.text


def test_target_wrong_owner_minimal_input_and_permanent_execution_deny(target,monkeypatch):
    from app.dependencies.auth import get_current_user
    from app.main import app
    client,_=target;draft=create(target)
    selection=client.get('/workflows/training-input').json()
    assert selection=={'dataset':{'label':'Release review CSV (design only)','dataset_ref':'target-reviewed-csv'},
        'execution':{'available':False,'service_ids':registered_parameters.SERVICES,'message':'INSPECTION ONLY. This registered workflow is available for design review; new experimental execution is disabled.'}}
    request=registered_parameters.workflow(draft['design']).model_dump(mode='json',exclude_unset=True)
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,'other')
        assert client.get('/workflows/training-input').json()['dataset'] is None
        assert client.get('/design-ai/registered-workflows').json()==[]
        assert client.post('/workflows/compile',json={**request,'run_input':{'dataset_ref':'target-reviewed-csv'}}).status_code==403
    app.dependency_overrides.pop(get_current_user)
    monkeypatch.setattr(settings,'design_ai_registration_environment','')
    monkeypatch.setattr(settings,'design_ai_templates','{}')
    # Removing registration/solution identity cannot turn these services executable.
    assert client.post('/workflows/submit-to-orchestrator',json=request).status_code==403


def test_preparation_is_read_only_and_legacy_sandbox_authority_not_copied(target):
    from app.services.registered_parameters_operator import prepare
    _,source=target;deployment=json.loads(settings.design_ai_templates)['portugal']['registered_parameters']['deployment_design_input']
    with SessionLocal() as db:
        with pytest.raises(HTTPException):prepare(db,'designer',source['id'],'target-review')
        value=prepare(db,'designer',source['id'],'target-review',deployment_design_input=deployment)
        assert value['registered_parameters']['deployment_design_input']==deployment
        assert not db.new and not db.dirty


def test_target_stale_revision_and_contracts_remain_authoritative(target):
    from app.models.operation_contract import OperationContract
    client,_=target;draft=create(target)
    assert configure(client,draft,revision=99,run_input={'dataset_ref':'target-reviewed-csv'}).status_code==409
    pending=configure(client,draft,run_input={'dataset_ref':'target-reviewed-csv'}).json()['pending']
    with SessionLocal() as db:
        db.get(OperationContract,'pt-chain-generate-v2').status='withdrawn';db.commit()
    assert client.post('/design-ai/drafts/'+draft['id']+'/apply',json={'revision':0,'proposal_id':pending['id']}).status_code==409
