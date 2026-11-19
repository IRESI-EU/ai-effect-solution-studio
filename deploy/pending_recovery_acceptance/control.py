"""Operator-only one-scope recovery capture. No chat/Apply/Run or model calls.

Paid requests and Apply happen solely in the ordinary browser. Mechanical checks
are evidence, not semantic scores; score each actual response separately.
"""
import argparse
from datetime import datetime,timedelta,timezone
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'apps/api'),str(ROOT/'deploy/genuine_acceptance')]
import scope as scoped
from app.schemas.solution_assistant import SavedSolutionResponse
from app.services.design_ai_provider import SAVED_SOLUTION_SYSTEM
from app.services.provider_evidence import digest,response_format
from app.services.solution_assistant import digest as design_digest
from app.services.scoped_ai_acceptance import Budget,binding,initialize,MODEL,MAX_INPUT,MAX_OUTPUT,RESERVATION,INPUT_NANO,OUTPUT_NANO


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def manifest(directory):return load(directory/'exercise.private.json')
def audits(directory):return [json.loads(line) for line in (directory/'provider-audit.private.jsonl').read_text(encoding='utf-8').splitlines()]


def snapshot(directory,identifier):
    p,client,_=scoped.load(directory)
    solution=scoped.get(client,p,'/solutions/'+identifier)
    conversation=scoped.get(client,p,'/design-ai/solutions/'+identifier)
    with sqlite3.connect((directory/'portal.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        count=db.execute('SELECT COUNT(*) FROM execution_submissions').fetchone()[0]
        row=db.execute('SELECT state FROM design_ai_drafts WHERE owner_id=?', (solution['created_by_user_id'],)).fetchall()
    state=next((json.loads(r[0]) for r in row if json.loads(r[0]).get('solution_id')==identifier),None)
    return dict(solution=solution,conversation=conversation,stored_state=state,submissions=count)


def freeze(directory,identifier,authorization):
    p,_,_=scoped.load(directory);runtime=load(directory/'runtime-policy.private.json')
    assert not p.get('offline_ui_fixture') and p.get('workflow_submission_disabled')
    assert runtime==dict(provider_class='OpenAIProvider',provider_override_present=False,offline_fixture=False,workflow_submission_disabled=True)
    assert not (directory/'acceptance.private.sqlite').exists() and not audits(directory)
    assert load(directory/'preflight.private.json')['passed']
    snap=snapshot(directory,identifier);assert not snap['solution']['nodes'] and not snap['conversation']['messages'] and snap['submissions']==0
    assert RESERVATION==67_650_000 and 3*RESERVATION<=210_000_000 and (MAX_INPUT,MAX_OUTPUT)==(64000,3000)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert load(directory/'serving.private.json')['portal_base']==commit
    subprocess.run(['git','diff','--exit-code','3ba51d9e7d665d5ebbea79d6235514bad0dee905','--','apps/api/app','apps/web'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    files=['apps/api/app/services/design_ai_provider.py','apps/api/app/schemas/solution_assistant.py','apps/api/app/services/solution_assistant.py','apps/api/app/routers/solution_assistant.py','apps/api/app/services/scoped_ai_acceptance.py','docs/PENDING_GENUINE_RECOVERY_CRITERIA_2026-11-19.md']
    record=dict(serving_commit=commit,solution_id=identifier,approved_binding=binding(SimpleNamespace(database_url='sqlite:///'+(directory/'portal.sqlite').as_posix()),snap['solution']['created_by_user_id'],identifier),authorization_sha256=sha(authorization),prompt_sha256=hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest(),wire_schema_sha256=digest(response_format(SavedSolutionResponse)['schema']),file_sha256={n:sha(ROOT/n) for n in files},max_requests=3,limit_nano=210000000,reservation_nano=RESERVATION,initial=snap)
    write(directory/'exercise.private.json',record)
    print(json.dumps({'frozen':True,'serving_commit':commit,'schema_sha256':record['wire_schema_sha256'],'paid_requests':0,'ledgers_created':0}))


def unchanged(directory):
    m=manifest(directory)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==m['serving_commit']
    assert all(sha(ROOT/n)==v for n,v in m['file_sha256'].items())
    assert hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest()==m['prompt_sha256']
    assert digest(response_format(SavedSolutionResponse)['schema'])==m['wire_schema_sha256']
    return m


def activate(directory):
    m=unchanged(directory);assert m['max_requests']==3 and m['limit_nano']==210000000
    assert snapshot(directory,m['solution_id'])==m['initial']
    expiry=(datetime.now(timezone.utc)+timedelta(hours=23,minutes=59)).isoformat()
    initialize(directory/'acceptance.private.sqlite',approved_binding=m['approved_binding'],authorization_ref='User narrow genuine recovery authority sha256:'+m['authorization_sha256'],expires_at=expiry,max_requests=3,limit_nano=210000000)
    assert Budget(directory/'acceptance.private.sqlite').availability()['max_calls']==3
    write(directory/'activation.private.json',dict(binding=m['approved_binding'],expires_at=expiry,requests=3,limit_usd=.21))
    print(json.dumps({'activated_once':True,'max_requests':3,'limit_usd':.21,'reservation_usd':RESERVATION/1e9,'expires_at':expiry,'calls_made':0}))


def before(directory,case):
    m=unchanged(directory);index=int(case[1]);assert case in ('R1','R2','R3')
    for n in range(1,index):assert load(directory/f'R{n}.score.private.json')['result']=='PASS'
    assert not (directory/'hard-stop.private.json').exists()
    assert Budget(directory/'acceptance.private.sqlite').availability()['can_request']
    snap=snapshot(directory,m['solution_id']);records=audits(directory);assert len(records)==index-1
    assert snap['solution']==m['initial']['solution'] and snap['submissions']==0
    write(directory/(case+'.before.private.json'),dict(snapshot=snap,audit_count=len(records)))
    pending=snap['conversation']['pending']
    print(json.dumps({'case':case,'revision':snap['conversation']['conversation_revision'],'pending_id':pending['id'] if pending else None,'history_messages':len(snap['conversation']['messages']),'paid_requests_so_far':len(records)}))


def recover(audit,snap):
    original=audit['validated_response'];assert original is not None
    value=deepcopy(original)
    if snap['conversation']['messages']:
        reply=snap['conversation']['messages'][-1]
        if reply['role']=='assistant':value['message']=reply['content']
    variants=[]
    for edit in value['solution_edits']:
        text=edit['value'];options=[text]
        try:
            obj=json.loads(text)
            if isinstance(obj,(dict,list)):
                options += [json.dumps(obj,separators=s,ensure_ascii=a) for s in [(',',':'),(',',': '),(', ',':'),(', ',': ')] for a in (True,False)]
                options += [json.dumps(obj,indent=i,ensure_ascii=False) for i in (2,4)]
        except (ValueError,TypeError):pass
        variants.append(list(dict.fromkeys(options)))
    size=1
    for options in variants:size*=len(options)
    assert size<=4096,'Exact response formatting recovery exceeded bounded local search'
    found=[]
    for texts in itertools.product(*variants):
        candidate=deepcopy(value)
        for edit,text in zip(candidate['solution_edits'],texts):edit['value']=text
        if digest(candidate)==audit['validated_response_sha256']:found.append(candidate)
    assert len(found)==1,'Cannot recover the exact original structured-response hash'
    return SavedSolutionResponse.model_validate(found[0]).model_dump(mode='json')


def after(directory,case):
    m=unchanged(directory);prior=load(directory/(case+'.before.private.json'));snap=snapshot(directory,m['solution_id']);records=audits(directory)
    try:
        assert len(records)==prior['audit_count']+1
        audit=records[-1];assert audit['provider_stage']=='schema_validated' and audit['response_schema_sha256']==m['wire_schema_sha256']
        assert audit['returned_model']==MODEL and audit['returned_service_tier'] in (None,'default') and audit['usage'] is not None
        assert snap['solution']==prior['snapshot']['solution'] and snap['submissions']==0
        assert snap['conversation']['conversation_revision']==prior['snapshot']['conversation']['conversation_revision']+1
        response=recover(audit,snap)
        # Freeze mechanical proof first. Semantic scoring is explicit after inspecting the actual response.
        write(directory/(case+'.after.private.json'),dict(before=prior['snapshot'],after=snap,response=response,audit=audit,actual_response_hash_verified=True))
        print(json.dumps({'case':case,'actual_response':response,'audit_hash_verified':True,'usage':audit['usage'],'pending_id':(snap['conversation']['pending'] or {}).get('id'),'submissions':0},ensure_ascii=False))
    except Exception as exc:
        write(directory/(case+'.failure.private.json'),dict(before=prior['snapshot'],after=snap,audit=records[-1] if records else None,error=type(exc).__name__+': '+str(exc)))
        stop(directory,case,'Response, accounting or preservation proof failed')
        raise


def score(directory,case,result,dimensions=None):
    m=unchanged(directory)
    if result=='PASS':
        r=load(directory/(case+'.after.private.json'));before=r['before'];after=r['after'];response=r['response'];pending=after['conversation']['pending'];candidate=pending['candidate'] if pending else None
        old=before['conversation']['pending']
        if case=='R2':assert response['outcome']=='answer' and not response['solution_edits'] and response['edit_base'] is None and pending==old
        else:
            assert response['outcome']=='proposal' and candidate and pending['current'] and len(candidate['steps'])==2 and len(candidate['connections'])==1
            gen=next(s for s in candidate['steps'] if s['operation_name']=='GenerateTopology');view=next(s for s in candidate['steps'] if s['operation_name']=='RenderTopologies')
            assert candidate['connections']==[{'source':gen['target_ref'],'target':view['target_ref'],'binding':{'source_slot':'networks','target_slot':'networks'}}]
            assert view['label'].endswith('Drawing A') and gen['effective_settings']==dict(how_many=2 if case=='R1' else 3,allow_hx=True,allow_bypass=True)
            expected=dict(kind='saved' if case=='R1' else 'pending',expected_updated_at=before['conversation']['expected_updated_at'],conversation_revision=before['conversation']['conversation_revision'],proposal_id=old['id'] if old else None,candidate_sha256=old['candidate']['candidate_sha256'] if old else None)
            assert response['edit_base']==expected
            if case=='R3':
                assert pending['supersedes']==old['id'] and pending['id']!=old['id']
                assert [s['node_id'] for s in candidate['steps']]==[s['node_id'] for s in old['candidate']['steps']]
                assert len(response['solution_edits'])==1 and response['solution_edits'][0]['kind']=='set_node_parameters'
                oldgen=next(s for s in old['candidate']['steps'] if s['operation_name']=='GenerateTopology')
                assert response['solution_edits'][0]['node_id']==oldgen['target_ref'] and json.loads(response['solution_edits'][0]['value'])==dict(how_many=3)
                assert len(after['stored_state']['pending']['edits'])>len(before['stored_state']['pending']['edits'])
        assert after['solution']==m['initial']['solution']
    if result=='FAIL':assert dimensions is not None and 'FAIL' in dimensions
    dimensions=dimensions or ['PASS']*4
    write(directory/(case+'.score.private.json'),dict(case=case,result=result,dimensions=dict(zip(('intent','correctness','progress','state'),dimensions)),semantic_review='Actual response inspected against frozen criteria; no mid-exercise correction'))
    if result!='PASS':stop(directory,case,'A required observation failed')
    print(json.dumps({'case':case,'result':result,'scope_closed':result!='PASS'}))


def stop(directory,case,reason):
    if not (directory/'hard-stop.private.json').exists():write(directory/'hard-stop.private.json',dict(case=case,reason=reason))
    close(directory)


def close(directory):
    budget=Budget(directory/'acceptance.private.sqlite');budget.close()
    with sqlite3.connect(budget.path) as db:rows=db.execute('SELECT reserved,held,usage,state FROM acceptance_requests ORDER BY id').fetchall()
    usages=[json.loads(r[2]) for r in rows if r[2] is not None]
    summary=dict(closed=True,requests=len(rows),known_input_tokens=sum(u['input_tokens'] for u in usages),known_output_tokens=sum(u['output_tokens'] for u in usages),usage_complete=len(usages)==len(rows),accounted_usd=sum(r[1] for r in rows)/1e9,lifetime_reserved_usd=sum(r[0] for r in rows)/1e9)
    with (directory/'closed-summary.private.json').open('w') as f:json.dump(summary,f,indent=2)
    print(json.dumps(summary))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['freeze','activate','before','after','score','close']);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--solution');parser.add_argument('--authorization',type=Path);parser.add_argument('--case',choices=['R1','R2','R3']);parser.add_argument('--result',choices=['PASS','FAIL']);parser.add_argument('--dimensions',nargs=4,choices=['PASS','FAIL'])
    a=parser.parse_args();d=a.directory.resolve()
    if a.action=='freeze':freeze(d,a.solution,a.authorization)
    elif a.action=='activate':activate(d)
    elif a.action=='before':before(d,a.case)
    elif a.action=='after':after(d,a.case)
    elif a.action=='score':score(d,a.case,a.result,a.dimensions)
    else:close(d)
