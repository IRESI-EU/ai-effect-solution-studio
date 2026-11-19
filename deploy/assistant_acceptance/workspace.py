"""Fresh normal assistant/Danish software acceptance; no paid provider configuration."""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REDIS='sha256:8b81dd37ff027bec4e516d41acfbe9fe2460070dc6d4a4570a2ac5b9d59df065'
PORTS=(23127,28194,28195,28196,28197,28198,26381)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value


def profile(directory):
    value=json.loads((directory/'profile.private.json').read_text())
    if value['kind']!='offline-assistant-danish-v1' or value['directory']!=str(directory.resolve()):raise RuntimeError('Not this isolated acceptance workspace')
    return value


def free_ports(ports):
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);sock.bind(('127.0.0.1',port))


def prepare(directory,wp3,dependencies):
    if directory.exists():raise RuntimeError('Use a new directory; existing experiments are preserved')
    free_ports(PORTS);directory.mkdir(parents=True,mode=0o700)
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    value={'kind':'offline-assistant-danish-v1','directory':str(directory.resolve()),'project':'aie-assistant-'+uuid4().hex[:12],
        'cookie':'aie_assistant_'+uuid4().hex,'api_url':'http://127.0.0.1:28194','web_url':'http://127.0.0.1:23127',
        'wp3_url':'http://127.0.0.1:28195','control_key':secrets.token_urlsafe(48),'orchestrator_key':secrets.token_urlsafe(48),
        'redis_key':secrets.token_urlsafe(48),'dependencies_directory':str(dependencies/'node_modules')}
    (directory/'profile.private.json').write_text(json.dumps(value,indent=2))
    accounts={role:{'email':role+'@assistant-fixture.invalid','password':'Fixture-9-'+secrets.token_urlsafe(32)} for role in ('administrator','provider','designer','other_designer')}
    (directory/'credentials.private.json').write_text(json.dumps(accounts,indent=2))
    for name in ('contracts','outputs','service-contracts','browser-evidence'): (directory/name).mkdir()
    shutil.copytree(wp3/'orchestrator/src',directory/'wp3-source',ignore=shutil.ignore_patterns('__pycache__','logs'))
    shutil.copytree(wp3/'use-cases/denmark-node',directory/'node-source',ignore=shutil.ignore_patterns('__pycache__','node_modules','.git'))
    (directory/'fixture-input.json').write_text(json.dumps({'run_config':{'supplies':['310-D::CHP'],'loads':['716-D::Dumpload']}}))
    (directory/'redis.private.conf').write_text('bind 0.0.0.0\nappendonly yes\nrequirepass '+value['redis_key']+'\n')
    compose={'name':value['project'],'services':{'redis':{'image':REDIS,'pull_policy':'never',
        'command':['redis-server','/private/redis.conf'],'ports':['127.0.0.1:26381:6379'],
        'volumes':['redis:/data',{'type':'bind','source':str(directory/'redis.private.conf'),'target':'/private/redis.conf','read_only':True}]}},'volumes':{'redis':{}}}
    (directory/'compose.private.json').write_text(json.dumps(compose,indent=2))
    print(json.dumps({'prepared':True,'project':value['project'],'web':value['web_url'],'paid_provider_enabled':False,'old_workspaces_changed':False}))


def environment(directory):
    p=profile(directory);tree=ast.parse((ROOT/'apps/api/app/core/config.py').read_text())
    names={n.target.id.upper() for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Settings' for n in c.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)}
    env={k:v for k,v in os.environ.items() if k.upper() not in names and not k.upper().startswith(('OPENAI_','DESIGN_AI_','AIE37_','PORTUGUESE_','STAGING_','PT_SANDBOX_','ARTIFACT_'))}
    accounts=json.loads((directory/'credentials.private.json').read_text())
    env.update(DATABASE_URL='sqlite:///'+(directory/'portal.sqlite').as_posix(),SESSION_COOKIE_NAME=p['cookie'],SECURE_COOKIES='false',
        SERVICE_CONTRACT_PATH=str(directory/'service-contracts'),BOOTSTRAP_ADMIN_EMAIL=accounts['administrator']['email'],
        BOOTSTRAP_ADMIN_PASSWORD=accounts['administrator']['password'],BOOTSTRAP_ADMIN_NAME='Development fixture administrator',
        DESIGN_AI_ENABLED='true',DESIGN_AI_MODEL='',OPENAI_API_KEY='',DESIGN_AI_TEMPLATES='{}',
        ORCHESTRATOR_BASE_URL=p['wp3_url'],ORCHESTRATOR_API_KEY=p['orchestrator_key'],ORCHESTRATOR_SERVICES_API_KEY=p['control_key'],
        ARTIFACT_BASE_PATH=str(directory/'outputs'),ARTIFACT_BASE_PATHS='',INTERNAL_API_URL=p['api_url'],
        NEXT_PUBLIC_ENVIRONMENT_LABEL='DEVELOPMENT SOFTWARE FIXTURES — OFFLINE ASSISTANT DOUBLE; real Danish algorithms',
        NEXT_TELEMETRY_DISABLED='1',NO_PROXY='127.0.0.1,localhost',PYTHONDONTWRITEBYTECODE='1',
        REDIS_URL='redis://:'+p['redis_key']+'@127.0.0.1:26381/0',SERVICE_API_KEY=p['control_key'])
    return env


def serve(directory):
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB,'sqlite')
    def sqlite_jsonb(_type,compiler,**kwargs):return 'JSON'
    from app.main import app
    from app.services.design_ai_provider import get_provider
    from offline_provider import OfflineProvider
    app.dependency_overrides[get_provider]=lambda:OfflineProvider(directory)
    @app.middleware('http')
    async def identity(request,call_next):
        response=await call_next(request);response.headers['X-AI-Effect-Offline-Acceptance']='scripted-double';return response
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=28194,log_level='warning',access_log=False)


def node(directory,kind):
    root=directory/'node-source';folder=root/'services'/('topology_generator' if kind=='generator' else 'draw_topology')
    sys.path[:0]=[str(root),str(folder)]
    os.environ.update(DATA_DIR=str(directory/'outputs'),CONTROL_PARAMETER_QUALIFICATION_MODE='true',
        SERVICE_PARAMETER_CONTRACT_FILE=str(directory/'contracts'/('generator.json' if kind=='generator' else kind+'.json')))
    service=module('acceptance_native_'+kind,folder/'service.py')
    from common.concurrent import create_app
    import uvicorn
    uvicorn.run(create_app(service),host='127.0.0.1',port={'generator':28196,'renderer-a':28197,'renderer-b':28198}[kind],log_level='warning',access_log=False)


def start(directory):
    p=profile(directory);free_ports(PORTS[:-1]);env=environment(directory)
    helper=module('acceptance_review_helper',ROOT/'deploy/parameter_onboarding/review_workspace.py')
    generation=directory/'builds'/uuid4().hex;generation.mkdir(parents=True)
    shutil.copytree(ROOT/'apps/api/app',generation/'portal-api/app',ignore=shutil.ignore_patterns('__pycache__'))
    children=[]
    try:
        actions=[('_serve',None,p['api_url']+'/health'),('_wp3',None,p['wp3_url']+'/health'),('_worker',None,None)]
        actions += [('_node',kind,'http://127.0.0.1:'+str(port)+'/health') for kind,port in [('generator',28196),('renderer-a',28197),('renderer-b',28198)]]
        for action,kind,url in actions:
            child_env=dict(env)
            child_env['PYTHONPATH']=str(generation/'portal-api') if action=='_serve' else str(directory/'wp3-source')+os.pathsep+str(ROOT.parent/'qualification-20261118/test-packages')
            command=[sys.executable,str(Path(__file__).resolve()),action,'--directory',str(directory)]
            if kind:command+=['--node',kind]
            log=(directory/((kind or action)+'.private.log')).open('a')
            process=subprocess.Popen(command,env=child_env,cwd=directory,stdout=log,stderr=subprocess.STDOUT);children.append(process)
            if url:helper.wait_http(url,process)
        web=helper.prepare_frontend(generation,p);next_bin=Path(p['dependencies_directory']).parent/'apps/web/node_modules/next/dist/bin/next'
        with (directory/'web-build.private.log').open('w') as log:
            result=subprocess.run(['node',str(next_bin),'build'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Frontend build failed; inspect ignored private diagnostics')
        log=(directory/'web.private.log').open('a')
        process=subprocess.Popen(['node',str(next_bin),'start','-H','127.0.0.1','-p','23127'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT);children.append(process)
        helper.wait_http(p['web_url']+'/login',process)
        (directory/'serving.private.json').write_text(json.dumps({'generation':str(generation),'portal_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'offline_double':True},indent=2))
        print('READY: '+p['web_url']+'/login — OFFLINE ASSISTANT DOUBLE; real native Danish source',flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','start','_serve','_wp3','_worker','_node'])
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--wp3',type=Path);parser.add_argument('--dependencies',type=Path);parser.add_argument('--node')
    args=parser.parse_args();directory=args.directory.resolve()
    if args.action=='prepare':prepare(directory,args.wp3.resolve(),args.dependencies.resolve())
    elif args.action=='start':start(directory)
    else:
        os.environ.update(environment(directory))
        if args.action=='_serve':serve(directory)
        elif args.action=='_node':node(directory,args.node)
        elif args.action=='_wp3':
            from main import create_app
            import uvicorn
            uvicorn.run(create_app(),host='127.0.0.1',port=28195,log_level='warning',access_log=False)
        else:
            import redis
            from worker_daemon import WorkerDaemon
            WorkerDaemon(redis.Redis.from_url(os.environ['REDIS_URL'],decode_responses=True),poll_interval=.2).run()
