"""One genuine acceptance workspace; real provider, no dependency override/fallback.

prepare/start never dispatch an LLM call or initialize a spending ledger. Normal
publisher onboarding and the existing exclusive scoped ledger remain authoritative.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import logging
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
REDIS='sha256:8b81dd37ff027bec4e516d41acfbe9fe2460070dc6d4a4570a2ac5b9d59df065'
PORTS=(23128,28199,28200,28201,28202,28203,26382)
MODEL='gpt-5.4-mini-2026-03-17'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value


def profile(directory):
    value=json.loads((directory/'profile.private.json').read_text())
    if value['kind']!='genuine-saved-solution-v1' or value['directory']!=str(directory.resolve()):raise RuntimeError('Wrong acceptance workspace')
    return value


def key_from_project(path,project):
    """Read only the explicitly authorised project's ignored dotenv file."""
    path=path.resolve();project=project.resolve()
    if not path.is_relative_to(project) or not path.is_file():raise RuntimeError('Key source must be a project-local configuration file')
    if subprocess.run(['git','check-ignore','--quiet','--',path.relative_to(project).as_posix()],cwd=project).returncode:
        raise RuntimeError('Key source must be ignored; never use tracked credentials')
    from dotenv import dotenv_values
    value=dotenv_values(path,interpolate=False).get('OPENAI_API_KEY')
    if not isinstance(value,str) or not value.startswith('sk-') or len(value)<=25:raise RuntimeError('No suitable configured project key; no provider probe was made')
    return value


def free(ports):
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);sock.bind(('127.0.0.1',port))


def prepare(directory,wp3,dependencies,key_source,project,authorization,ports=PORTS,offline_ui=False):
    if directory.exists():raise RuntimeError('Use a fresh directory; never replace an acceptance scope')
    if len(ports)!=7 or len(set(ports))!=7:raise RuntimeError('Seven distinct loopback ports are required')
    free(ports)
    if not offline_ui:key_from_project(key_source,project)
    web_port,api_port,wp3_port,gen_port,draw_a_port,draw_b_port,redis_port=ports
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=wp3,text=True).strip()!='39405313f9b685d91b8263b9b87a3fc42577331d':
        raise RuntimeError('Verify the reviewed WP3 source identity before preparation')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=wp3,text=True).strip():raise RuntimeError('Preserve dirty WP3 source')
    directory.mkdir(parents=True,mode=0o700)
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,stdout=subprocess.DEVNULL)
    value={'kind':'genuine-saved-solution-v1','directory':str(directory),'project':'aie-genuine-'+uuid4().hex[:12],
        'cookie':'aie_genuine_'+uuid4().hex,'api_url':f'http://127.0.0.1:{api_port}','web_url':f'http://127.0.0.1:{web_port}','wp3_url':f'http://127.0.0.1:{wp3_port}',
        'node_ports':{'generator':gen_port,'renderer-a':draw_a_port,'renderer-b':draw_b_port},'redis_port':redis_port,'ports':list(ports),'offline_ui_fixture':offline_ui,
        'control_key':secrets.token_urlsafe(48),'orchestrator_key':secrets.token_urlsafe(48),'redis_key':secrets.token_urlsafe(48),
        'dependencies_directory':str(dependencies/'node_modules'),'key_source':str(key_source.resolve()),'key_project':str(project.resolve()),
        'authorization_ref':'AI-EFFECT genuine acceptance user prompt 2026-11-19 sha256:'+hashlib.sha256(authorization.read_bytes()).hexdigest()+'; project key reuse and one conditional two-phase exercise explicitly authorised'}
    (directory/'profile.private.json').write_text(json.dumps(value,indent=2))
    accounts={role:{'email':role+'@genuine-fixture.invalid','password':'Fixture-9-'+secrets.token_urlsafe(32)} for role in ('administrator','provider','designer','other_designer')}
    (directory/'credentials.private.json').write_text(json.dumps(accounts,indent=2))
    for name in ('contracts','outputs','service-contracts'): (directory/name).mkdir()
    shutil.copytree(wp3/'orchestrator/src',directory/'wp3-source',ignore=shutil.ignore_patterns('__pycache__','logs'))
    shutil.copytree(wp3/'use-cases/denmark-node',directory/'node-source',ignore=shutil.ignore_patterns('__pycache__','.git'))
    (directory/'fixture-input.json').write_text(json.dumps({'run_config':{'supplies':['310-D::CHP'],'loads':['716-D::Dumpload']}}))
    (directory/'redis.private.conf').write_text('bind 0.0.0.0\nappendonly yes\nrequirepass '+value['redis_key']+'\n')
    compose={'name':value['project'],'services':{'redis':{'image':REDIS,'pull_policy':'never','command':['redis-server','/private/redis.conf'],
        'ports':[f'127.0.0.1:{redis_port}:6379'],'volumes':['redis:/data',{'type':'bind','source':str(directory/'redis.private.conf'),'target':'/private/redis.conf','read_only':True}]}},'volumes':{'redis':{}}}
    (directory/'compose.private.json').write_text(json.dumps(compose,indent=2))
    print(json.dumps({'prepared':True,'real_provider_selected':True,'paid_dispatch_active':False,'ledger_created':False,'old_workspaces_changed':False}))


def environment(directory):
    p=profile(directory);tree=ast.parse((ROOT/'apps/api/app/core/config.py').read_text())
    names={n.target.id.upper() for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Settings' for n in c.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)}
    env={k:v for k,v in os.environ.items() if k.upper() not in names and not k.upper().startswith(('OPENAI_','DESIGN_AI_','AIE37_','PORTUGUESE_','STAGING_','PT_SANDBOX_','ARTIFACT_'))}
    accounts=json.loads((directory/'credentials.private.json').read_text())
    env.update(DATABASE_URL='sqlite:///'+(directory/'portal.sqlite').as_posix(),SESSION_COOKIE_NAME=p['cookie'],SECURE_COOKIES='false',
        SERVICE_CONTRACT_PATH=str(directory/'service-contracts'),BOOTSTRAP_ADMIN_EMAIL=accounts['administrator']['email'],BOOTSTRAP_ADMIN_PASSWORD=accounts['administrator']['password'],
        BOOTSTRAP_ADMIN_NAME='Development acceptance administrator',DESIGN_AI_ENABLED='true',DESIGN_AI_MODEL=MODEL,OPENAI_API_KEY='',DESIGN_AI_TEMPLATES='{}',
        DESIGN_AI_SCOPED_ACCEPTANCE_FILE=str(directory/'acceptance.private.sqlite'),DESIGN_AI_REASONING_EFFORT='none',DESIGN_AI_MAX_OUTPUT_TOKENS='3000',DESIGN_AI_TIMEOUT_SECONDS='60',
        ORCHESTRATOR_BASE_URL=p['wp3_url'],ORCHESTRATOR_API_KEY=p['orchestrator_key'],ORCHESTRATOR_SERVICES_API_KEY=p['control_key'],
        ARTIFACT_BASE_PATH=str(directory/'outputs'),ARTIFACT_BASE_PATHS='',INTERNAL_API_URL=p['api_url'],NEXT_PUBLIC_ENVIRONMENT_LABEL='GENUINE LLM ACCEPTANCE — DEVELOPMENT SOFTWARE FIXTURES',
        NEXT_TELEMETRY_DISABLED='1',NO_PROXY='127.0.0.1,localhost',PYTHONDONTWRITEBYTECODE='1',REDIS_URL='redis://:'+p['redis_key']+'@127.0.0.1:'+str(p['redis_port'])+'/0',SERVICE_API_KEY=p['control_key'])
    if p.get('offline_ui_fixture'):
        env.update(OPENAI_API_KEY='',DESIGN_AI_MODEL='',DESIGN_AI_SCOPED_ACCEPTANCE_FILE='',NEXT_PUBLIC_ENVIRONMENT_LABEL='OFFLINE ASSUMPTION DISCLOSURE FIXTURE — NO MODEL')
    return env


def serve(directory):
    p=profile(directory)
    if not p.get('offline_ui_fixture'):os.environ['OPENAI_API_KEY']=key_from_project(Path(p['key_source']),Path(p['key_project']))
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB,'sqlite')
    def sqlite_jsonb(_type,compiler,**kwargs):return 'JSON'
    from app.main import app
    from app.services.design_ai_provider import get_provider,OpenAIProvider
    if p.get('offline_ui_fixture'):
        from ui_disclosure_fixture import DisclosureFixture
        app.dependency_overrides[get_provider]=lambda:DisclosureFixture()
    elif get_provider in app.dependency_overrides or not isinstance(get_provider(),OpenAIProvider):raise RuntimeError('Genuine acceptance forbids provider overrides')
    audit=logging.getLogger('design_ai.provider.audit');audit.setLevel(logging.DEBUG);audit.propagate=False
    audit.addHandler(logging.FileHandler(directory/'provider-audit.private.jsonl',encoding='utf-8'))
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=int(p['api_url'].rsplit(':',1)[1]),log_level='warning',access_log=False)


def node(directory,kind):
    p=profile(directory);root=directory/'node-source';folder=root/'services'/('topology_generator' if kind=='generator' else 'draw_topology')
    sys.path[:0]=[str(root),str(folder)]
    os.environ.update(DATA_DIR=str(directory/'outputs'),CONTROL_PARAMETER_QUALIFICATION_MODE='true',
        SERVICE_PARAMETER_CONTRACT_FILE=str(directory/'contracts'/('generator.json' if kind=='generator' else kind+'.json')))
    service=module('genuine_native_'+kind,folder/'service.py')
    from common.concurrent import create_app
    import uvicorn
    uvicorn.run(create_app(service),host='127.0.0.1',port=p['node_ports'][kind],log_level='warning',access_log=False)


def start(directory):
    p=profile(directory);free(p.get('ports',list(PORTS))[:-1]);env=environment(directory)
    helper=module('genuine_review_helper',ROOT/'deploy/parameter_onboarding/review_workspace.py')
    generation=directory/'builds'/uuid4().hex;generation.mkdir(parents=True)
    shutil.copytree(ROOT/'apps/api/app',generation/'portal-api/app',ignore=shutil.ignore_patterns('__pycache__'))
    children=[]
    try:
        actions=[('_serve',None,p['api_url']+'/health'),('_wp3',None,p['wp3_url']+'/health'),('_worker',None,None)]
        actions += [('_node',kind,'http://127.0.0.1:'+str(port)+'/health') for kind,port in p['node_ports'].items()]
        for action,kind,url in actions:
            child_env=dict(env);child_env['PYTHONPATH']=str(generation/'portal-api') if action=='_serve' else str(directory/'wp3-source')+os.pathsep+str(ROOT.parent/'qualification-20261118/test-packages')
            command=[sys.executable,str(Path(__file__).resolve()),action,'--directory',str(directory)]
            if kind:command+=['--node',kind]
            log=(directory/((kind or action)+'.private.log')).open('a')
            process=subprocess.Popen(command,env=child_env,cwd=directory,stdout=log,stderr=subprocess.STDOUT);children.append(process)
            if url:helper.wait_http(url,process)
        web=helper.prepare_frontend(generation,p);next_bin=Path(p['dependencies_directory']).parent/'apps/web/node_modules/next/dist/bin/next'
        with (directory/'web-build.private.log').open('w') as log:
            result=subprocess.run(['node',str(next_bin),'build'],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Build failed; inspect ignored private diagnostics')
        log=(directory/'web.private.log').open('a');process=subprocess.Popen(['node',str(next_bin),'start','-H','127.0.0.1','-p',p['web_url'].rsplit(':',1)[1]],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT);children.append(process)
        helper.wait_http(p['web_url']+'/login',process)
        (directory/'serving.private.json').write_text(json.dumps({'generation':str(generation),'portal_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'offline_double':bool(p.get('offline_ui_fixture'))},indent=2))
        print('READY: '+p['web_url']+'/login — real provider; scoped ledger must be activated before any message',flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','start','_serve','_wp3','_worker','_node'])
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--wp3',type=Path);parser.add_argument('--dependencies',type=Path)
    parser.add_argument('--ports',type=int,nargs=7);parser.add_argument('--offline-ui',action='store_true')
    parser.add_argument('--key-source',type=Path);parser.add_argument('--project',type=Path);parser.add_argument('--authorization',type=Path);parser.add_argument('--node')
    args=parser.parse_args();directory=args.directory.resolve()
    if args.action=='prepare':prepare(directory,args.wp3.resolve(),args.dependencies.resolve(),args.key_source,args.project,args.authorization,tuple(args.ports or PORTS),args.offline_ui)
    elif args.action=='start':start(directory)
    else:
        os.environ.update(environment(directory))
        if args.action=='_serve':serve(directory)
        elif args.action=='_node':node(directory,args.node)
        elif args.action=='_wp3':
            from main import create_app
            import uvicorn
            uvicorn.run(create_app(),host='127.0.0.1',port=int(profile(directory)['wp3_url'].rsplit(':',1)[1]),log_level='warning',access_log=False)
        else:
            import redis
            from worker_daemon import WorkerDaemon
            WorkerDaemon(redis.Redis.from_url(os.environ['REDIS_URL'],decode_responses=True),poll_interval=.2).run()
