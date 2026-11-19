"""One six-request exercise. Operator capture only; never sends/Applies/Runs."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,sqlite3,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'apps/api'),str(ROOT/'deploy/pending_recovery_acceptance'),str(ROOT/'deploy/genuine_acceptance')]
import control as recovery
from app.services.scoped_ai_acceptance import Budget,initialize,binding,RESERVATION
from app.services.design_ai_provider import SAVED_SOLUTION_SYSTEM
from app.services.provider_evidence import digest,response_format
from app.schemas.solution_assistant import SavedSolutionResponse
load=recovery.load;write=recovery.write;sha=recovery.sha;snapshot=recovery.snapshot;audits=recovery.audits
CRITERIA='docs/COMPLETE_JOURNEY_CRITERIA_2026-11-19.md'

def manifest(d):return load(d/'exercise.private.json')
def frozen(d):
    m=manifest(d)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==m['serving_commit']
    assert all(sha(ROOT/n)==h for n,h in m['files'].items())
    assert all(sha(d/n)==h for n,h in m['runtime_files'].items())
    return m

def close(d):recovery.close(d)
def stop(d,case,reason):
    if not (d/'hard-stop.private.json').exists():write(d/'hard-stop.private.json',dict(case=case,reason=reason))
    close(d)

def freeze(d,identifier,authority):
    p=load(d/'profile.private.json');runtime=load(d/'runtime-policy.private.json')
    assert runtime==dict(provider_class='OpenAIProvider',provider_override_present=False,offline_fixture=False,workflow_submission_disabled=False)
    assert not (d/'acceptance.private.sqlite').exists() and not audits(d)
    assert load(d/'preflight.private.json')['passed'] and RESERVATION*6<=450000000
    snap=snapshot(d,identifier);assert not snap['solution']['nodes'] and not snap['conversation']['messages'] and snap['submissions']==0
    files=[CRITERIA,'deploy/full_journey_acceptance/control.py']+[str(f.relative_to(ROOT)).replace('\\','/') for f in (ROOT/'apps/api/app').rglob('*.py')]
    runtime_files=[f for root in ('contracts','node-source','wp3-source') for f in (d/root).rglob('*') if f.is_file() and '__pycache__' not in str(f)]
    runtime_files += [d/'fixture-input.json']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert load(d/'serving.private.json')['portal_base']==commit
    m=dict(serving_commit=commit,wp3_commit=p['wp3_commit'],solution_id=identifier,initial=snap,authorization_sha256=sha(authority),
        approved_binding=binding(SimpleNamespace(database_url='sqlite:///'+(d/'portal.sqlite').as_posix()),snap['solution']['created_by_user_id'],identifier),
        files={n:sha(ROOT/n) for n in files},runtime_files={f.relative_to(d).as_posix():sha(f) for f in runtime_files},
        prompt_sha256=hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest(),schema_sha256=digest(response_format(SavedSolutionResponse)['schema']),max_requests=6,limit_nano=450000000)
    write(d/'exercise.private.json',m)
    print(json.dumps({k:m[k] for k in ('serving_commit','wp3_commit','prompt_sha256','schema_sha256','max_requests','limit_nano')}))

def activate(d):
    m=frozen(d);assert snapshot(d,m['solution_id'])==m['initial']
    expiry=(datetime.now(timezone.utc)+timedelta(hours=23,minutes=59)).isoformat()
    initialize(d/'acceptance.private.sqlite',approved_binding=m['approved_binding'],authorization_ref='User complete genuine journey authority sha256:'+m['authorization_sha256'],expires_at=expiry,max_requests=6,limit_nano=450000000)
    write(d/'activation.private.json',dict(expires_at=expiry,max_requests=6,limit_usd=.45))
    print(json.dumps(dict(activated_once=True,max_requests=6,reserved_max_usd=6*RESERVATION/1e9,expires_at=expiry)))

def before(d,case):
    m=frozen(d);n=int(case[1:]);assert 1<=n<=6 and not (d/'hard-stop.private.json').exists()
    for i in range(1,n):assert load(d/f'J{i}.score.private.json')['result']=='PASS'
    assert Budget(d/'acceptance.private.sqlite').availability()['can_request'] and len(audits(d))==n-1
    snap=snapshot(d,m['solution_id']);assert snap['submissions']==(0 if n<3 else 1)
    if n>=3:assert load(d/'first-run-score.private.json')['result']=='PASS'
    write(d/(case+'.before.private.json'),dict(snapshot=snap,audit_count=n-1))
    print(json.dumps(dict(case=case,ready=True,submissions=snap['submissions'],revision=snap['conversation']['conversation_revision'])))

def after(d,case):
    m=frozen(d);b=load(d/(case+'.before.private.json'));snap=snapshot(d,m['solution_id']);records=audits(d)
    try:
        assert len(records)==b['audit_count']+1
        audit=records[-1];assert audit['provider_stage']=='schema_validated' and audit['response_schema_sha256']==m['schema_sha256']
        assert audit['returned_model']=='gpt-5.4-mini-2026-03-17' and audit['returned_service_tier'] in (None,'default') and audit['usage'] is not None
        assert snap['solution']==b['snapshot']['solution'] and snap['submissions']==b['snapshot']['submissions']
        assert snap['conversation']['conversation_revision']==b['snapshot']['conversation']['conversation_revision']+1
        response=recovery.recover(audit,snap)
        write(d/(case+'.after.private.json'),dict(before=b['snapshot'],after=snap,response=response,audit=audit,actual_response_hash_verified=True))
        print(json.dumps(dict(case=case,response=response,hash_verified=True,usage=audit['usage']),ensure_ascii=False))
    except Exception:
        write(d/(case+'.failure.private.json'),dict(before=b,after=snap,audit=records[-1] if records else None));stop(d,case,'Required response/accounting/state observation failed');raise

def score(d,case,result,reason):
    frozen(d);r=load(d/(case+'.after.private.json'))
    # Semantic scores are made only after inspecting the actual response/state.
    write(d/(case+'.score.private.json'),dict(result=result,dimensions=dict.fromkeys(('intent','correctness','progress','state'),result),reason=reason))
    if result!='PASS':stop(d,case,reason)
    print(json.dumps(dict(case=case,result=result,scope_closed=result!='PASS')))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['freeze','activate','before','after','score','close']);a.add_argument('--directory',required=True,type=Path);a.add_argument('--solution');a.add_argument('--authorization',type=Path);a.add_argument('--case');a.add_argument('--result',choices=['PASS','FAIL']);a.add_argument('--reason');v=a.parse_args();d=v.directory.resolve()
    if v.action=='freeze':freeze(d,v.solution,v.authorization)
    elif v.action=='activate':activate(d)
    elif v.action=='before':before(d,v.case)
    elif v.action=='after':after(d,v.case)
    elif v.action=='score':score(d,v.case,v.result,v.reason)
    else:close(d)
