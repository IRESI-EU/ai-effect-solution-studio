"""Unpaid harness checks. Synthetic observations are NOT model acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import sqlite3
import pytest
import evaluate as runner
from grade import grade


def example(kind='edit'):
    case=dict(expected=kind,target='Generator North',values={'how_many':2})
    frozen=dict(saved_sha256='saved',expected_candidate_sha256='candidate',target_ref='scoped-north',edit_base={'kind':'pending'})
    observation=dict(http_status=200,saved_sha256='saved',submissions=0,candidate_sha256='candidate',pending_unchanged=False,summary=dict(source='application_diff',status='proposed'))
    audit=dict(provider_stage='schema_validated',validated_response=dict(outcome='setting_edit',message=None,solution_edits=[],assumptions=[],edit_base={'kind':'pending'},parameter_action=dict(operation='set_parameters',target_ref='scoped-north',requested_values=[dict(name='how_many',value=2)])))
    return case,frozen,observation,audit


def test_correct_edit_requires_semantic_review_not_automatic_pass():
    assert grade(*example())['status']=='REVIEW_REQUIRED'


@pytest.mark.parametrize('fault',['target','value','empty','base','boolean','extra','false_compliance','lost_pending','saved_mutation','dispatch','summary'])
def test_stop_on_wrong_interpretation_or_preservation(fault):
    case,f,o,a=example();response=a['validated_response'];action=response['parameter_action']
    if fault=='target':action['target_ref']='scoped-south'
    if fault=='value':action['requested_values'][0]['value']=4
    if fault=='empty':action['requested_values']=[]
    if fault=='base':response['edit_base']={'kind':'saved'}
    if fault=='boolean':action['requested_values'][0]['value']=True
    if fault=='extra':action['requested_values'].append(dict(name='allow_bypass',value=False))
    if fault=='false_compliance':response.update(outcome='answer',parameter_action=None,message='Already done')
    if fault=='lost_pending':o['candidate_sha256']='lost-work'
    if fault=='saved_mutation':o['saved_sha256']='changed'
    if fault=='dispatch':o['submissions']=1
    if fault=='summary':o['summary']={}
    assert grade(case,f,o,a)['status']=='FAIL_STOP'


def test_only_explicit_unchanged_values_allowed():
    case,f,o,a=example();case['permitted_unchanged_values']={'allow_hx':True}
    a['validated_response']['parameter_action']['requested_values'].append(dict(name='allow_hx',value=True))
    assert grade(case,f,o,a)['status']=='REVIEW_REQUIRED'


@pytest.mark.parametrize('expected',['clarification','refusal'])
def test_no_proposal_allowed_for_ambiguity_or_invalid_request(expected):
    case,f,o,a=example(expected);case['values']={};o['pending_unchanged']=True
    a['validated_response']=dict(outcome='clarification',edit_base=None,parameter_action=None,solution_edits=[])
    assert grade(case,f,o,a)['status']=='REVIEW_REQUIRED'
    o['pending_unchanged']=False
    assert grade(case,f,o,a)['status']=='FAIL_STOP'


def test_no_change_must_be_established_by_application():
    case,f,o,a=example('no_change');o.update(summary=dict(source='application_diff',status='no_change'),pending_unchanged=True)
    assert grade(case,f,o,a)['status']=='REVIEW_REQUIRED'
    o['pending_unchanged']=False
    assert grade(case,f,o,a)['status']=='FAIL_STOP'


@pytest.mark.parametrize('stage,detail,category',[('sdk_parse',None,'parsing'),('schema_validated','application_validation','application'),('provider_request',None,'provider_or_transport')])
def test_failure_stage_separate_from_interpretation(stage,detail,category):
    case,f,o,a=example();o.update(http_status=502,detail_stage=detail);a.update(provider_stage=stage,validated_response=None)
    result=grade(case,f,o,a);assert result['status']=='FAIL_STOP' and result['category']==category


def test_exact_six_cases_real_continuation_repeats_and_accounting():
    spec=runner.read(runner.SPEC);cases=spec['cases'];assert len(cases)==spec['max_requests']==6
    assert spec['limit_nano_usd']==spec['reservation_nano_usd']*6==405900000
    assert spec['reservation_nano_usd']==64000*825+3000*4950
    assert cases[0]['instances']==cases[1]['instances']==2
    assert cases[1]['conversation_of']==cases[0]['id'] and cases[1]['select_target']=='Generator South'
    assert cases[1]['message']==cases[0]['message']
    assert not any('clarification_fixture' in c for c in cases)
    historical=runner.read(runner.ROOT/'docs/verification/setting-interpretation-executed-20261120.json')['cases']
    assert cases[4]['message']==historical[0]['request'] and cases[5]['message']==historical[1]['request']


def target_choice_example(model='guess'):
    case,f,o,a=example('target_choice');case.update(message='Ambiguous fixture request',requested_values={'how_many':2})
    f['expected_candidate_sha256']='unchanged-review';f['eligible_targets']=[dict(label='North',target_ref='scoped-north'),dict(label='South',target_ref='scoped-south')]
    o.update(pending_unchanged=True,candidate_sha256='unchanged-review',target_question=dict(current=True,request=case['message'],choices=f['eligible_targets']),application_message=dict(source='application_target_choice'))
    if model=='clarify':a['validated_response']=dict(outcome='clarification',message='Which displayed instance?',clarification='North or South?',parameter_action=None,solution_edits=[],edit_base=None)
    return case,f,o,a


def test_model_guess_and_application_containment_are_reported_separately():
    result=grade(*target_choice_example());assert result['status']=='REVIEW_REQUIRED'
    assert result['model_behaviour']=='model guessed; application contained it'
    result=grade(*target_choice_example('clarify'));assert result['status']=='REVIEW_REQUIRED'
    assert 'genuine model clarification' in result['model_behaviour']


@pytest.mark.parametrize('fault',['replaced_pending','candidate_changed','stale_question','wrong_question','missing_choice','false_success','wrong_value','extra_setting','wrong_ref','wrong_base'])
def test_ambiguity_never_passes_uncontained_or_false_compliance(fault):
    c,f,o,a=target_choice_example();r=a['validated_response']
    if fault=='replaced_pending':o['pending_unchanged']=False
    if fault=='candidate_changed':o['candidate_sha256']='guessed-pending'
    if fault=='stale_question':o['target_question']['current']=False
    if fault=='wrong_question':o['target_question']['request']='Different request'
    if fault=='missing_choice':o['target_question']['choices']=o['target_question']['choices'][:1]
    if fault=='false_success':r.update(outcome='answer',message='Done',parameter_action=None)
    if fault=='wrong_value':r['parameter_action']['requested_values'][0]['value']=4
    if fault=='extra_setting':r['parameter_action']['requested_values'].append(dict(name='other',value=True))
    if fault=='wrong_ref':r['parameter_action']['target_ref']='unoffered'
    if fault=='wrong_base':r['edit_base']={'kind':'saved'}
    assert grade(c,f,o,a)['status']=='FAIL_STOP'


def test_shared_conversation_directory_uses_same_database_and_distinct_ledger(tmp_path):
    a=tmp_path/'A';b=tmp_path/'B';a.mkdir();b.mkdir()
    runner.write(a/'case.private.json',dict(id='A'));runner.write(b/'case.private.json',dict(id='B',conversation_of='A'))
    assert runner.state_directory(a)==runner.state_directory(b)==a
    ae,be=runner.environment(a),runner.environment(b)
    assert ae['DATABASE_URL']==be['DATABASE_URL'] and ae['SESSION_COOKIE_NAME']==be['SESSION_COOKIE_NAME']
    assert ae['DESIGN_AI_SCOPED_ACCEPTANCE_FILE']!=be['DESIGN_AI_SCOPED_ACCEPTANCE_FILE']
    assert ae['OPENAI_API_KEY']==be['OPENAI_API_KEY']==''


def test_no_approval_no_activation_or_key_read(tmp_path,monkeypatch):
    p=tmp_path/'approval.json';runner.write(p,dict(approved=False,expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    monkeypatch.setattr(runner,'verify',lambda d:{})
    runner.write(tmp_path/'manifest.private.json',{})
    with pytest.raises(RuntimeError,match='Separate concrete'):
        runner.activate(tmp_path,p,tmp_path/'missing.env',tmp_path)
    assert not (tmp_path/'evaluation.private.sqlite').exists()


def test_manifest_rejects_changed_source(tmp_path,monkeypatch):
    runner.write(tmp_path/'manifest.private.json',dict(source_files={'old':'old'},spec_sha256=runner.sha(runner.SPEC)))
    monkeypatch.setattr(runner,'source_files',lambda:{'new':'new'})
    with pytest.raises(RuntimeError,match='changed'):runner.verify(tmp_path)


def parent(tmp_path,status='REVIEW_REQUIRED',closed=0):
    approval=dict(manifest_sha256=runner.sha(tmp_path/'manifest.private.json'),expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),limit_nano_usd=676500000)
    with sqlite3.connect(tmp_path/'evaluation.private.sqlite') as db:
        db.executescript('CREATE TABLE policy(value TEXT,closed INTEGER); CREATE TABLE attempts(id TEXT,reserved INTEGER,status TEXT,result TEXT,review TEXT);')
        db.execute('INSERT INTO policy VALUES (?,?)',(json.dumps(dict(approval=approval)),closed))
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?)',('01-original',67650000,status,'{}',None))


@pytest.mark.parametrize('status,closed',[('STARTED',0),('FAIL_STOP',1),('REVIEW_REQUIRED',0),('PASS',1)])
def test_incomplete_failed_or_unreviewed_attempt_cannot_dispatch(tmp_path,monkeypatch,status,closed):
    runner.write(tmp_path/'manifest.private.json',{});parent(tmp_path,status,closed)
    monkeypatch.setattr(runner,'verify',lambda d:{})
    monkeypatch.setattr(runner,'child',lambda *a:pytest.fail('No worker may start'))
    with pytest.raises(RuntimeError):runner.attempt(tmp_path)


def test_semantic_failure_closes_scope_and_cannot_be_overridden(tmp_path,monkeypatch):
    runner.write(tmp_path/'manifest.private.json',{});parent(tmp_path)
    monkeypatch.setattr(runner,'verify',lambda d:{})
    runner.review(tmp_path,'01-original','fail','Human review detected a false compliance claim.')
    with sqlite3.connect(tmp_path/'evaluation.private.sqlite') as db:
        assert db.execute('SELECT closed FROM policy').fetchone()==(1,)
    with pytest.raises(RuntimeError):runner.review(tmp_path,'01-original','pass','Cannot override this recorded failure.')


def test_accounting_preserves_uncertainty_and_never_claims_account_balance(tmp_path):
    runner.write(tmp_path/'manifest.private.json',{});parent(tmp_path,status='STARTED')
    value=runner.accounting(tmp_path)
    assert value['uncertain_reserved_usd']==0.06765 and value['cumulative_conservative_estimated_usd']==0
    assert value['lifetime_reserved_usd']==0.06765 and value['remaining_authorised_calls']==5
    assert not value['next_dispatch_permitted'] and value['account_balance'].startswith('NOT_OBSERVED')
    with sqlite3.connect(tmp_path/'evaluation.private.sqlite') as db:db.execute('update policy set closed=1')
    closed=runner.accounting(tmp_path)
    assert closed['remaining_authorised_calls']==closed['remaining_authorised_reservations_usd']==0
    assert closed['uncertain_reserved_usd']==0.06765


def test_accounting_reports_actual_settled_usage_separately(tmp_path):
    runner.write(tmp_path/'manifest.private.json',{});parent(tmp_path,status='PASS')
    d=tmp_path/'01-original';d.mkdir()
    with sqlite3.connect(d/'acceptance.private.sqlite') as db:
        db.execute('create table acceptance_requests(reserved integer,held integer,usage text,state text)')
        db.execute('insert into acceptance_requests values(?,?,?,?)',(67650000,825000+495000,json.dumps(dict(input_tokens=1000,output_tokens=100)),'settled'))
    value=runner.accounting(tmp_path)
    assert value['cumulative_conservative_estimated_usd']==0.00132 and value['uncertain_reserved_usd']==0
    assert value['usage']==dict(input_tokens=1000,output_tokens=100)
    assert value['lifetime_reserved_usd']==0.06765 and value['next_dispatch_permitted']
