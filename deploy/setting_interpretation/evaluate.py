"""Unpaid prepare/check; separately authorised one-at-a-time real-path evaluation.

Never changes production app/provider code. No model overrides in live mode.
A/B share one actual SQLite database, cookie, owned solution and conversation.
C-F are isolated. Every attempt has a fresh one-call ledger under one six-call
parent. Fixture setup never fabricates clarification or a model result.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SPEC=HERE/'cases.json'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with Path(p).open('x',encoding='utf-8') as f: json.dump(v,f,indent=2,ensure_ascii=False)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def source_files():
    files=[p for folder in [ROOT/'apps/api/app',ROOT/'apps/web',HERE] for p in folder.rglob('*')
            if p.is_file() and p.suffix in {'.py','.json','.ts','.tsx','.cjs','.css'} and not {'__pycache__','node_modules','.next'} & set(p.parts)]
    files += [ROOT/'deploy/genuine_acceptance/workspace.py',ROOT/'deploy/parameter_onboarding/review_workspace.py']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files}
def dependencies():
    return dict(python=sys.version.split()[0],packages={name:importlib.metadata.version(name) for name in ('openai','httpx','fastapi','pydantic','sqlalchemy')})
def state_directory(d):
    case=read(d/'case.private.json')
    return d.parent/case['conversation_of'] if case.get('conversation_of') else d


def environment(d):
    state=state_directory(d)
    env=dict(os.environ)
    # Do not inherit a key, budget authority, old grant, execution or dotenv profile.
    for k in list(env):
        if k.startswith(('OPENAI_','DESIGN_AI_','ORCHESTRATOR_','PORTUGUESE_','LOCAL_DUTCH_','AIE18_')):env.pop(k)
    env.update(PYTHONPATH=str(ROOT/'apps/api'),PYTHONDONTWRITEBYTECODE='1',OPENAI_API_KEY='',
        DATABASE_URL='sqlite:///'+(state/'portal.sqlite').as_posix(),SESSION_COOKIE_NAME='aie_interpret_'+state.name,
        BOOTSTRAP_ADMIN_EMAIL='',BOOTSTRAP_ADMIN_PASSWORD='',SERVICE_CONTRACT_PATH=str(d/'service-contracts'),
        DESIGN_AI_ENABLED='true',DESIGN_AI_MODEL='gpt-5.4-mini-2026-03-17',DESIGN_AI_REASONING_EFFORT='none',
        DESIGN_AI_MAX_OUTPUT_TOKENS='3000',DESIGN_AI_TIMEOUT_SECONDS='60',DESIGN_AI_CONTEXT_CHARS='48000',
        DESIGN_AI_SCOPED_ACCEPTANCE_FILE=str(d/'acceptance.private.sqlite'),ORCHESTRATOR_BASE_URL='',
        ORCHESTRATOR_API_KEY='',REDIS_URL='',ARTIFACT_BASE_PATH=str(d/'outputs'),SECURE_COOKIES='false')
    return env
def child(d,mode):
    env=environment(d)
    with (d/(mode+'.private.log')).open('x',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'_'+mode,'--directory',str(d)],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode: raise RuntimeError('Case worker failed; inspect ignored '+mode+' diagnostics. No retry.')
def application():
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB,'sqlite')
    def sqlite_jsonb(_type,compiler,**kwargs): return 'JSON'
    from app.main import app
    from app.services.design_ai_provider import get_provider,OpenAIProvider
    if app.dependency_overrides or not isinstance(get_provider(),OpenAIProvider):raise RuntimeError('Real application/provider required; overrides forbidden')
    from fastapi.responses import JSONResponse
    @app.middleware('http')
    async def no_execution(request,call_next):
        if request.method not in {'GET','HEAD'} and (request.url.path.startswith(('/deployments','/workflows/submit')) or request.url.path.endswith('/runtime/verify')):
            return JSONResponse(status_code=409,content={'detail':'Setting interpretation only; execution unavailable.'})
        return await call_next(request)
    return app
def client(app,d):
    from fastapi.testclient import TestClient
    c=TestClient(app,raise_server_exceptions=False)
    r=c.post('/auth/login',json={k:read(d/'credentials.private.json')['designer'][k] for k in ('email','password')})
    if r.status_code!=200:raise RuntimeError('Normal fixture sign-in failed')
    return c,r.json()['id']
def snapshot(d):
    from app.db import SessionLocal
    from app.models.solution import Solution
    from app.models.user import User
    from app.models.execution_submission import ExecutionSubmission
    from app.services import solution_assistant as s
    m=read(d/'binding.private.json')
    with SessionLocal() as db:
        sol=db.get(Solution,m['solution_id']);u=db.get(User,m['user_id']);row=s.conversation(sol,db,u)
        return dict(saved=s.content(sol),conversation=s.view(sol,row,db,u),submissions=db.query(ExecutionSubmission).count())
def prepare_case(d):
    app=application();case=read(d/'case.private.json')
    from app.db import SessionLocal
    from app.models.solution import Solution
    from app.models.service import Service
    from app.models.user import User
    from app.services import solution_assistant as s
    from app.services.design_ai_provider import SAVED_SOLUTION_SYSTEM,redact_context
    from app.services.provider_evidence import response_format,digest as audit_digest
    from app.schemas.solution_assistant import SavedSolutionResponse,EditBase
    from app.schemas.design_ai import AssistantTurn,SolutionEdit
    from app.services.scoped_ai_acceptance import binding
    from app.core.config import settings
    # No credentials are loaded during preparation. This is labelled fixture
    # setup, not a fabricated authenticated/model conversation. Live login uses
    # the normal route only after separate approval and a durable reservation.
    source_id=read(d.parent/'source-binding.private.json')['solution_id']
    with SessionLocal() as db:
        source=db.get(Solution,source_id);uid=source.created_by_user_id
        user=db.get(User,uid)
        assert user and user.status=='active' and user.role=='solution_designer'
    # Reuse only an existing approved fixture and its current owned catalogue.
    examples=read(d.parent/'source-review.private.json')['steps'];gen=examples[0];drawing=examples[1]
    with SessionLocal() as db:
        user=db.get(User,uid);gs=db.get(Service,gen['service_id']);ds=db.get(Service,drawing['service_id'])
        assert gs.name.startswith('DEVELOPMENT SOFTWARE FIXTURE') and ds.name.endswith('Drawing A')
        contract=s.active_contract(gs,db);props=contract.definition['execution_parameters']['properties']
        assert props['how_many']['type']=='integer' and props['how_many']['minimum']==1 and props['how_many']['maximum']==4
        assert all(props[k]['type']=='boolean' for k in ('allow_hx','allow_bypass'))
        def node(identifier,service,label,params=None,x=100,y=100):
            ct=s.active_contract(service,db)
            data=dict(node_kind='service',label=label,service=s.service_to_builder_data(service),operation_contract=dict(contract_id=ct.id,contract_version=ct.contract_version))
            if params is not None:data['configuration']=dict(contract_id=ct.id,contract_version=ct.contract_version,parameters=params)
            return dict(id=identifier,type='default',position=dict(x=x,y=y),data=data)
        settings_values=dict(how_many=case['initial_maximum'],allow_hx=True,allow_bypass=True)
        nodes=[node('generator-north',gs,'Generator North',settings_values),node('drawing-a',ds,'Drawing A',x=400)]
        edges=[dict(id='north-drawing',source='generator-north',target='drawing-a',data=dict(connection_kind='service_connection',binding=dict(source_slot='networks',target_slot='networks')))]
        if case['instances']==2:nodes.append(node('generator-south',gs,'Generator South',dict(settings_values),y=300))
    from app.services.workflow_boundaries import complete
    complete(nodes,edges)
    if case.get('conversation_of'):
        sid=read(state_directory(d)/'binding.private.json')['solution_id']
    else:
        sid=str(uuid4())
        with SessionLocal() as db:
            db.add(Solution(id=sid,name='FIXTURE '+case['id'],description='Frozen setting-interpretation software fixture; no execution.',nodes=nodes,edges=edges,
                created_by_user_id=uid,design_metadata=dict(run_input=dict(fixture_only=True,selected='UNEXECUTED-SETTING-FIXTURE'),fixture_case=case['id'])))
            db.commit()
    write(d/'binding.private.json',dict(solution_id=sid,user_id=uid))
    with SessionLocal() as db:
        sol=db.get(Solution,sid);user=db.get(User,uid);row=s.conversation(sol,db,user,create=True)
        if case['base']=='pending' and not case.get('conversation_of'):
            ref=s.target_ref(sol,'generator-north')
            # Explicit initial pending fixture: not an interpretation attempt.
            turn=AssistantTurn(message='FIXTURE pending review, not a model response',template_key=None,expected_revision=None,edits=[],solution_edits=[SolutionEdit(kind='rename',value='FIXTURE earlier pending review '+case['id']),SolutionEdit(kind='set_node_label',node_id=ref,value='Generator North')])
            s.propose(sol,row,'FIXTURE: prior pending design',turn,db,user,outcome='proposal',base=EditBase.model_validate(s.edit_base(sol,row)))
        if case.get('clarification_fixture'):raise RuntimeError('Fabricated prior clarification is forbidden')
        ctx=redact_context(s.context(sol,row,case['message'],db,user))
        projection=ctx['pending_candidate'] if case['base']=='pending' else ctx['saved_design']
        step=next((x for x in projection['steps'] if x['label']==case['target']),None)
        base=deepcopy(ctx['edit_bases'][case['base']])
        if case.get('conversation_of'):base['conversation_revision']+=1
        current=s.materialize(sol,row.state['pending'],db,user) if row.state.get('pending') else s.content(sol)
        expected=current
        if case['expected'] in {'edit','no_change'}:
            expected,_=s.candidate(type('Fixture',(),current)(),[SolutionEdit(kind='set_node_parameters',node_id=step['node_id'],value=json.dumps(case['values']))],{},db,user)
        serialized=json.dumps(ctx,ensure_ascii=False,allow_nan=False)
        bound=len(serialized.encode())+len(SAVED_SOLUTION_SYSTEM.encode())+len(json.dumps(response_format(SavedSolutionResponse)).encode())+8192
        if len(serialized)>48000 or bound>64000:raise RuntimeError('Actual context exceeds frozen provider limits; no dispatch')
        frozen=dict(target_ref=step['target_ref'] if step else None,edit_base=base,saved_sha256=s.digest(s.content(sol)),expected_candidate_sha256=s.digest(expected),
            context_sha256=None if case.get('conversation_of') else audit_digest(ctx),input_bound=64000 if case.get('conversation_of') else bound,prompt_sha256=hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest(),wire_schema_sha256=audit_digest(response_format(SavedSolutionResponse)['schema']),approved_binding=binding(settings,uid,sid))
        frozen['conversation_of']=case.get('conversation_of')
        frozen['select_target']=case.get('select_target')
        frozen['eligible_targets']=[dict(label=x['label'],target_ref=x['target_ref']) for x in s.setting_targets(sol,row,db,user)['choices']]
        write(d/'frozen.private.json',frozen);write(d/'context.private.json',ctx)
    write(d/'before.private.json',snapshot(d))
    # Configuration with an absent new ledger/key cannot dispatch. No chat call.
    from app.services.design_ai_provider import configured
    assert not configured() and not settings.openai_api_key and not (d/'acceptance.private.sqlite').exists()
def prepare(d,source):
    if d.exists():raise RuntimeError('Use a fresh ignored directory; never overwrite a scope')
    if subprocess.run(['git','check-ignore','--quiet',str(d)],cwd=ROOT).returncode:raise RuntimeError('Operator directory must be ignored')
    profile=read(source/'profile.private.json');serving=read(source/'serving.private.json')
    if not profile.get('offline') or not serving.get('offline'):raise RuntimeError('Only the retained verified offline fixture database is eligible')
    d.mkdir(parents=True)
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip();subprocess.run(['icacls',str(d),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    source_hash=sha(source/'portal.sqlite')
    source_review=read(source/'pending-two-final.private.json');review=source_review['conversation']['pending']['candidate'];write(d/'source-review.private.json',review)
    write(d/'source-binding.private.json',dict(solution_id=source_review['conversation']['solution_id']))
    spec=read(SPEC);summaries=[]
    for case in spec['cases']:
        cd=d/case['id'];cd.mkdir();shutil.copyfile(source/'credentials.private.json',cd/'credentials.private.json');write(cd/'case.private.json',case)
        if not case.get('conversation_of'):
            with sqlite3.connect((source/'portal.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(cd/'portal.sqlite') as dest:src.backup(dest)
        child(cd,'prepare');f=read(cd/'frozen.private.json');summaries.append(dict(case=case['id'],fixture_sha256=digest(read(cd/'before.private.json')),**f))
    if sha(source/'portal.sqlite')!=source_hash:raise RuntimeError('Retained offline database changed during preparation')
    manifest=dict(version=1,status='PREPARED_NOT_AUTHORISED',spec_sha256=sha(SPEC),source_files=source_files(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),cases=summaries,
        dependencies=dependencies(),
        retained_source_database_sha256=source_hash,credentials_sha256=sha(source/'credentials.private.json'))
    write(d/'manifest.private.json',manifest)
    print(json.dumps(dict(prepared_cases=spec['max_requests'],manifest_sha256=sha(d/'manifest.private.json'),max_requests=spec['max_requests'],maximum_usd=spec['limit_nano_usd']/1e9,metered_requests=0,ledger_files_created=0)))
def verify(d):
    m=read(d/'manifest.private.json')
    if m['source_files']!=source_files() or m['spec_sha256']!=sha(SPEC):raise RuntimeError('Frozen source/prompt/schema/harness/set changed; do not run')
    if m['dependencies']!=dependencies():raise RuntimeError('Frozen dependencies changed')
    cases={c['id']:c for c in read(SPEC)['cases']}
    for record in m['cases']:
        cd=d/record['case'];f=read(cd/'frozen.private.json')
        if read(cd/'case.private.json')!=cases[record['case']]:raise RuntimeError('Frozen request or expected case changed')
        if f!={k:v for k,v in record.items() if k not in {'case','fixture_sha256'}}:raise RuntimeError('Frozen case changed')
        if sha(cd/'credentials.private.json')!=m['credentials_sha256'] or digest(read(cd/'before.private.json'))!=record['fixture_sha256']:raise RuntimeError('Fixture evidence changed')
    return m
def approval(d,p):
    m=verify(d);a=read(p);spec=read(SPEC);now=datetime.now(timezone.utc)
    expiry=datetime.fromisoformat(a['expires_at'])
    if (a.get('approved') is not True or a.get('manifest_sha256')!=sha(d/'manifest.private.json') or a.get('max_requests')!=spec['max_requests']
        or a.get('limit_nano_usd')!=spec['limit_nano_usd'] or len(a.get('authorization_ref','').strip())<20
        or expiry.tzinfo is None or not now<expiry<=now+timedelta(hours=24)):
        raise RuntimeError('Separate concrete current approval required; no key loaded or ledger created')
    return a
def activate(d,p,key_source,key_project):
    a=approval(d,p)
    # Validate path/ignore boundary now, but do not read any key until an attempt.
    if not key_source.resolve().is_relative_to(key_project.resolve()) or subprocess.run(['git','check-ignore','--quiet',str(key_source.resolve())],cwd=key_project).returncode:raise RuntimeError('Only project-local ignored key configuration is allowed')
    with (d/'evaluation.private.sqlite').open('xb'):pass
    with sqlite3.connect(d/'evaluation.private.sqlite') as db:
        db.executescript('CREATE TABLE policy(value TEXT NOT NULL, closed INTEGER NOT NULL); CREATE TABLE attempts(id TEXT PRIMARY KEY, reserved INTEGER NOT NULL, status TEXT NOT NULL, result TEXT, review TEXT);')
        db.execute('INSERT INTO policy VALUES (?,0)',(canonical(dict(approval=a,manifest_sha256=sha(d/'manifest.private.json'),key_source=str(key_source.resolve()),key_project=str(key_project.resolve()))),))
    print('Activated one new six-attempt evaluation after separate approval; no dispatch yet.')
def attempt(d):
    verify(d);spec=read(SPEC)
    with sqlite3.connect((d/'evaluation.private.sqlite').as_uri()+'?mode=rw',uri=True) as db:
        db.execute('BEGIN IMMEDIATE');raw,closed=db.execute('SELECT value,closed FROM policy').fetchone();policy=json.loads(raw)
        a=policy['approval']
        if closed or a['manifest_sha256']!=sha(d/'manifest.private.json') or datetime.fromisoformat(a['expires_at'])<=datetime.now(timezone.utc):raise RuntimeError('Evaluation closed, expired or changed')
        rows=db.execute('SELECT id,reserved,status,review FROM attempts ORDER BY id').fetchall()
        if any(x[2]!='PASS' for x in rows) or len(rows)>=spec['max_requests'] or sum(x[1] for x in rows)+spec['reservation_nano_usd']>a['limit_nano_usd']:raise RuntimeError('Prior attempt needs review, failed, or cap exhausted; no dispatch')
        case=spec['cases'][len(rows)];cd=d/case['id']
        db.execute('INSERT INTO attempts VALUES (?,?,?,NULL,NULL)',(case['id'],spec['reservation_nano_usd'],'STARTED'));db.commit()
    write(cd/'authorised.private.json',dict(**policy,case=case['id']))
    try:child(cd,'live');result=read(cd/'result.private.json')
    except Exception:
        result=dict(status='FAIL_STOP',category='worker_or_transport',reasons=['Inspect private diagnostics; attempt reserved, never repeat'])
    with sqlite3.connect(d/'evaluation.private.sqlite') as db:
        db.execute('UPDATE attempts SET status=?,result=? WHERE id=?',(result['status'],canonical(result),case['id']))
        if result['status']=='FAIL_STOP':db.execute('UPDATE policy SET closed=1')
    print(json.dumps(dict(case=case['id'],**result,accounting=accounting(d))))
def live_case(d):
    auth=read(d/'authorised.private.json');parent=d.parent;verify(parent)
    if datetime.fromisoformat(auth['approval']['expires_at'])<=datetime.now(timezone.utc):raise RuntimeError('Approval expired')
    with sqlite3.connect((parent/'evaluation.private.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        raw,closed=db.execute('SELECT value,closed FROM policy').fetchone()
        permit=db.execute('SELECT reserved,status FROM attempts WHERE id=?',(d.name,)).fetchone()
    if closed or json.loads(raw)!={k:v for k,v in auth.items() if k!='case'} or permit!=(read(SPEC)['reservation_nano_usd'],'STARTED'):
        raise RuntimeError('Missing exclusive current parent reservation; no dispatch')
    app=application();c,uid=client(app,d);before=snapshot(d);f=read(d/'frozen.private.json');case=read(d/'case.private.json')
    if uid!=read(d/'binding.private.json')['user_id']:raise RuntimeError('Signed-in owner differs from frozen account')
    if case.get('conversation_of'):
        prior=parent/case['conversation_of']
        if before!=read(prior/'after.private.json'):raise RuntimeError('Actual preceding conversation changed; no dispatch')
        initial=read(prior/'before.private.json')
        if before['saved']!=initial['saved'] or before['conversation']['pending']!=initial['conversation']['pending']:
            raise RuntimeError('Preceding ambiguous request changed existing work; no dispatch')
        write(d/'actual-before.private.json',before)
    elif before!=read(d/'before.private.json'):raise RuntimeError('Initial case state changed; no dispatch')
    from app.core.config import settings
    from app.services import solution_assistant as s
    from app.services.scoped_ai_acceptance import initialize,Budget,RESERVATION
    from app.services.design_ai_provider import get_provider,OpenAIProvider,redact_context
    from app.db import SessionLocal
    from app.models.solution import Solution
    from app.models.user import User
    m=read(d/'binding.private.json')
    with SessionLocal() as db:
        sol=db.get(Solution,m['solution_id']);u=db.get(User,uid);row=s.conversation(sol,db,u)
        ctx=redact_context(s.context(sol,row,case['message'],db,u))
        choice=None
        if case.get('select_target'):
            targets=before['conversation']['setting_targets']
            matches=[x for x in targets['choices'] if x['label']==case['select_target']]
            if len(matches)!=1:raise RuntimeError('One current displayed South choice is required; no guessing')
            selected=matches[0];choice={k:v for k,v in targets.items() if k!='choices'} | {'target_ref':selected['target_ref']}
            from app.schemas.solution_assistant import SettingTargetChoice
            s.check_target_choice(sol,row,SettingTargetChoice.model_validate(choice),db,u)
            if choice['base']!=f['edit_base'] or choice['target_ref']!=f['target_ref']:raise RuntimeError('Current choice differs from frozen expected South/base')
            ctx['user_selected_target']={'target_ref':selected['target_ref'],'label':selected['label'],'source':'authenticated_request_choice','edit_base':choice['base'],
                'instruction':'Only this explicitly selected instance may receive setting changes; other instances remain unchanged.'}
    from app.services.provider_evidence import digest as audit_digest
    if not case.get('conversation_of') and audit_digest(ctx)!=f['context_sha256']:raise RuntimeError('Exact frozen model input changed; no dispatch')
    from app.services.design_ai_provider import SAVED_SOLUTION_SYSTEM
    from app.services.provider_evidence import response_format
    from app.schemas.solution_assistant import SavedSolutionResponse
    serialized=json.dumps(redact_context(ctx),ensure_ascii=False,allow_nan=False)
    bound=len(serialized.encode())+len(SAVED_SOLUTION_SYSTEM.encode())+len(json.dumps(response_format(SavedSolutionResponse)).encode())+8192
    if len(serialized)>48000 or bound>read(SPEC)['max_input_tokens']:raise RuntimeError('Actual continuation exceeds frozen input bound before key loading; no dispatch')
    write(d/'dispatch-context.private.json',dict(context=ctx,context_sha256=audit_digest(ctx),target_choice=choice,input_bound=bound,derived_from_actual=case.get('conversation_of')))

    initialize(d/'acceptance.private.sqlite',approved_binding=f['approved_binding'],authorization_ref=auth['approval']['authorization_ref'],expires_at=auth['approval']['expires_at'],max_requests=1,limit_nano=RESERVATION)
    helper=module('setting_eval_key_reader',ROOT/'deploy/genuine_acceptance/workspace.py')
    settings.openai_api_key=helper.key_from_project(Path(auth['key_source']),Path(auth['key_project']))
    assert isinstance(get_provider(),OpenAIProvider) and not app.dependency_overrides
    audit=logging.getLogger('design_ai.provider.audit');audit.setLevel(logging.DEBUG);audit.propagate=False
    handler=logging.FileHandler(d/'provider-audit.private.jsonl',encoding='utf-8');audit.addHandler(handler)
    try:
        view=before['conversation']
        r=c.post('/design-ai/solutions/'+m['solution_id']+'/chat',json=dict(message=case['message'],expected_updated_at=view['expected_updated_at'],conversation_revision=view['conversation_revision'],**({'target_choice':choice} if choice else {})))
        after=snapshot(d);write(d/'after.private.json',after)
        payload=r.json();detail=payload.get('detail',{}) if isinstance(payload,dict) else {};pending=after['conversation']['pending']
        observation=dict(http_status=r.status_code,detail_stage=detail.get('stage') if isinstance(detail,dict) else None,
            saved_sha256=s.digest(after['saved']),submissions=after['submissions'],pending_unchanged=pending==before['conversation']['pending'],
            candidate_sha256=pending['candidate']['candidate_sha256'] if pending else s.digest(after['saved']),
            summary=(after['conversation']['messages'][-1].get('change_summary') if after['conversation']['messages'] else None),
            target_question=after['conversation'].get('target_question'),clarification=after['conversation'].get('clarification'),
            application_message=after['conversation']['messages'][-1] if after['conversation']['messages'] else None)
        handler.flush();audits=[json.loads(line) for line in (d/'provider-audit.private.jsonl').read_text(encoding='utf-8').splitlines()]
        if len(audits)!=1:raise RuntimeError('Expected exactly one recorded real-provider attempt')
        grader=module('setting_eval_grader',HERE/'grade.py');result=grader.grade(case,f,observation,audits[0]);write(d/'observation.private.json',observation);write(d/'result.private.json',result)
    finally:
        settings.openai_api_key='';Budget(d/'acceptance.private.sqlite').close();audit.removeHandler(handler);handler.close();c.close()
def check_case(d):
    # Unpaid preflight loads no credentials: assert provider disabled and the
    # real protected route rejects an unauthenticated request without dispatch.
    app=application();before=snapshot(d)
    from app.services.design_ai_provider import get_provider,OpenAIProvider,configured
    from app.core.config import settings
    from fastapi.testclient import TestClient
    assert isinstance(get_provider(),OpenAIProvider) and not app.dependency_overrides and not configured() and not settings.openai_api_key
    with TestClient(app,raise_server_exceptions=False) as c:
        r=c.get('/design-ai/solutions/'+before['conversation']['solution_id'])
        assert r.status_code==401
    assert snapshot(d)==before and not (d/'acceptance.private.sqlite').exists() and not (d/'provider-audit.private.jsonl').exists()
    write(d/'disabled-route-check.private.json',dict(status='PASS_NO_CREDENTIALS_UNAUTHENTICATED_PREFLIGHT',provider_class=type(get_provider()).__name__,dependency_overrides=0,http_status=401,ledger_files=0,key_loaded=False,saved_and_pending_unchanged=True))

def check_routes(d):
    verify(d)
    for case in read(SPEC)['cases']:child(d/case['id'],'check')
    print('Six unpaid no-credential preflights: real provider disabled; protected route 401; no key, ledger or model request. Authenticated genuine requests remain unattempted.')
def review(d,case,verdict,reason):
    verify(d)
    if len(reason.strip())<20:raise RuntimeError('Record concrete semantic review evidence')
    with sqlite3.connect((d/'evaluation.private.sqlite').as_uri()+'?mode=rw',uri=True) as db:
        db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT status,result FROM attempts WHERE id=?',(case,)).fetchone()
        if not row or row[0]!='REVIEW_REQUIRED':raise RuntimeError('Only a machine-checked current attempt can receive semantic review; failures cannot be overridden')
        db.execute('UPDATE attempts SET status=?,review=? WHERE id=?',('PASS' if verdict=='pass' else 'FAIL_STOP',reason,case))
        if verdict!='pass':db.execute('UPDATE policy SET closed=1')
        elif db.execute("SELECT COUNT(*) FROM attempts WHERE status='PASS'").fetchone()[0]==read(SPEC)['max_requests']:db.execute('UPDATE policy SET closed=1')
    print('Semantic review recorded; no model request or Apply dispatched.')
def accounting(d):
    spec=read(SPEC);path=d/'evaluation.private.sqlite';rows=[];closed=True;expired=False
    if path.exists():
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            raw,closed=db.execute('SELECT value,closed FROM policy').fetchone()
            expired=datetime.fromisoformat(json.loads(raw)['approval']['expires_at'])<=datetime.now(timezone.utc)
            rows=db.execute('SELECT id,reserved,status FROM attempts ORDER BY id').fetchall()
    settled=uncertain=inputs=outputs=0;details=[]
    for identifier,reserved,status in rows:
        ledger=d/identifier/'acceptance.private.sqlite';held=reserved;usage=None;state='no_provider_ledger_observed'
        if ledger.exists():
            with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as db:
                requests=db.execute('SELECT reserved,held,usage,state FROM acceptance_requests').fetchall()
            if len(requests)>1:raise RuntimeError('More than one provider request for a frozen attempt')
            if requests:
                _,held,raw_usage,state=requests[0];usage=json.loads(raw_usage) if raw_usage else None
        if usage:
            settled+=held;inputs+=usage['input_tokens'];outputs+=usage['output_tokens']
        else:uncertain+=reserved
        details.append(dict(case=identifier,status=status,provider_state=state,usage=usage,estimated_usd=held/1e9 if usage else None,uncertain_reserved_usd=0 if usage else reserved/1e9))
    available=path.exists() and not closed and not expired
    return dict(parent_created=path.exists(),closed=bool(closed),expired=expired,attempts=len(rows),usage=dict(input_tokens=inputs,output_tokens=outputs),
        cumulative_conservative_estimated_usd=settled/1e9,uncertain_reserved_usd=uncertain/1e9,lifetime_reserved_usd=sum(r[1] for r in rows)/1e9,
        remaining_authorised_calls=spec['max_requests']-len(rows) if available else 0,
        remaining_authorised_reservations_usd=(spec['limit_nano_usd']-sum(r[1] for r in rows))/1e9 if available else 0,
        next_dispatch_permitted=bool(available and not uncertain and len(rows)<spec['max_requests'] and all(r[2]=='PASS' for r in rows)),details=details,
        account_balance='NOT_OBSERVED; this is application accounting only')


def report(d):
    verify(d);spec=read(SPEC);dbpath=d/'evaluation.private.sqlite';rows=[]
    if dbpath.exists():
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:rows=db.execute('SELECT id,reserved,status,result,review FROM attempts ORDER BY id').fetchall()
    attempted={r[0]:dict(status=r[2],reserved_nano=r[1],result=json.loads(r[3]) if r[3] else None,review=r[4]) for r in rows}
    print(json.dumps(dict(status='PREPARED_NOT_AUTHORISED' if not dbpath.exists() else 'EVALUATION_RECORD',manifest_sha256=sha(d/'manifest.private.json'),
        maximum_calls=spec['max_requests'],maximum_usd=spec['limit_nano_usd']/1e9,accounting=accounting(d),cases=[dict(id=c['id'],**attempted.get(c['id'],dict(status='NOT_ATTEMPTED'))) for c in spec['cases']]),indent=2))

def serve_case(d):
    app=application()
    from fastapi.responses import JSONResponse
    @app.middleware('http')
    async def no_more_chat(request,call_next):
        if request.method not in {'GET','HEAD'} and request.url.path.startswith('/design-ai/') and request.url.path.endswith('/chat'):
            return JSONResponse(status_code=409,content={'detail':'Evaluation review only. No additional model request is authorised.'})
        return await call_next(request)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=28272,log_level='warning',access_log=False)
def start_review(d,case,dependencies):
    verify(d);cd=d/case
    with sqlite3.connect((d/'evaluation.private.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT status FROM attempts WHERE id=?',(case,)).fetchone()
    definition=read(cd/'case.private.json')
    if not row or row[0]!='PASS' or not definition.get('conversation_of'):raise RuntimeError('Only the successful reviewed genuine A/B continuation can open this browser proof')
    with sqlite3.connect((d/'evaluation.private.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        prior=db.execute('SELECT status FROM attempts WHERE id=?',(definition['conversation_of'],)).fetchone()
    if prior!=('PASS',):raise RuntimeError('Actual ambiguous request must pass review before browser proof')
    for port in (23138,28272):
        with socket.socket() as sock:sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);sock.bind(('127.0.0.1',port))
    helper=module('setting_review_frontend',ROOT/'deploy/parameter_onboarding/review_workspace.py')
    generation=ROOT.parent/'scui'/uuid4().hex[:8];generation.mkdir(parents=True)
    env=environment(cd);env.update(INTERNAL_API_URL='http://127.0.0.1:28272',NEXT_PUBLIC_ENVIRONMENT_LABEL='GENUINE SETTING EVALUATION — REVIEW ONLY / NO RUN',NEXT_TELEMETRY_DISABLED='1')
    children=[]
    try:
        api=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_serve','--directory',str(cd)],cwd=cd,env=env,stdout=(cd/'review-api.private.log').open('a'),stderr=subprocess.STDOUT);children.append(api)
        helper.wait_http('http://127.0.0.1:28272/health',api)
        web=helper.prepare_frontend(generation,dict(dependencies_directory=str(dependencies.resolve())))
        next_bin=dependencies.resolve().parent/'apps/web/node_modules/next/dist/bin/next'
        with (cd/'review-build.private.log').open('x') as log:result=subprocess.run(['node',str(next_bin),'build'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Build failed; inspect private log')
        child=subprocess.Popen(['node',str(next_bin),'start','-H','127.0.0.1','-p','23138'],cwd=web,env=env,stdout=(cd/'review-web.private.log').open('a'),stderr=subprocess.STDOUT);children.append(child)
        helper.wait_http('http://127.0.0.1:23138/login',child)
        write(cd/'review-serving.private.json',dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),case=case,model_calls_enabled=False))
        print('READY: http://127.0.0.1:23138/login — genuine reviewed proposal; model calls and Run disabled',flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=8)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','check','check-routes','activate','attempt','review','report','start-review','_prepare','_live','_check','_serve']);p.add_argument('--directory',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--approval',type=Path);p.add_argument('--key-source',type=Path);p.add_argument('--key-project',type=Path);p.add_argument('--case');p.add_argument('--verdict',choices=['pass','fail']);p.add_argument('--reason');p.add_argument('--dependencies',type=Path);a=p.parse_args();d=a.directory.resolve()
    if a.action=='prepare':prepare(d,a.source.resolve())
    elif a.action=='check':verify(d);print('Frozen source, dependencies, cases and fixtures match; no key loaded or model called.')
    elif a.action=='activate':activate(d,a.approval,a.key_source,a.key_project)
    elif a.action=='attempt':attempt(d)
    elif a.action=='review':review(d,a.case,a.verdict,a.reason or '')
    elif a.action=='report':report(d)
    elif a.action=='check-routes':check_routes(d)
    elif a.action=='start-review':start_review(d,a.case,a.dependencies)
    elif a.action=='_prepare':prepare_case(d)
    elif a.action=='_live':live_case(d)
    elif a.action=='_check':check_case(d)
    elif a.action=='_serve':serve_case(d)
