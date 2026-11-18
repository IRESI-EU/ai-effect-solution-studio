"""Fresh local execution workspace; never changes the guarded review profile.

Uses normal Portal roles/routes, native WP3/Redis/Worker, private real DGAN and
the configured connector. SQLite is development-only, not release qualification.
"""
import argparse
import ast
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f'
REDIS = 'sha256:8b81dd37ff027bec4e516d41acfbe9fe2460070dc6d4a4570a2ac5b9d59df065'


def module(path):
    spec = importlib.util.spec_from_file_location('workspace_review_helpers', path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def profile(directory):
    value = json.loads((directory / 'profile.private.json').read_text())
    if value['kind'] != 'normal-designer-execution-v1' or value['directory'] != str(directory.resolve()):
        raise RuntimeError('Unrecognized execution workspace')
    return value


def environment(directory):
    value = profile(directory)
    settings = ast.parse((ROOT / 'apps/api/app/core/config.py').read_text())
    names = {i.target.id.upper() for c in settings.body if isinstance(c, ast.ClassDef) and c.name == 'Settings'
             for i in c.body if isinstance(i, ast.AnnAssign) and isinstance(i.target, ast.Name)}
    env = {k:v for k,v in os.environ.items() if k.upper() not in names
           and not k.upper().startswith(('OPENAI_', 'DESIGN_AI_', 'AIE37_', 'PORTUGUESE_', 'STAGING_', 'PT_SANDBOX_'))}
    accounts = json.loads((directory / 'credentials.private.json').read_text())
    env.update(DATABASE_URL='sqlite:///' + (directory / 'portal.sqlite').as_posix(), SESSION_COOKIE_NAME=value['cookie'],
        SERVICE_CONTRACT_PATH=str(directory / 'service-contracts'), SECURE_COOKIES='false',
        BOOTSTRAP_ADMIN_EMAIL=accounts['administrator']['email'], BOOTSTRAP_ADMIN_PASSWORD=accounts['administrator']['password'],
        BOOTSTRAP_ADMIN_NAME='Development fixture administrator', DESIGN_AI_ENABLED='true', DESIGN_AI_MODEL='', OPENAI_API_KEY='',
        DESIGN_AI_TEMPLATES='{}', ORCHESTRATOR_BASE_URL=value['wp3_url'], ORCHESTRATOR_API_KEY=value['orchestrator_key'],
        ORCHESTRATOR_SERVICES_API_KEY=value['control_key'], OWNED_CONTROL_TARGETS_FILE=str(directory / 'targets.private.json'),
        INTERNAL_API_URL=value['api_url'], NEXT_PUBLIC_ENVIRONMENT_LABEL='DEVELOPMENT SOFTWARE FIXTURES — real local DGAN; paid AI disconnected',
        NEXT_TELEMETRY_DISABLED='1', NO_PROXY='127.0.0.1,localhost', PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(ROOT / 'apps/api'), REDIS_URL='redis://:' + value['redis_key'] + '@127.0.0.1:26380/0')
    return env


def prepare(directory, wp3, dependencies):
    if directory.exists(): raise RuntimeError('Use a NEW directory; never reset saved experiments')
    canonical = (ROOT / 'apps/api/app/services/runtime_observation.py').read_bytes()
    for variant in ('portugal-node-sidecar', 'portugal-node-integrated'):
        if (wp3 / 'use-cases' / variant / 'common/runtime_observation.py').read_bytes() != canonical:
            raise RuntimeError('Paired source must carry the identical reviewed observation validator')
    for port in (23126, 28191, 28192, 28193, 26380):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1); sock.bind(('127.0.0.1', port))
    directory.mkdir(parents=True, mode=0o700)
    if os.name == 'nt':
        owner = subprocess.check_output(['whoami'], text=True).strip()
        subprocess.run(['icacls', str(directory), '/inheritance:r', '/grant:r', owner + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL)
    value = {'kind': 'normal-designer-execution-v1', 'directory': str(directory.resolve()), 'project': 'aie-normal-' + uuid4().hex[:12],
        'cookie': 'aie_normal_' + uuid4().hex, 'api_url': 'http://127.0.0.1:28191', 'web_url': 'http://127.0.0.1:23126',
        'wp3_url': 'http://127.0.0.1:28192', 'connector_url': 'http://127.0.0.1:28193', 'namespace': 'fixture_' + uuid4().hex,
        'control_key': secrets.token_urlsafe(48), 'orchestrator_key': secrets.token_urlsafe(48),
        'observation_key': secrets.token_urlsafe(48), 'redis_key': secrets.token_urlsafe(48),
        'dependencies_directory': str(dependencies.resolve() / 'node_modules')}
    accounts = {role: {'email': role + '@normal-designer.invalid', 'password': 'Fixture-9-' + secrets.token_urlsafe(32)}
                for role in ('administrator', 'provider', 'designer', 'other_designer')}
    (directory / 'profile.private.json').write_text(json.dumps(value, indent=2)); (directory / 'credentials.private.json').write_text(json.dumps(accounts, indent=2))
    for name in ('contracts', 'inputs', 'service-contracts'): (directory / name).mkdir()
    # Frozen source copies; only this explicit workspace is attached to them.
    shutil.copytree(wp3 / 'orchestrator/src', directory / 'wp3-source', ignore=shutil.ignore_patterns('__pycache__', 'logs'))
    shutil.copytree(wp3 / 'use-cases/portugal-node-sidecar/common', directory / 'connector-source/common', ignore=shutil.ignore_patterns('__pycache__'))
    (directory / 'contracts/installed.json').write_text(json.dumps({'capability_schema_version': '1.0', 'transports': ['http-parameters-v1'], 'qualification_only': True, 'operations': []}))
    fixture = 'datetime,load,temperature\n' + ''.join(f'2026-11-18T00:{i:02d}:00,{1 + math.sin(i/4):.6f},{18 + math.cos(i/5):.6f}\n' for i in range(32))
    (directory / 'inputs/DEVELOPMENT-SOFTWARE-FIXTURE.csv').write_bytes(fixture.encode())
    (directory / 'targets.private.json').write_text(json.dumps({'targets': [{'runtime_destination': value['wp3_url'],
        'base_url': value['connector_url'], 'token': value['control_key'], 'observation_contracts': ['algorithm-settings-v1']}]}))
    (directory / 'control.private.env').write_text('SERVICE_API_KEY=' + value['control_key'] + '\nSYNTHETIC_DATA_OBSERVATION_KEY=' + value['observation_key'] + '\n')
    (directory / 'ml.private.env').write_text('RUNTIME_OBSERVATION_API_KEY=' + value['observation_key'] + '\n')
    (directory / 'redis.private.conf').write_text('bind 0.0.0.0\nappendonly yes\nrequirepass ' + value['redis_key'] + '\n')
    def bind(path, target): return {'type': 'bind', 'source': str(path), 'target': target, 'read_only': True}
    compose = {'name': value['project'], 'services': {
        'redis': {'image': REDIS, 'pull_policy': 'never', 'command': ['redis-server', '/private/redis.conf'], 'ports': ['127.0.0.1:26380:6379'],
            'networks': ['loopback'], 'volumes': ['redis:/data', bind(directory / 'redis.private.conf', '/private/redis.conf')]},
        'ml': {'image': IMAGE, 'pull_policy': 'never', 'command': ['python', '/qualification/ml_observer.py'], 'env_file': [str(directory / 'ml.private.env')],
            'environment': {'OBSERVED_ML_IMAGE': IMAGE, 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
            'networks': ['private'], 'cpus': 2, 'mem_limit': '2g', 'volumes': [
                {'type': 'volume', 'source': 'models', 'target': '/app/models', 'volume': {'nocopy': True}}, 'observations:/qualification-evidence',
                bind(HERE, '/qualification'), bind(ROOT / 'apps/api/app/services', '/observation-contract')]},
        'connector': {'image': IMAGE, 'pull_policy': 'never', 'command': ['python', '/connector-entry/connector.py'],
            'env_file': [str(directory / 'control.private.env')], 'environment': {'SERVICE_PARAMETER_CONTRACT_DIR': '/contracts',
                'CONTROL_PARAMETER_STATE_DIR': '/state', 'CONTROL_PARAMETER_QUALIFICATION_MODE': 'true',
                'SYNTHETIC_DATA_URL': 'http://ml:600', 'SYNTHETIC_DATA_OBSERVATION_URL': 'http://ml:600/runtime-observations',
                'SELF_URL': value['connector_url'], 'SYNTHETIC_DATA_USER_NAMESPACE': value['namespace'], 'SYNTHETIC_DATA_INDEX_COLUMN': 'datetime'},
            'networks': ['private', 'loopback'], 'ports': ['127.0.0.1:28193:8080'], 'volumes': [
                'state:/state', bind(directory / 'contracts', '/contracts'), bind(directory / 'connector-source', '/qualification-source'),
                bind(ROOT / 'deploy/portuguese_qualification', '/connector-entry')]}
        }, 'networks': {'private': {'internal': True}, 'loopback': {}}, 'volumes': {'redis': {}, 'models': {}, 'state': {}, 'observations': {}}}
    (directory / 'compose.private.json').write_text(json.dumps(compose, indent=2))
    print(json.dumps({'prepared': True, 'project': value['project'], 'api': value['api_url'], 'web': value['web_url'], 'retained_workspaces_changed': False}))


def serve(directory):
    env = environment(directory)
    os.environ.clear(); os.environ.update(env)
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB, 'sqlite')
    def sqlite_jsonb(_type, compiler, **kwargs): return 'JSON'
    from app.main import app
    value = profile(directory)
    @app.middleware('http')
    async def development_identity(request, call_next):
        response = await call_next(request); response.headers['X-AI-Effect-Development'] = value['cookie']; return response
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=28191, log_level='warning', access_log=False)


def wp3_process(directory, worker=False):
    env = environment(directory); os.environ.update(env)
    sys.path.insert(0, str(directory / 'wp3-source'))
    if worker:
        import redis
        from worker_daemon import WorkerDaemon
        WorkerDaemon(redis.Redis.from_url(env['REDIS_URL'], decode_responses=True), poll_interval=.2).run()
    else:
        import uvicorn
        from main import create_app
        uvicorn.run(create_app(), host='127.0.0.1', port=28192, log_level='warning', access_log=False)


def start(directory):
    value = profile(directory); env = environment(directory)
    for port in (23126, 28191, 28192):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1); sock.bind(('127.0.0.1', port))
    helper = module(ROOT / 'deploy/parameter_onboarding/review_workspace.py')
    children = []
    try:
        for action, url in [('_serve', value['api_url'] + '/health'), ('_wp3', value['wp3_url'] + '/health'), ('_worker', None)]:
            child_env = dict(env)
            if action != '_serve': child_env['PYTHONPATH'] = str(directory / 'wp3-source') + os.pathsep + str(ROOT.parent / 'qualification-20261118/test-packages')
            log = (directory / (action + '.private.log')).open('a')
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), action, '--directory', str(directory)], env=child_env, stdout=log, stderr=subprocess.STDOUT)
            children.append(process)
            if url: helper.wait_http(url, process)
        record = directory / 'web-build.private.json'
        names = subprocess.check_output(['git','ls-files','-z','--','apps/web','examples','package.json','pnpm-lock.yaml','pnpm-workspace.yaml'],cwd=ROOT).decode().split('\0')
        source_hash = hashlib.sha256()
        for name in sorted(filter(None,names)):
            path = ROOT / name
            if path.is_file(): source_hash.update(name.encode()); source_hash.update(path.read_bytes())
        fingerprint = source_hash.hexdigest()
        build = json.loads(record.read_text()) if record.exists() else {}
        if build.get('frontend_source_sha256') != fingerprint:
            # Preserve every earlier build and its source; build in a fresh directory.
            build_directory = directory / 'builds' / uuid4().hex
            build_directory.mkdir(parents=True)
            web = helper.prepare_frontend(build_directory, value)
            next_bin = Path(value['dependencies_directory']).parent / 'apps/web/node_modules/next/dist/bin/next'
            with (directory / 'web-build.private.log').open('w') as log:
                result = subprocess.run(['node', str(next_bin), 'build'], cwd=web, env=env, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode: raise RuntimeError('Isolated frontend build failed; inspect private build log')
            build = {'portal_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'frontend_source_sha256': fingerprint, 'directory': str(web)}
            record.write_text(json.dumps(build))
        web = Path(build['directory'])
        next_bin = Path(value['dependencies_directory']).parent / 'apps/web/node_modules/next/dist/bin/next'
        log = (directory / 'web.private.log').open('a')
        process = subprocess.Popen(['node', str(next_bin), 'start', '-H', '127.0.0.1', '-p', '23126'], cwd=web, env=env, stdout=log, stderr=subprocess.STDOUT)
        children.append(process); helper.wait_http(value['web_url'] + '/login', process)
        print('READY: normal development execution ' + value['web_url'] + '/login', flush=True)
        while all(p.poll() is None for p in children): time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None: child.terminate(); child.wait(timeout=8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'start', '_serve', '_wp3', '_worker'])
    parser.add_argument('--directory', type=Path, required=True); parser.add_argument('--wp3', type=Path); parser.add_argument('--dependencies', type=Path)
    args = parser.parse_args(); args.directory = args.directory.resolve()
    if args.action == 'prepare': prepare(args.directory, args.wp3.resolve(), args.dependencies.resolve())
    elif args.action == 'start': start(args.directory)
    elif args.action == '_serve': serve(args.directory)
    else: wp3_process(args.directory, worker=args.action == '_worker')
