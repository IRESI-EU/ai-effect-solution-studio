"""Isolated deterministic recommendation/control tests. No provider or algorithm.

SQLite covers authorization/revisions, not PostgreSQL concurrency.
"""
from copy import deepcopy
import json

import pytest

from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models.operation_contract import OperationContract
from app.models.solution import Solution
from app.models.user import User
from app.models.design_ai import DesignDraft
from app.services import design_ai, catalogue_discovery
from app.services.capability_bindings import digest
from app.services.design_ai_provider import get_provider
from conftest import TestProvider
from test_portuguese_chain import chained, training_profile


@pytest.fixture
def registered(chained,monkeypatch):
    client,payload=chained;training_profile(monkeypatch)
    monkeypatch.setattr('app.services.design_ai_provider.AsyncOpenAI',lambda **k:pytest.fail('Provider networking is forbidden in isolated tests'))
    import requests
    monkeypatch.setattr(requests.Session,'request',lambda *a,**k:pytest.fail('Runtime networking is forbidden in isolated tests'))
    saved=client.post('/solutions',json=payload).json()
    with SessionLocal() as db:
        source=db.get(Solution,saved['id'])
        pins={c.id:digest(c.definition) for c in db.query(OperationContract).filter(OperationContract.id.in_(['pt-chain-train-v2','pt-chain-generate-v2'])).all()}
        policy={'portugal':{'solution_id':source.id,'instance_settings_only':True,'registered_parameters':{
            'registration_id':'pt-reviewer-chain-v2','reviewer_id':'designer','source_revision':design_ai.digest(design_ai.content(source)),
            'contract_definitions':pins}}}
    monkeypatch.setattr(settings,'design_ai_templates',json.dumps(policy))
    return client,client.get('/solutions/'+saved['id']).json()


def advertised(registered):
    client,_=registered
    r=client.get('/design-ai/registered-workflows');assert r.status_code==200,r.text
    assert len(r.json())==1
    return r.json()[0]


def create(registered,**changes):
    item=advertised(registered)
    r=registered[0].post('/design-ai/drafts',json={'candidate_id':item['candidate_id'],'recommendation_revision':item['recommendation_revision'],**changes})
    assert r.status_code==200,r.text
    return r.json()


def configure(client,draft,**changes):
    values={n['id']:n['data']['configuration']['parameters'] for n in draft['design']['nodes']}
    gen=next(n for n in draft['design']['nodes'] if n['data']['service']['operation_name']=='GenerateData')
    values[gen['id']]={'number_of_examples':20}
    payload={'revision':draft['revision'],'settings':values,'run_input':{'dataset_ref':'approved-data'},**changes}
    return client.post('/design-ai/drafts/'+draft['id']+'/configuration',json=payload)


def test_registered_controls_defaults_input_proposal_undo_reapply_save_and_compile(registered):
    client,source=registered;item=advertised(registered)
    assert item['configuration_kind']=='registered_parameters' and item['execution_supported'] is False
    assert item['required_inputs'][0]['choices']==[{'label':'Sandbox test dataset','dataset_ref':'approved-data'}]
    draft=create(registered);before=deepcopy(draft['design'])
    assert before['run_input'] is None and not draft['pending'] and not draft['saved_solution_id']
    assert 'Select a training CSV before validating.' in draft['validation']['errors']
    assert {n['id'] for n in before['nodes']}.isdisjoint({n['id'] for n in source['nodes']})
    assert [n['data']['configuration']['parameters'] for n in before['nodes']]==[{'epochs':1,'batch_size':4},{'number_of_examples':10}]
    assert client.post(f"/design-ai/drafts/{draft['id']}/save",json={'revision':0}).status_code==422
    response=configure(client,draft);assert response.status_code==200,response.text
    pending=response.json()['pending'];assert pending['validation']['valid']
    assert pending['input_review']=={'before':'Not selected','after':'Sandbox test dataset'}
    assert pending['parameter_review']['changes'][0]['before']==10 and pending['parameter_review']['changes'][0]['after']==20
    path='/design-ai/drafts/'+draft['id']
    applied=client.post(path+'/apply',json={'revision':0,'proposal_id':pending['id']}).json()
    assert applied['revision']==1 and applied['design']['run_input']=={'dataset_ref':'approved-data'}
    undone=client.post(path+'/undo',json={'revision':1}).json()
    assert undone['revision']==2 and undone['design']==before
    assert undone['pending']['design']==applied['design']
    reapplied=client.post(path+'/apply',json={'revision':2,'proposal_id':undone['pending']['id']}).json()
    assert reapplied['design']==applied['design'] and reapplied['revision']==3
    saved=client.post(path+'/save',json={'revision':3});assert saved.status_code==200,saved.text
    sid=saved.json()['draft']['saved_solution_id'];assert sid!=source['id']
    opened=client.get(path).json();assert opened['design']==reapplied['design'] and not opened['dirty']
    solution=client.get('/solutions/'+sid).json()
    assert solution['nodes']==reapplied['design']['nodes']
    assert solution['edges']==reapplied['design']['edges'] and solution['design_metadata']['run_input']=={'dataset_ref':'approved-data'}
    assert client.get('/solutions/'+source['id']).json()==source
    from app.services.registered_parameters import workflow
    payload=workflow(opened['design']).model_dump(mode='json',exclude_unset=True)
    compiled=client.post('/workflows/compile',json=payload);assert compiled.status_code==200,compiled.text
    assert compiled.json()['solution_studio_metadata']['capability_bindings']['bindings'][0]['source_slot']=='model_ref'
    assert not client.get('/deployments').json()


@pytest.mark.parametrize('value',[0,21,True,'20',1.5,None])
def test_invalid_registered_setting_rejected_without_proposal(registered,value):
    client,_=registered;draft=create(registered)
    gen=draft['design']['nodes'][1]['id']
    response=configure(client,draft,settings={gen:{'number_of_examples':value}})
    assert response.status_code==422,response.text
    assert client.get('/design-ai/drafts/'+draft['id']).json()['pending'] is None


@pytest.mark.parametrize('change',[{'run_input':{'dataset_ref':'unapproved'}},{'run_input':{'dataset_ref':'/private/file.csv'}},{'settings':{'other':{}}}])
def test_unauthorized_dataset_or_instance_rejected(registered,change):
    client,_=registered;draft=create(registered)
    assert configure(client,draft,**change).status_code==422


def test_unknown_parameter_and_stale_revision_rejected(registered):
    client,_=registered;draft=create(registered);gen=draft['design']['nodes'][1]['id']
    assert configure(client,draft,settings={gen:{'invented':20}}).status_code==422
    assert configure(client,draft,revision=99).status_code==409


@pytest.mark.parametrize('drift',['contract','source','owner','registration','dataset','approval'])
def test_revoked_or_stale_authority_denies_discovery_and_mutation(registered,monkeypatch,drift):
    client,source=registered;draft=create(registered)
    if drift=='registration':monkeypatch.setattr(settings,'design_ai_templates','{}')
    elif drift=='dataset':monkeypatch.setattr(settings,'portuguese_training_dataset_ref','')
    else:
        with SessionLocal() as db:
            if drift=='contract':
                c=db.get(OperationContract,'pt-chain-generate-v2');d=deepcopy(c.definition);d['description']='drift';c.definition=d
            if drift=='source':db.get(Solution,source['id']).name='changed'
            if drift=='owner':db.get(Solution,source['id']).created_by_user_id='other'
            if drift=='approval':
                from app.models.service import Service
                db.get(Service,'pt-experimental-chain-GenerateData').status='rejected'
            db.commit()
    assert client.get('/design-ai/registered-workflows').json()==[]
    assert configure(client,draft).status_code in (403,409)


def test_normal_actor_permissions_and_pair_exclusions_remain(registered):
    client,_=registered
    with SessionLocal() as db:
        assert catalogue_discovery.registered(db,db.get(User,'other'))==[]
        from app.services.catalogue_composition import records
        pairs,_=records(db,db.get(User,'designer'))
        assert all(s.id not in {'pt-experimental-chain-TrainModel','pt-experimental-chain-GenerateData'} for pair in pairs for s,_,_ in pair['_operations'])
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,'other')
        assert client.get('/design-ai/registered-workflows').json()==[]
    app.dependency_overrides.pop(get_current_user)


def test_operator_preparation_checks_existing_owner_and_does_not_publish_or_write(registered):
    from app.services.registered_parameters_operator import prepare
    from fastapi import HTTPException
    _,source=registered
    with SessionLocal() as db:
        before=deepcopy(design_ai.content(db.get(Solution,source['id'])))
        record=prepare(db,'designer',source['id'],'pt-reviewer-chain-v2')
        assert record['registered_parameters']['reviewer_id']=='designer'
        with pytest.raises(HTTPException):prepare(db,'other',source['id'],'pt-reviewer-chain-v2')
        assert design_ai.content(db.get(Solution,source['id']))==before and not db.new and not db.dirty


def test_wrong_draft_owner_and_contract_drift_before_apply_are_denied(registered):
    from app.dependencies.auth import get_current_user
    client,_=registered;draft=create(registered);pending=configure(client,draft).json()['pending']
    path='/design-ai/drafts/'+draft['id']
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,'other')
        assert client.post(path+'/apply',json={'revision':0,'proposal_id':pending['id']}).status_code==404
    app.dependency_overrides.pop(get_current_user)
    with SessionLocal() as db:
        c=db.get(OperationContract,'pt-chain-generate-v2');c.status='withdrawn';db.commit()
    assert client.post(path+'/apply',json={'revision':0,'proposal_id':pending['id']}).status_code==409


@pytest.mark.parametrize('method,key,value',[('TrainModel','epochs',True),('TrainModel','epochs',3),('TrainModel','batch_size',1),('TrainModel','batch_size','4')])
def test_training_settings_use_same_canonical_validation(registered,method,key,value):
    client,_=registered;draft=create(registered);node=next(n for n in draft['design']['nodes'] if n['data']['service']['operation_name']==method)
    assert configure(client,draft,settings={node['id']:{key:value}}).status_code==422


def test_noop_and_duplicate_confirmation_cannot_reapply(registered):
    client,_=registered;draft=create(registered);pending=configure(client,draft).json()['pending'];path='/design-ai/drafts/'+draft['id']
    request={'revision':0,'proposal_id':pending['id']}
    first=client.post(path+'/apply',json=request).json()
    assert client.post(path+'/apply',json=request).status_code==409
    values={n['id']:n['data']['configuration']['parameters'] for n in first['design']['nodes']}
    assert configure(client,first,settings=values).status_code==422


def test_provider_double_recommends_only_advertised_metadata_and_declared_values(registered):
    from app.schemas.design_ai import AssistantTurn
    client,_=registered;item=advertised(registered)
    turn=AssistantTurn(message='Recommend this registered experimental chain, using its defaults and a separate CSV selection.',
        template_key=None,expected_revision=None,edits=[],discovery={'outcome':'supported_recommendation','candidate_id':item['candidate_id']},
        registered_settings={'first':[{'name':'epochs','value':2}],'second':[{'name':'number_of_examples','value':20}]})
    fake=TestProvider(turn);app.dependency_overrides[get_provider]=lambda:fake
    response=client.post('/design-ai/chat',json={'message':'Train the approved sandbox model for two epochs and generate twenty sequences.'})
    assert response.status_code==200,response.text
    result=response.json();assert result['draft'] is None
    assert result['recommendation']['registered_settings']['second']==[{'name':'number_of_examples','value':20}]
    context=json.dumps(fake.contexts)
    assert 'approved-data' in context and 'dataset.csv' not in context and '/state' not in context and 'control/data' not in context
    bad=AssistantTurn.model_validate({**turn.model_dump(),'registered_settings':{'first':[],'second':[{'name':'invented','value':20}]}})
    fake.turn=bad
    assert client.post('/design-ai/chat',json={'message':'unsupported setting'}).status_code==422
    with SessionLocal() as db:assert db.query(DesignDraft).count()==0


def test_recommendation_create_keeps_requested_changes_reviewable_until_csv_selection(registered):
    client,_=registered;item=advertised(registered)
    choice={'first':[{'name':'epochs','value':2}],'second':[{'name':'number_of_examples','value':20}]}
    draft=create(registered,registered_settings=choice)
    assert draft['design']['run_input'] is None and not draft['pending']['validation']['valid']
    assert draft['design']['nodes'][1]['data']['configuration']['parameters']=={'number_of_examples':10}
    assert draft['pending']['design']['nodes'][1]['data']['configuration']['parameters']=={'number_of_examples':20}
    assert client.post('/design-ai/drafts/'+draft['id']+'/apply',json={'revision':0,'proposal_id':draft['pending']['id']}).status_code==422
    bad=client.post('/design-ai/drafts',json={'candidate_id':item['candidate_id'],'recommendation_revision':'0'*64,'registered_settings':choice})
    assert bad.status_code==409
