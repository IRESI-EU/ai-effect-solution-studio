"""Focused OFFLINE two-instance walkthrough. No model, ledger, worker or Run.

Copies the retained case-5 database read-only into a fresh private directory.
The supplied failed action is replayed with only current identity/base binding;
the second response is an explicitly scripted South action after the user chooses.
Production never imports this opt-in fixture.
"""
import argparse
from copy import deepcopy
import json, os
from pathlib import Path
import shutil, socket, sqlite3, subprocess, sys, time
from uuid import uuid4
from workspace import module, ROOT


def prepare(directory, case, offline, *, title='OFFLINE target choice — earlier pending title'):
    if directory.exists():raise RuntimeError('A fresh directory is required; never replace a retained fixture')
    directory.mkdir(parents=True)
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    with sqlite3.connect((case/'portal.sqlite').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(directory/'portal.sqlite') as dest:source.backup(dest)
    binding=json.loads((case/'binding.private.json').read_text(encoding='utf-8'))
    before=json.loads((case/'before.private.json').read_text(encoding='utf-8'))
    assert before['conversation']['conversation_revision']==0 and before['conversation']['pending'] is None
    with sqlite3.connect(directory/'portal.sqlite') as db:
        row=db.execute('select id,state from design_ai_drafts where owner_id=?',(binding['user_id'],)).fetchall()
        matching=[(i,json.loads(s)) for i,s in row if json.loads(s).get('solution_id')==binding['solution_id']]
        assert len(matching)==1
        identifier,state=matching[0]
        db.execute('update design_ai_drafts set state=?,revision=0 where id=?',(json.dumps(dict(kind=state['kind'],solution_id=binding['solution_id'],messages=[],pending=None)),identifier))
    shutil.copyfile(case/'credentials.private.json',directory/'credentials.private.json')
    shutil.copyfile(case/'binding.private.json',directory/'binding.private.json')
    p=json.loads((offline/'profile.private.json').read_text(encoding='utf-8'))
    profile=dict(source=p['source'],api_url='http://127.0.0.1:28271',web_url='http://127.0.0.1:23137',cookie='aie_choice_'+uuid4().hex,dependencies_directory=p['dependencies_directory'],offline=True)
    (directory/'profile.private.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
    os.environ.update(environment(directory));sys.path.insert(0,str(ROOT/'apps/api'))
    sqlite_types()
    from app.db import SessionLocal
    from app.models.solution import Solution
    from app.models.user import User
    from app.schemas.solution_assistant import SavedSolutionResponse, as_assistant_turn
    from app.services import solution_assistant as service
    with SessionLocal() as db:
        solution=db.get(Solution,binding['solution_id']);user=db.get(User,binding['user_id']);row=service.conversation(solution,db,user)
        turn=SavedSolutionResponse.model_validate(dict(outcome='proposal',message='OFFLINE setup only: earlier title review, not applied.',clarification=None,assumptions=[],solution_edits=[dict(kind='rename',value=title)],edit_base=service.edit_base(solution,row)))
        service.propose(solution,row,'OFFLINE fixture setup: retain this earlier pending title.',as_assistant_turn(turn),db,user,base=turn.edit_base)
        initial=dict(saved=service.content(solution),conversation=service.view(solution,row,db,user))
    (directory/'initial.private.json').write_text(json.dumps(initial,indent=2),encoding='utf-8')
    print('Prepared fresh OFFLINE copy with earlier pending review; retained source untouched',flush=True)


def environment(directory):
    helper=module('existing_setting_walkthrough',ROOT/'deploy/setting_edit_walkthrough/workspace.py')
    env=helper.environment(directory)
    credentials=json.loads((directory/'credentials.private.json').read_text(encoding='utf-8'))
    profile=json.loads((directory/'profile.private.json').read_text(encoding='utf-8'))
    env.update(BOOTSTRAP_ADMIN_EMAIL=credentials['administrator']['email'],BOOTSTRAP_ADMIN_PASSWORD=credentials['administrator']['password'],SERVICE_API_KEY='',NEXT_PUBLIC_ENVIRONMENT_LABEL=profile.get('environment_label','OFFLINE TARGET CHOICE FIXTURE — NO MODEL / NO RUN'))
    return env


def sqlite_types():
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB,'sqlite')
    def compile_json(_type,compiler,**kwargs):return 'JSON'


class OfflineChoice:
    name='EXPLICIT OFFLINE TARGET CHOICE RESPONSE REPLAY';mode='test'
    def __init__(self,directory):
        self.directory=directory
        report=json.loads((ROOT/'docs/verification/setting-interpretation-executed-20261120.json').read_text(encoding='utf-8'))
        self.case=next(c for c in report['cases'] if c['id']=='05-ambiguous')
    async def respond(self,c):
        from app.schemas.solution_assistant import SavedSolutionResponse
        if c['request']!=self.case['request']:raise ValueError('This offline walkthrough supplies only the documented case-5 request; no model is connected')
        projection=c['pending_candidate'] or c['saved_design'];selected=c.get('user_selected_target')
        targets=[s for s in projection['steps'] if 'how_many' in s['effective_settings']]
        if len(targets)!=2:raise ValueError('Expected the isolated two-instance fixture')
        target=next(s for s in targets if s['target_ref']==selected['target_ref']) if selected else next(s for s in targets if s['label']=='Generator North')
        response=deepcopy(self.case['provider_audit']['validated_response'])
        response['edit_base']=c['edit_bases']['pending' if c['pending_candidate'] else 'saved']
        response['parameter_action']['target_ref']=target['target_ref']
        with (self.directory/'responses.private.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps(dict(offline=True,selected=selected,response=response))+'\n')
        return SavedSolutionResponse.model_validate(response)


def serve(directory):
    sqlite_types()
    from app.main import app
    from app.services.design_ai_provider import get_provider
    from fastapi.responses import JSONResponse
    provider=OfflineChoice(directory);app.dependency_overrides[get_provider]=lambda:provider
    @app.middleware('http')
    async def no_execution(request,call_next):
        if request.method not in {'GET','HEAD'} and (request.url.path.startswith(('/deployments','/workflows/submit')) or request.url.path.endswith('/runtime/verify')):
            return JSONResponse(status_code=409,content={'detail':'OFFLINE target choice walkthrough: execution disabled.'})
        return await call_next(request)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=28271,log_level='warning',access_log=False)


def start(directory, *, script=None, build_parent='ctui'):
    profile=json.loads((directory/'profile.private.json').read_text(encoding='utf-8'));env=environment(directory)
    from urllib.parse import urlsplit
    for port in (urlsplit(profile['web_url']).port,urlsplit(profile['api_url']).port):
        with socket.socket() as sock:sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);sock.bind(('127.0.0.1',port))
    helper=module('choice_frontend_helper',ROOT/'deploy/parameter_onboarding/review_workspace.py')
    # Keep the build cwd below the Windows path limit.
    generation=ROOT.parent/build_parent/uuid4().hex[:8];generation.mkdir(parents=True)
    shutil.copytree(ROOT/'apps/api/app',generation/'api/app',ignore=shutil.ignore_patterns('__pycache__'))
    children=[]
    try:
        api_env=dict(env);api_env['PYTHONPATH']=str(generation/'api')
        api=subprocess.Popen([sys.executable,str(Path(script or __file__).resolve()),'_serve','--directory',str(directory)],cwd=directory,env=api_env,stdout=(directory/'api.private.log').open('a'),stderr=subprocess.STDOUT);children.append(api)
        helper.wait_http(profile['api_url']+'/health',api)
        web=helper.prepare_frontend(generation,profile)
        next_bin=Path(profile['dependencies_directory']).parent/'apps/web/node_modules/next/dist/bin/next'
        with (directory/'build.private.log').open('w') as log:result=subprocess.run(['node',str(next_bin),'build'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Build failed; inspect ignored local diagnostics')
        child=subprocess.Popen(['node',str(next_bin),'start','-H','127.0.0.1','-p',str(urlsplit(profile['web_url']).port)],cwd=web,env=env,stdout=(directory/'web.private.log').open('a'),stderr=subprocess.STDOUT);children.append(child)
        helper.wait_http(profile['web_url']+'/login',child)
        (directory/'serving.private.json').write_text(json.dumps(dict(generation=str(generation),commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),offline=True),indent=2),encoding='utf-8')
        print('READY: '+profile['web_url']+'/login — OFFLINE scripted responses; no model or Run',flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=8)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','start','_serve']);p.add_argument('--directory',type=Path,required=True);p.add_argument('--case',type=Path);p.add_argument('--offline',type=Path);a=p.parse_args();d=a.directory.resolve()
    if a.action=='prepare':prepare(d,a.case.resolve(),a.offline.resolve())
    elif a.action=='start':start(d)
    else:os.environ.update(environment(d));serve(d)
