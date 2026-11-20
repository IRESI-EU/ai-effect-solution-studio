"""Small OFFLINE API/web review harness. Copies an existing offline database read-only.

No Docker, workers, ML stack, paid key, budget ledger or runtime execution is started.
The original offline workspace remains untouched. Authentication/ownership are normal.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value


def prepare(directory,source):
    if directory.exists():raise RuntimeError('Use a new directory; retained demonstrations must not be replaced')
    p=json.loads((source/'profile.private.json').read_text())
    serving=json.loads((source/'serving.private.json').read_text())
    if not p.get('offline_ui_fixture') or not serving.get('offline_double'):raise RuntimeError('Only a verified OFFLINE source workspace is eligible')
    directory.mkdir(parents=True)
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    with sqlite3.connect((source/'portal.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(directory/'portal.sqlite') as dest:src.backup(dest)
    shutil.copyfile(source/'credentials.private.json',directory/'credentials.private.json')
    profile={'source':str(source),'directory':str(directory),'api_url':'http://127.0.0.1:28269','web_url':'http://127.0.0.1:23135',
        'cookie':'aie_setting_'+uuid4().hex,'dependencies_directory':p['dependencies_directory'],'offline':True}
    (directory/'profile.private.json').write_text(json.dumps(profile,indent=2))
    print('Prepared isolated offline database copy; no model or execution enabled',flush=True)


def environment(directory):
    profile=json.loads((directory/'profile.private.json').read_text())
    helper=module('existing_offline_environment',ROOT/'deploy/genuine_acceptance/workspace.py')
    env=helper.environment(Path(profile['source']))
    env.update(DATABASE_URL='sqlite:///'+(directory/'portal.sqlite').as_posix(),SESSION_COOKIE_NAME=profile['cookie'],
        INTERNAL_API_URL=profile['api_url'],OPENAI_API_KEY='',DESIGN_AI_MODEL='',DESIGN_AI_SCOPED_ACCEPTANCE_FILE='',
        ORCHESTRATOR_BASE_URL='',ORCHESTRATOR_API_KEY='',ORCHESTRATOR_SERVICES_API_KEY='',
        ARTIFACT_BASE_PATH=str(directory/'outputs'),REDIS_URL='',
        NEXT_PUBLIC_ENVIRONMENT_LABEL='OFFLINE SETTING ACTION REPLAY — NO MODEL / NO RUN')
    for key in list(env):
        if key.startswith('DESIGN_AI_') and ('FILE' in key or 'ALLOWANCE' in key):env[key]=''
    return env


def serve(directory):
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB,'sqlite')
    def sqlite_jsonb(_type,compiler,**kwargs):return 'JSON'
    from app.main import app
    from app.services.design_ai_provider import get_provider
    from offline_provider import OfflineProvider
    from fastapi.responses import JSONResponse
    provider=OfflineProvider(directory);app.dependency_overrides[get_provider]=lambda:provider
    @app.middleware('http')
    async def no_execution(request,call_next):
        if request.method!='GET' and (request.url.path.startswith('/deployments') or request.url.path.startswith('/workflows/submit') or request.url.path.endswith('/runtime/verify')):
            return JSONResponse(status_code=409,content={'detail':'OFFLINE review harness: workflow execution is disabled.'})
        return await call_next(request)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=28269,log_level='warning',access_log=False)


def start(directory):
    p=json.loads((directory/'profile.private.json').read_text());env=environment(directory)
    for port in (23135,28269):
        with socket.socket() as sock:sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);sock.bind(('127.0.0.1',port))
    helper=module('existing_frontend_helper',ROOT/'deploy/parameter_onboarding/review_workspace.py')
    generation=directory/'builds'/uuid4().hex;generation.mkdir(parents=True)
    shutil.copytree(ROOT/'apps/api/app',generation/'api/app',ignore=shutil.ignore_patterns('__pycache__'))
    children=[]
    try:
        api_env=dict(env);api_env['PYTHONPATH']=str(generation/'api')
        api=subprocess.Popen([sys.executable,str(Path(__file__)),'_serve','--directory',str(directory)],cwd=directory,env=api_env,stdout=(directory/'api.private.log').open('a'),stderr=subprocess.STDOUT);children.append(api)
        helper.wait_http(p['api_url']+'/health',api)
        web=helper.prepare_frontend(generation,p)
        next_bin=Path(p['dependencies_directory']).parent/'apps/web/node_modules/next/dist/bin/next'
        with (directory/'build.private.log').open('w') as log:result=subprocess.run(['node',str(next_bin),'build'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Build failed; inspect ignored diagnostics')
        child=subprocess.Popen(['node',str(next_bin),'start','-H','127.0.0.1','-p','23135'],cwd=web,env=env,stdout=(directory/'web.private.log').open('a'),stderr=subprocess.STDOUT);children.append(child)
        helper.wait_http(p['web_url']+'/login',child)
        (directory/'serving.private.json').write_text(json.dumps({'generation':str(generation),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'offline':True},indent=2))
        print('READY: '+p['web_url']+'/login — EXPLICIT OFFLINE RESPONSES; no Run or model',flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','start','_serve'])
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--source',type=Path)
    args=parser.parse_args();directory=args.directory.resolve()
    if args.action=='prepare':prepare(directory,args.source.resolve())
    elif args.action=='start':start(directory)
    else:os.environ.update(environment(directory));serve(directory)
