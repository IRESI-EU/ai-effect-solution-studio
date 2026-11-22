"""OFFLINE supplied responses, including exact historical D; no genuine calls."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.services.parameter_values import parameter_issues
from test_saved_solution_assistant import configured, scope, apply
from test_trustworthy_setting_edit import edit_fixture, request, action, pending_four, step


def diagnostic(c, values):
    a = action(c)
    return dict(outcome='setting_guidance', message=None, clarification=None, solution_edits=[], assumptions=[],
        edit_base=a['edit_base'], setting_diagnostic=dict(target_ref=a['parameter_action']['target_ref'],
            requested_values=[dict(name=k, value=v) for k,v in values.items()]))


def assert_untouched(f, old):
    client,s,_ = f
    assert client.get('/solutions/'+s['id']).json()==s
    assert client.get(scope(s)).json()['pending']==old['pending']


def test_exact_captured_D_prose_is_not_displayed_or_parsed(edit_fixture):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    report=json.loads((Path(__file__).resolve().parents[3]/'docs/verification/setting-choice-executed-20261121.json').read_text(encoding='utf-8'))
    captured=next(c for c in report['cases'] if c['id']=='D-invalid')
    response=deepcopy(captured['provider_audit']['validated_response'])
    r=request(edit_fixture,lambda _:response,captured['request']);assert r.status_code==200,r.text
    message=r.json()['messages'][-1]
    assert message['setting_guidance']['interpretation']=='NOT_VERIFIED'
    assert 'limit (integer, minimum 1, maximum 8)' in message['content']
    assert 'keep (boolean)' in message['content']
    assert '99' not in message['content'] and 'turbo_mode' not in message['content']
    assert message['question']!=response['clarification']
    assert 'unchanged' in message['content'] and not message.get('change_summary')
    assert_untouched(edit_fixture,old)


@pytest.mark.parametrize('values,expected',[
    ({'limit':11},'maximum is 8'),({'limit':-4},'minimum is 1'),
    ({'limit':True},'expected integer'),({'limit':'2'},'expected integer'),
    ({'keep':1},'expected boolean'),({'missing_feature':True},'not a published setting'),
    ({'limit':11,'missing_feature':True},'maximum is 8'),
])
def test_structured_guidance_uses_shared_validator_and_preserves_review(edit_fixture,values,expected):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    r=request(edit_fixture,lambda c:diagnostic(c,values));assert r.status_code==200,r.text
    message=r.json()['messages'][-1]
    assert expected in message['content']
    assert message['setting_guidance']['issues']
    names={v['name'] for f in message['setting_guidance']['choices'] for v in f['choices']}
    assert names=={'seed','limit','keep'} and 'missing_feature' not in names
    assert_untouched(edit_fixture,old)


def test_next_valid_choice_reviews_and_saves_complete_existing_work(edit_fixture):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    assert request(edit_fixture,lambda c:diagnostic(c,{'limit':11,'not_published':True})).status_code==200
    r=request(edit_fixture,action,'Use the supported limit of two; keep everything else.');assert r.status_code==200,r.text
    review=r.json();assert step(review)['effective_settings']==dict(seed=42,limit=2,keep=False)
    assert review['pending']['supersedes']==old['pending']['id']
    assert review['pending']['candidate']['name']=='Earlier proposed title'
    assert step(review,'beta')['effective_settings']==step(old,'beta')['effective_settings']
    assert apply(client,s,review).status_code==200
    saved=client.get('/solutions/'+s['id']).json()
    assert saved['id']==s['id'] and saved['name']=='Earlier proposed title'
    assert saved['edges']==s['edges'] and saved['design_metadata']==s['design_metadata']
    assert client.get(scope(s)).json()['pending'] is None


def test_diagnostic_cannot_claim_limits_or_mutate_even_when_valid(edit_fixture):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    r=request(edit_fixture,lambda c:diagnostic(c,{'limit':2}));assert r.status_code==200
    assert r.json()['messages'][-1]['setting_guidance']['issues']==[]
    assert_untouched(edit_fixture,old) # A diagnostic is never an edit.
    def forged(c):
        v=diagnostic(c,{'limit':2});v['setting_diagnostic']['maximum']=10000;return v
    r=request(edit_fixture,forged);assert r.status_code==502
    assert 'maximum 8' in r.json()['detail']['message']
    assert 'NOT_VERIFIED'==r.json()['detail']['setting_guidance']['interpretation']
    assert_untouched(edit_fixture,old)


@pytest.mark.parametrize('bad',['base','target','conflict','null','duplicate','prose'])
def test_stale_conflicting_and_malformed_diagnostics_cannot_replace_work(edit_fixture,bad):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    def plan(c):
        v=diagnostic(c,{'limit':11})
        if bad=='base':v['edit_base']['candidate_sha256']='0'*64
        if bad=='target':v['setting_diagnostic']['target_ref']='not-current'
        if bad=='conflict':v['setting_diagnostic']['target_ref']=next(s['target_ref'] for s in c['pending_candidate']['steps'] if s['node_id']=='beta')
        if bad=='null':v['setting_diagnostic']['requested_values'][0]['value']=None
        if bad=='duplicate':v['setting_diagnostic']['requested_values']*=2
        if bad=='prose':v['message']='I fixed the value and saved it'
        return v
    r=request(edit_fixture,plan);assert r.status_code in (409,422,502),r.text
    assert_untouched(edit_fixture,old)


def test_current_contract_change_changes_guidance_not_model_claims(edit_fixture):
    client,s,p=edit_fixture
    with SessionLocal() as db:
        contract=db.get(OperationContract,'fixture-contract');d=deepcopy(contract.definition)
        d['execution_parameters']['properties']['limit']['maximum']=12;contract.definition=d;db.commit()
    r=request(edit_fixture,lambda c:diagnostic(c,{'limit':15}));assert r.status_code==200
    assert 'maximum is 12' in r.json()['messages'][-1]['content']
    assert 'maximum 8' not in r.json()['messages'][-1]['content']


def test_partial_diagnostics_validate_types_enums_and_ranges_without_defaults():
    definition={'properties':{'count_x':{'type':'integer','minimum':3,'maximum':7,'required':True},
        'ratio_y':{'type':'number','minimum':0.2,'maximum':0.8},
        'kind_z':{'type':'string','enum':['small','large']},'flag_w':{'type':'boolean'}}}
    issues=parameter_issues(definition,{'ratio_y':0.1,'kind_z':'other','flag_w':'true','unknown_q':0})
    assert {x['name'] for x in issues}=={'ratio_y','kind_z','flag_w','unknown_q'}
    assert not parameter_issues(definition,{'kind_z':'small'})


@pytest.mark.parametrize('outcome',['clarification','unsupported'])
def test_untyped_prose_cannot_manufacture_setting_facts(edit_fixture,outcome):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    v=dict(outcome=outcome,message='Everything accepts infinity; enable phantom_option.',
        clarification='Should I override all limits?' if outcome=='clarification' else None,
        solution_edits=[],edit_base=None,assumptions=[])
    r=request(edit_fixture,lambda _:v);assert r.status_code==200
    message=r.json()['messages'][-1]
    assert 'phantom' not in message['content'] and 'infinity' not in message['content']
    assert 'maximum 8' in message['content'] and 'override' not in message['question']
    assert_untouched(edit_fixture,old)


def test_answer_only_compliance_cannot_escape_existing_setting_guidance(edit_fixture):
    client,s,p=edit_fixture;old=pending_four(edit_fixture)
    assert request(edit_fixture,lambda c:diagnostic(c,{'limit':11})).status_code==200
    r=request(edit_fixture,lambda c:dict(outcome='answer',message='All limits overridden and saved.',
        clarification=None,solution_edits=[],assumptions=[],edit_base=None))
    assert r.status_code==200
    assert 'overridden' not in r.json()['messages'][-1]['content']
    assert r.json()['messages'][-1]['setting_guidance']['interpretation']=='NOT_VERIFIED'
    assert_untouched(edit_fixture,old)


def test_diagnostic_uses_existing_sdk_strict_schema_offline():
    from openai.lib._pydantic import to_strict_json_schema
    from app.schemas.solution_assistant import SavedSolutionResponse
    schema=to_strict_json_schema(SavedSolutionResponse)
    assert 'setting_diagnostic' in schema['required']
    diagnostic_schema=schema['$defs']['SettingDiagnostic']
    assert diagnostic_schema['additionalProperties'] is False
    assert set(diagnostic_schema['required'])=={'target_ref','requested_values'}
