"""OFFLINE action interpretation fixtures; never real model interpretation or Run."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.db import SessionLocal
from app.main import app
from app.models.operation_contract import OperationContract
from app.models.execution_submission import ExecutionSubmission
from app.schemas.solution_assistant import SavedSolutionResponse
from app.services.design_ai_provider import get_provider
from app.services.solution_assistant import digest
from test_saved_solution_assistant import configured,node,scope,apply
from app.services.workflow_boundaries import complete

class Offline:
    name='OFFLINE setting action replay';mode='test'
    def __init__(self):self.plan=None;self.contexts=[]
    async def respond(self,c):
        self.contexts.append(deepcopy(c))
        return SavedSolutionResponse.model_validate(self.plan(c))

@pytest.fixture
def edit_fixture(configured):
    with SessionLocal() as db:
        contract=db.get(OperationContract,'fixture-contract');d=deepcopy(contract.definition)
        d['execution_parameters']['properties'].update(limit={'type':'integer','title':'Candidate limit','description':'Software fixture only','minimum':1,'maximum':8,'default':4},keep={'type':'boolean','title':'Retain feature','description':'Unrelated fixture setting','default':True})
        contract.definition=d;db.commit()
    nodes=[node('alpha'),node('beta',43)]
    nodes[0]['data']['configuration']['parameters'].update(limit=6,keep=False)
    nodes[1]['data']['configuration']['parameters'].update(limit=7,keep=True)
    edges=[];complete(nodes,edges)
    s=configured.post('/solutions',json={'name':'Setting action fixture','nodes':nodes,'edges':edges,'design_metadata':{'run_input':{'selected':'fixture-input'}}}).json()
    s=configured.get('/solutions/'+s['id']).json();provider=Offline();app.dependency_overrides[get_provider]=lambda:provider
    return configured,s,provider

def request(f,plan,text='Change the maximum to two.'):
    client,s,p=f;p.plan=plan;state=client.get(scope(s)).json()
    return client.post(scope(s)+'/chat',json={'message':text,**{k:state[k] for k in ('expected_updated_at','conversation_revision')}})

def action(c,value=2,base=None,node_id='alpha'):
    base=base or ('pending' if c['pending_candidate'] else 'saved')
    step=next(s for s in c['pending_candidate' if base=='pending' else 'saved_design']['steps'] if s['node_id']==node_id)
    return dict(outcome='setting_edit',message=None,solution_edits=[],clarification=None,assumptions=[],edit_base=deepcopy(c['edit_bases'][base]),parameter_action=dict(operation='set_parameters',target_ref=step['target_ref'],requested_values=[dict(name='limit',value=value)]))

def pending_four(f):
    def plan(c):
        ref=next(s['target_ref'] for s in c['saved_design']['steps'] if s['node_id']=='alpha')
        return dict(outcome='proposal',message='EXPLICIT OFFLINE setup proposal',clarification=None,assumptions=[],edit_base=c['edit_bases']['saved'],solution_edits=[dict(kind='rename',value='Earlier proposed title'),dict(kind='set_node_parameters',node_id=ref,value='{"limit":4}')])
    r=request(f,plan,'OFFLINE setup: propose four and a title');assert r.status_code==200,r.text
    return r.json()

def step(state,node='alpha'):return next(s for s in state['pending']['candidate']['steps'] if s['node_id']==node)

@pytest.mark.parametrize('text',['Change the supported maximum from 4 to 2.','Please cap the candidates at two instead, leaving the rest alone.'])
def test_pending_four_to_two_actual_diff_apply_save_reopen(edit_fixture,text):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    response=request(edit_fixture,action,text);assert response.status_code==200,response.text
    review=response.json();actual=step(review)
    assert actual['effective_settings']==dict(seed=42,limit=2,keep=False)
    assert step(review,'beta')=={**step(old,'beta'),'target_ref':step(review,'beta')['target_ref']}
    assert review['pending']['supersedes']==old['pending']['id']
    assert review['pending']['candidate']['name']=='Earlier proposed title'
    diff=review['messages'][-1]['change_summary'];assert diff['source']=='application_diff' and diff['base_kind']=='pending'
    assert [(d['parameter'],d['before'],d['after']) for d in diff['changes']]==[('limit',4,2)]
    assert '4 → 2' in review['messages'][-1]['content'] and 'Proposed' in review['messages'][-1]['content']
    assert client.get('/solutions/'+s['id']).json()==s
    assert client.get(scope(s)).json()==review
    from app.models.solution import Solution
    from app.models.user import User
    from app.services import solution_assistant as service
    with SessionLocal() as db:
        source=db.get(Solution,s['id']);user=db.get(User,'designer');row=service.conversation(source,db,user)
        expected=service.materialize(source,row.state['pending'],db,user)
    r=apply(client,s,review);assert r.status_code==200,r.text
    assert 'applied and saved' in r.json()['application_notice']
    current=client.get('/solutions/'+s['id']).json()
    # GET hydrates registry display metadata for minimal legacy nodes; compare
    # the actual stored graph, not that read-only display projection.
    with SessionLocal() as db:
        persisted=service.content(db.get(Solution,s['id']))
        assert persisted==expected
        assert digest(persisted)==review['pending']['candidate']['candidate_sha256']
    assert next(n['data']['configuration']['parameters'] for n in current['nodes'] if n['id']=='alpha')==dict(seed=42,limit=2,keep=False)
    assert current['design_metadata']==s['design_metadata'] and current['edges']==s['edges']
    r=client.put('/solutions/'+s['id'],json={k:current[k] for k in ('name','nodes','edges','design_metadata')}|{'expected_updated_at':current['updated_at']});assert r.status_code==200,r.text
    reopened=client.get('/solutions/'+s['id']).json();assert reopened['nodes']==current['nodes'] and reopened['edges']==current['edges']
    with SessionLocal() as db:assert db.query(ExecutionSubmission).count()==0

def test_saved_base_and_accurate_already_satisfied_without_proposal(edit_fixture):
    client,s,p=edit_fixture
    r=request(edit_fixture,lambda c:action(c,6));assert r.status_code==200,r.text
    value=r.json();assert value['pending'] is None and value['messages'][-1]['outcome']=='answer'
    assert 'No change needed in the saved design' in value['messages'][-1]['content'] and 'already 6' in value['messages'][-1]['content']
    assert client.get('/solutions/'+s['id']).json()==s
    r=request(edit_fixture,action);assert r.status_code==200
    assert step(r.json())['effective_settings']['limit']==2
    assert r.json()['messages'][-1]['change_summary']['base_kind']=='saved'

def test_pending_already_satisfied_keeps_exact_review_and_no_success_claim(edit_fixture):
    old=pending_four(edit_fixture);client,s,p=edit_fixture
    r=request(edit_fixture,lambda c:action(c,4));assert r.status_code==200,r.text
    assert r.json()['pending']==old['pending']
    message=r.json()['messages'][-1];assert message['change_summary']['status']=='no_change'
    assert 'No change needed in the proposed design' in message['content'] and 'already 4' in message['content']
    assert client.get('/solutions/'+s['id']).json()==s

@pytest.mark.parametrize('bad',['empty','missing','duplicate','ambiguous','raw_node','invalid','boolean','unknown','summary','wrong_base','stale_revision','stale_hash'])
def test_invalid_action_preserves_prior_review_and_messages(edit_fixture,bad):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    def plan(c):
        v=action(c)
        if bad=='empty':v['parameter_action']['requested_values']=[]
        if bad=='missing':v['parameter_action']=None
        if bad=='duplicate':v['parameter_action']['requested_values']*=2
        if bad=='ambiguous':v['parameter_action']['target_ref']='ConfigureAndSynthesize'
        if bad=='raw_node':v['parameter_action']['target_ref']='alpha'
        if bad=='invalid':v['parameter_action']['requested_values'][0]['value']=999
        if bad=='boolean':v['parameter_action']['requested_values'][0]['value']=True
        if bad=='unknown':v['parameter_action']['requested_values'][0]['name']='invented_option'
        if bad=='summary':v['message']='Successfully changed everything and ran it'
        if bad=='wrong_base':return action(c,base='saved')
        if bad=='stale_revision':v['edit_base']['conversation_revision']-=1
        if bad=='stale_hash':v['edit_base']['candidate_sha256']='0'*64
        return v
    r=request(edit_fixture,plan);assert r.status_code in (409,422,502),r.text
    assert client.get(scope(s)).json()==old and client.get('/solutions/'+s['id']).json()==s

def test_manual_save_stales_proposal_and_does_not_apply(edit_fixture):
    client,s,p=edit_fixture;review=request(edit_fixture,action).json()
    r=client.put('/solutions/'+s['id'],json={'name':'Manual revision','expected_updated_at':s['updated_at']});assert r.status_code==200
    assert apply(client,s,review).status_code==409
    value=client.get(scope(s)).json();assert value['pending']['current'] is False and value['application_notice'] is None

def test_original_j2_empty_response_is_still_rejected_without_repair(edit_fixture):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    value=json.loads((Path(__file__).parent/'fixtures/complete-journey-rejected-j2-20261119.json').read_text(encoding='utf-8'))
    r=request(edit_fixture,lambda _:value);assert r.status_code==502
    assert client.get(scope(s)).json()==old

def test_legacy_setting_prose_is_not_trusted_for_change_summary(edit_fixture):
    client,s,p=edit_fixture
    def plan(c):
        a=action(c);return dict(outcome='proposal',message='Changed to 999 and ran successfully',clarification=None,assumptions=[],edit_base=a['edit_base'],solution_edits=[dict(kind='set_node_parameters',node_id=a['parameter_action']['target_ref'],value='{"limit":2}')])
    r=request(edit_fixture,plan);assert r.status_code==200,r.text
    assert '999' not in r.json()['messages'][-1]['content'] and '6 → 2' in r.json()['messages'][-1]['content']


def test_no_change_reply_after_apply_is_scoped_to_this_request(edit_fixture):
    client,s,p=edit_fixture
    review=request(edit_fixture,action).json();assert apply(client,s,review).status_code==200
    saved=client.get('/solutions/'+s['id']).json()
    r=request(edit_fixture,action);assert r.status_code==200,r.text
    value=r.json();assert value['pending'] is None
    assert value['application_notice'] is not None
    assert 'This request made no design changes and did not run the workflow.' in value['messages'][-1]['content']
    assert 'Nothing has been applied' not in value['messages'][-1]['content']
    assert client.get('/solutions/'+s['id']).json()==saved
