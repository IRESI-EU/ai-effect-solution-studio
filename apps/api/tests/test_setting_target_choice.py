"""Offline target-choice boundary; no model requests or genuine acceptance claim."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.models.solution import Solution
from app.services.solution_assistant import content, digest
from test_trustworthy_setting_edit import edit_fixture, action
from test_saved_solution_assistant import scope, apply, configured


def choose(state, identifier):
    targets=state['setting_targets']
    return {k:v for k,v in targets.items() if k!='choices'} | {'target_ref':next(c['target_ref'] for c in targets['choices'] if c['instance_id']==identifier)}


def send(f, plan=action, *, selection=None, text='Change the candidate maximum to two.'):
    client,s,p=f;p.plan=plan;state=client.get(scope(s)).json()
    return client.post(scope(s)+'/chat',json={k:state[k] for k in ('expected_updated_at','conversation_revision')} | {'message':text} | ({'target_choice':selection} if selection else {}))


def saved_content(s):
    with SessionLocal() as db:return content(db.get(Solution,s['id']))


def earlier_review(f):
    def rename(c):return dict(outcome='proposal',message='OFFLINE prior review',clarification=None,assumptions=[],edit_base=c['edit_bases']['saved'],solution_edits=[dict(kind='rename',value='Earlier pending title')])
    return send(f,rename).json()


def test_ambiguous_guess_preserves_exact_earlier_pending_work(edit_fixture):
    client,s,p=edit_fixture;old=earlier_review(edit_fixture);before=saved_content(s)
    r=send(edit_fixture);assert r.status_code==200,r.text
    q=r.json();assert q['pending']==old['pending'] and saved_content(s)==before
    assert q['target_question']['current'] and len(q['target_question']['choices'])==2
    assert q['clarification']['source']=='application_target_choice'
    assert q['messages'][-1]['outcome']=='clarification' and 'unchanged' in q['messages'][-1]['content']
    assert q['messages'][-1].get('change_summary') is None


def test_explicit_south_choice_changes_only_south_then_apply_and_reopen(edit_fixture):
    client,s,p=edit_fixture;old=earlier_review(edit_fixture)
    q=send(edit_fixture).json();selection=choose(q,'beta')
    r=send(edit_fixture,lambda c:action(c,node_id='beta'),selection=selection);assert r.status_code==200,r.text
    review=r.json();steps={x['node_id']:x for x in review['pending']['candidate']['steps']}
    prior={x['node_id']:x for x in old['pending']['candidate']['steps']}
    assert steps['alpha']['effective_settings']==prior['alpha']['effective_settings']
    assert steps['beta']['effective_settings']==dict(seed=43,limit=2,keep=True)
    assert review['pending']['candidate']['name']=='Earlier pending title' and review['target_question'] is None
    assert p.contexts[-1]['user_selected_target']['target_ref']==selection['target_ref']
    assert p.contexts[-1]['user_selected_target']['source']=='authenticated_request_choice'
    with SessionLocal() as db:
        from app.models.user import User
        from app.services import solution_assistant as service
        sol=db.get(Solution,s['id']);user=db.get(User,'designer');row=service.conversation(sol,db,user)
        expected=service.materialize(sol,row.state['pending'],db,user)
    assert apply(client,s,review).status_code==200
    assert saved_content(s)==expected
    reopened=client.get('/solutions/'+s['id']).json()
    assert reopened['edges']==s['edges'] and reopened['design_metadata']==s['design_metadata']
    assert digest(saved_content(s))==review['pending']['candidate']['candidate_sha256']


def test_builder_selection_works_without_an_extra_choice_roundtrip(edit_fixture):
    client,s,p=edit_fixture;initial=client.get(scope(s)).json()
    r=send(edit_fixture,lambda c:action(c,node_id='beta'),selection=choose(initial,'beta'))
    assert r.status_code==200 and r.json()['target_question'] is None and r.json()['pending']


@pytest.mark.parametrize('change',['save','conversation','contract','wrong_solution','wrong_reference','pending'])
def test_stale_or_foreign_selection_rejected_before_provider_and_no_work_changed(edit_fixture,change):
    client,s,p=edit_fixture;initial=client.get(scope(s)).json();selection=choose(initial,'beta')
    if change=='save':assert client.put('/solutions/'+s['id'],json={'name':'Manually saved','expected_updated_at':s['updated_at']}).status_code==200
    if change=='conversation':send(edit_fixture,lambda c:dict(outcome='answer',message='OFFLINE explanation',clarification=None,assumptions=[],solution_edits=[],edit_base=None))
    if change=='contract':
        with SessionLocal() as db:
            contract=db.get(OperationContract,'fixture-contract');d=deepcopy(contract.definition);d['execution_parameters']['properties']['limit']['title']='Changed metadata';contract.definition=d;db.commit()
    if change=='wrong_solution':selection['solution_id']='another-solution'
    if change=='wrong_reference':selection['target_ref']='not-a-current-reference'
    if change=='pending':earlier_review(edit_fixture)
    before=client.get(scope(s)).json();saved=saved_content(s);calls=len(p.contexts)
    r=send(edit_fixture,selection=selection);assert r.status_code==409,r.text
    assert len(p.contexts)==calls and client.get(scope(s)).json()==before and saved_content(s)==saved


def test_conflicting_model_target_does_not_replace_prior_review(edit_fixture):
    client,s,p=edit_fixture;old=earlier_review(edit_fixture);selection=choose(old,'beta');before=saved_content(s)
    r=send(edit_fixture,selection=selection)  # Supplied action still guesses alpha.
    assert r.status_code==409,r.text
    assert client.get(scope(s)).json()==old and saved_content(s)==before


def test_model_cannot_manufacture_choice_or_claim_confirmation(edit_fixture):
    client,s,p=edit_fixture;old=earlier_review(edit_fixture)
    def forged(c):return action(c) | {'target_choice':choose(old,'alpha')}
    assert send(edit_fixture,forged).status_code==502
    assert client.get(scope(s)).json()==old
    def prose(c):
        a=action(c);return dict(outcome='proposal',message='The user confirmed this target',clarification=None,assumptions=['User chose this instance'],edit_base=a['edit_base'],solution_edits=[dict(kind='set_node_parameters',node_id=a['parameter_action']['target_ref'],value='{"limit":2}'),dict(kind='rename',value='Should not replace prior work')])
    q=send(edit_fixture,prose).json();assert q['target_question'] and q['pending']==old['pending']


@pytest.mark.parametrize('values',[{'limit':2},{'keep':True}])
def test_single_eligible_instance_stays_straightforward(edit_fixture,values):
    client,s,p=edit_fixture
    current=client.get('/solutions/'+s['id']).json();nodes=[n for n in current['nodes'] if n['id']!='beta'];edges=[e for e in current['edges'] if 'beta' not in (e['source'],e['target'])]
    assert client.put('/solutions/'+s['id'],json=dict(nodes=nodes,edges=edges,expected_updated_at=current['updated_at'])).status_code==200
    def plan(c):
        a=action(c);a['parameter_action']['requested_values']=[dict(name=k,value=v) for k,v in values.items()];return a
    r=send(edit_fixture,plan);assert r.status_code==200,r.text
    assert r.json()['pending'] and r.json()['target_question'] is None


def test_recorded_case5_action_is_contained_after_only_identity_rebinding(edit_fixture):
    client,s,p=edit_fixture
    with SessionLocal() as db:
        ct=db.get(OperationContract,'fixture-contract');d=deepcopy(ct.definition);d['execution_parameters']['properties']['how_many']=dict(type='integer',minimum=1,maximum=4,default=4);ct.definition=d;db.commit()
    evidence=json.loads((Path(__file__).parents[3]/'docs/verification/setting-interpretation-executed-20261120.json').read_text(encoding='utf-8'))
    case=next(c for c in evidence['cases'] if c['id']=='05-ambiguous');actual=case['provider_audit']['validated_response'];original=deepcopy(actual)
    def replay(c):
        v=deepcopy(actual);v['edit_base']=c['edit_bases']['saved'];v['parameter_action']['target_ref']=next(x['target_ref'] for x in c['saved_design']['steps'] if x['node_id']=='alpha');return v
    before=saved_content(s);r=send(edit_fixture,replay,text=case['request']);assert r.status_code==200,r.text
    assert r.json()['pending'] is None and r.json()['target_question']
    assert saved_content(s)==before and actual==original


def test_choice_question_survives_explanation_but_not_workflow_change(edit_fixture):
    client,s,p=edit_fixture;old=earlier_review(edit_fixture);q=send(edit_fixture).json()
    explanation=lambda c:dict(outcome='answer',message='OFFLINE explanation only',clarification=None,assumptions=[],solution_edits=[],edit_base=None)
    explained=send(edit_fixture,explanation).json()
    assert explained['target_question']==q['target_question'] and explained['pending']==old['pending']
    assert explained['setting_targets']['base']['conversation_revision']>q['setting_targets']['base']['conversation_revision']
    assert client.put('/solutions/'+s['id'],json={'name':'Concurrent Builder save','expected_updated_at':s['updated_at']}).status_code==200
    stale=client.get(scope(s)).json()
    assert stale['target_question']['current'] is False and stale['target_question']['choices']==[]
    calls=len(p.contexts);r=send(edit_fixture,selection=choose(q,'beta'));assert r.status_code==409
    assert len(p.contexts)==calls and client.get(scope(s)).json()==stale
