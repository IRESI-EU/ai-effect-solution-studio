"""Separate local provider-review workspace. Never attaches to the retained demo.

Uses the real Portal with a dedicated SQLite review database (not PostgreSQL
qualification), normal authentication and copied PUBLIC catalogue metadata.
No runtime, grant, provider key or experimental ledger is attached.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / 'apps/web'
THIS = Path(__file__).resolve()
SERVICE_FIELDS = {'name', 'provider', 'category', 'description', 'input_type', 'output_type', 'version', 'container_name',
    'image', 'proto_uri', 'node_type', 'operation_name', 'input_message_name', 'output_message_name', 'internal_host',
    'internal_port', 'repository_url', 'repository_branch', 'manifest_path', 'interface_type', 'orchestration_mode',
    'adapter_type', 'health_path', 'contract_uri', 'lifecycle_status'}


def write_private(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')
    path.chmod(0o600)


def read_profile(directory):
    directory = directory.resolve()
    profile = json.loads((directory / 'profile.json').read_text())
    if (profile.get('kind') != 'isolated-provider-review-v1' or profile['directory'] != str(directory)
            or profile['database'] != str(directory / 'review.sqlite')
            or not profile['cookie'].startswith('aieffect_provider_review_')):
        raise RuntimeError('This is not the isolated review workspace; nothing was started')
    if any(port in {23124, 28188} or not 1024 <= port <= 65535 for port in (profile['web_port'], profile['api_port'])) or profile['web_port'] == profile['api_port']:
        raise RuntimeError('Choose distinct unprivileged review ports, separate from the retained demo')
    return directory, profile


def clean_environment(profile):
    # Read only setting names, without importing environment-dependent app code.
    tree = ast.parse((REPO / 'apps/api/app/core/config.py').read_text())
    names = {item.target.id.upper() for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Settings'
             for item in node.body if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)}
    environment = {key: value for key, value in os.environ.items() if key.upper() not in names
        and not key.upper().startswith(('OPENAI_', 'DESIGN_AI_', 'PT_SANDBOX_', 'STAGING_', 'AIE37_', 'PORTUGUESE_'))}
    environment.update(DATABASE_URL='sqlite:///' + Path(profile['database']).as_posix(),
        SERVICE_CONTRACT_PATH=str(Path(profile['directory']) / 'service-contracts'),
        SESSION_COOKIE_NAME=profile['cookie'], SECURE_COOKIES='false', DESIGN_AI_ENABLED='true',
        DESIGN_AI_RESTRICTED_BETA='false', DESIGN_AI_LOCAL_PILOT='false', OPENAI_API_KEY='', DESIGN_AI_MODEL='',
        DESIGN_AI_TEMPLATES='{}', DESIGN_AI_REGISTRATION_ENVIRONMENT='',
        ORCHESTRATOR_BASE_URL='http://127.0.0.1:9', ORCHESTRATOR_API_KEY='', ORCHESTRATOR_SERVICES_API_KEY='',
        BOOTSTRAP_ADMIN_EMAIL='', BOOTSTRAP_ADMIN_PASSWORD='',
        INTERNAL_API_URL=f"http://127.0.0.1:{profile['api_port']}", NEXT_BUILD_DIR=profile['build_directory'],
        NEXT_PUBLIC_ENVIRONMENT_LABEL='OFFLINE provider review - new build - execution and AI calls disabled',
        NEXT_TELEMETRY_DISABLED='1', PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(REPO / 'apps/api'), NO_PROXY='127.0.0.1,localhost')
    return environment


def prepare(directory, catalogue, source_reference, web_port=23125, api_port=28189, dependencies_from=None):
    directory = directory.resolve()
    if directory.exists():
        raise RuntimeError('Choose a NEW directory. Existing profiles, credentials and saved data are never replaced')
    if not isinstance(catalogue, list) or not catalogue or any(not isinstance(row, dict) for row in catalogue):
        raise ValueError('Supply a non-empty public catalogue JSON array')
    sys.path.insert(0, str(REPO / 'apps/api'))
    from app.schemas.auth import NodeCode
    from typing import get_args
    nodes = set(get_args(NodeCode))
    owners = {row.get('owner_node') for row in catalogue if row.get('owner_node') in nodes}
    if not owners:
        raise ValueError('The catalogue has no declared supported node ownership; do not guess owners')
    if any(port in {23124, 28188} or not 1024 <= port <= 65535 for port in (web_port, api_port)) or web_port == api_port:
        raise ValueError('Review ports must be distinct and separate from the retained demo')
    if any(not row.get('name') or not row.get('provider') or not row.get('category') for row in catalogue):
        raise ValueError('Catalogue rows need declared names, providers and categories')
    directory.mkdir(parents=True, mode=0o700)
    if os.name == 'nt':
        owner = subprocess.check_output(['whoami'], text=True).strip()
        subprocess.run(['icacls', str(directory), '/inheritance:r', '/grant:r', owner + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL)
    profile_id = uuid4().hex
    profile = {'kind': 'isolated-provider-review-v1', 'id': profile_id, 'directory': str(directory),
        'database': str(directory / 'review.sqlite'), 'cookie': 'aieffect_provider_review_' + profile_id,
        'web_port': web_port, 'api_port': api_port, 'build_directory': '.next-provider-review-' + profile_id,
        'dependencies_directory': str((Path(dependencies_from) if dependencies_from else REPO) / 'node_modules'),
        'source_reference': source_reference, 'catalogue_sha256': hashlib.sha256(json.dumps(catalogue, sort_keys=True).encode()).hexdigest(),
        'prepared_at': datetime.now(timezone.utc).isoformat(), 'catalogue_count': len(catalogue)}
    accounts = {key: {'email': key.replace('_', '-') + '@provider-review.invalid', 'password': 'Review-9-' + secrets.token_urlsafe(28),
                     'role': role, 'node': node, 'id': str(uuid4())}
                for key, role, node in [('administrator', 'platform_admin', None), ('designer', 'solution_designer', None)]
                + [('provider_' + node, 'node_manager', node) for node in sorted(owners)]}
    # Preserve only relevant public metadata, not unknown interface documents,
    # copied approvals, user identifiers or pre-existing parameter contracts.
    snapshot = [{'source_id': row.get('id'), 'source_status': row.get('status'), 'owner_node': row.get('owner_node'),
                 'metadata': {key: row.get(key) for key in SERVICE_FIELDS if key in row}} for row in catalogue]
    write_private(directory / 'profile.json', profile)
    write_private(directory / 'credentials.private.json', accounts)
    write_private(directory / 'catalogue.private.json', snapshot)
    (directory / 'service-contracts').mkdir()
    # Validate ports/profile identity before importing a database engine.
    read_profile(directory)
    result = subprocess.run([sys.executable, str(THIS), '_seed', '--directory', str(directory)], env=clean_environment(profile),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (directory / 'seed.log').write_text(result.stdout)
    if result.returncode:
        raise RuntimeError('Workspace preparation failed; existing environments are unchanged. See seed.log in the new directory')
    return profile


def seed(directory):
    directory, profile = read_profile(directory)
    environment = clean_environment(profile)
    os.environ.clear(); os.environ.update(environment)
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB, 'sqlite')
    def sqlite_jsonb(_type, compiler, **kwargs): return 'JSON'
    from app.main import app  # Normal model/schema initialization, no HTTP requests.
    from app.db import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.service import Service
    accounts = json.loads((directory / 'credentials.private.json').read_text())
    rows = json.loads((directory / 'catalogue.private.json').read_text())
    with SessionLocal() as db:
        if db.query(User).first() or db.query(Service).first():
            raise RuntimeError('Review database is not empty; seed never resets data')
        for account in accounts.values():
            db.add(User(id=account['id'], email=account['email'], display_name=account['email'].split('@')[0].replace('-', ' ').title(),
                        password_hash=hash_password(account['password']), role=account['role'], node=account['node'], status='active'))
        for row in rows:
            values = row['metadata']
            values = {key: value for key, value in values.items() if value is not None}
            values['name'] = 'REVIEW COPY - ' + values['name']
            db.add(Service(id=str(uuid4()), **values, owner_node=row['owner_node'], status='pending_review', trust_badge='pending_review',
                interface_contract={'review_source': {'reference': profile['source_reference'], 'source_id': row['source_id'],
                    'source_status': row['source_status'], 'catalogue_sha256': profile['catalogue_sha256'], 'runtime_qualified': False}}))
        db.commit()
    print(json.dumps({'review_accounts': len(accounts), 'unqualified_metadata_copies': len(rows), 'contracts_published': 0, 'executions': 0}))


def create_review_app(directory):
    directory, profile = read_profile(directory)
    environment = clean_environment(profile)
    os.environ.clear(); os.environ.update(environment)
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB, 'sqlite')
    def sqlite_jsonb(_type, compiler, **kwargs): return 'JSON'
    from app.main import app
    from fastapi.responses import JSONResponse
    @app.middleware('http')
    async def review_only(request, call_next):
        path = request.url.path
        permitted = (path in {'/health', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/workflows/compile', '/workflows/training-input', '/deployments'}
            or path.startswith(('/auth/', '/admin/users', '/services', '/operation-contracts/', '/solutions', '/design-ai')))
        design_read_or_edit = (not path.startswith('/design-ai') or path == '/design-ai/config'
            or (path.startswith('/design-ai/solutions/') and (request.method == 'GET' or path.endswith(('/apply', '/undo', '/dismiss')))))
        blocked = (not permitted or not design_read_or_edit or path.endswith('/runtime/verify') or '/confirm-runtime' in path
            or (path.startswith('/operation-contracts/') and path.endswith('/activate')) or path.endswith('/chat'))
        if blocked:
            return JSONResponse(status_code=409, content={'detail': 'Provider-review workspace only: runtime qualification, publication, execution and AI calls are not enabled here.'})
        response = await call_next(request)
        response.headers['X-AI-Effect-Review-Only'] = 'true'
        response.headers['X-AI-Effect-Review-Profile'] = profile['id']
        return response
    return app


def check_port(port):
    with socket.socket() as sock:
        if os.name == 'nt': sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))


def wait_http(url, process, timeout=45, expected_profile=None):
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None: raise RuntimeError('Review process exited; inspect its log in the new profile directory')
        try:
            with opener.open(url, timeout=2) as response:
                if response.status == 200:
                    if expected_profile and response.headers.get('X-AI-Effect-Review-Profile') != expected_profile:
                        raise RuntimeError('The listening API is not this isolated review profile')
                    return
        except (OSError, urllib.error.URLError): pass
        time.sleep(.2)
    raise RuntimeError('Review process did not become ready; inspect its log')


def prepare_frontend(directory, profile):
    """Build in a source copy. Next may rewrite TS metadata only in that copy."""
    target = directory / 'frontend-source'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', 'apps/web', 'examples', 'package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml'], cwd=REPO).decode().split('\0')
    for name in filter(None, paths):
        source = REPO / name
        if source.is_file():
            destination = target / name; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    modules = Path(profile.get('dependencies_directory', str(REPO / 'node_modules'))).resolve()
    if not modules.is_dir(): raise RuntimeError('Reviewed Node dependencies are missing; none were installed')
    link = target / 'node_modules'
    def link_directory(destination, source):
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(destination), str(source)], check=True, stdout=subprocess.DEVNULL)
        else: destination.symlink_to(source, target_is_directory=True)
    link_directory(link, modules)
    web_modules = modules.parent / 'apps/web/node_modules'
    if web_modules.is_dir():
        link_directory(target / 'apps/web/node_modules', web_modules)
    common = os.path.commonpath([str(target.resolve()), str(modules.resolve())])
    original = str(REPO / 'apps/web/next.config.js')
    (target / 'apps/web/next.config.js').write_text('const base = require(' + json.dumps(original) + ');\nmodule.exports = {...base, distDir: ".next", turbopack: {...base.turbopack, root: ' + json.dumps(common) + '}};\n')
    return target / 'apps/web'


def start(directory, api_only=False, open_browser=False):
    directory, profile = read_profile(directory)
    check_port(profile['api_port'])
    if not api_only: check_port(profile['web_port'])
    environment = clean_environment(profile)
    modules = Path(profile.get('dependencies_directory', str(REPO / 'node_modules')))
    next_bin = modules / 'next/dist/bin/next'
    if not next_bin.is_file(): next_bin = modules.parent / 'apps/web/node_modules/next/dist/bin/next'
    node = shutil.which('node')
    if not api_only and (not node or not next_bin.is_file()):
        raise RuntimeError('Use the checked-out Portal with its reviewed Node dependencies. No packages were installed or existing services changed')
    children = []
    try:
        print('Starting the separate provider-review API...', flush=True)
        api_log = (directory / 'api.log').open('a')
        api = subprocess.Popen([sys.executable, str(THIS), '_serve', '--directory', str(directory)], env=environment,
                               stdout=api_log, stderr=subprocess.STDOUT)
        children.append(api); wait_http(f"http://127.0.0.1:{profile['api_port']}/health", api, expected_profile=profile['id'])
        if not api_only:
            record = directory / 'web-build.json'
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
            dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPO, text=True).strip()
            build_web = directory / 'frontend-source/apps/web'
            if not record.exists() or not (build_web / '.next/BUILD_ID').is_file() or json.loads(record.read_text()).get('source') != revision or dirty:
                build_web = prepare_frontend(directory, profile)
                print('Building the review interface in a separate source copy. Existing files are unchanged.', flush=True)
                with (directory / 'web-build.log').open('w') as log:
                    result = subprocess.run([node, str(next_bin), 'build'], cwd=build_web, env=environment, stdout=log, stderr=subprocess.STDOUT)
                if result.returncode: raise RuntimeError('Review frontend build failed; see web-build.log. No dependency installation was attempted')
                record.write_text(json.dumps({'source': revision, 'dirty_at_build': bool(dirty)}))
            web_log = (directory / 'web.log').open('a')
            web = subprocess.Popen([node, str(next_bin), 'start', '-H', '127.0.0.1', '-p', str(profile['web_port'])],
                                   cwd=build_web, env=environment, stdout=web_log, stderr=subprocess.STDOUT)
            children.append(web); wait_http(f"http://127.0.0.1:{profile['web_port']}/login", web)
        print(json.dumps({'running': True, 'review_only': True,
            'url': f"http://127.0.0.1:{profile['api_port'] if api_only else profile['web_port']}",
            'credentials_file': str(directory / 'credentials.private.json'), 'retained_demo_changed': False}), flush=True)
        if not api_only:
            browser_url = f"http://127.0.0.1:{profile['web_port']}/login"
            print('READY: open ' + browser_url, flush=True)
            print('Use a node-provider account from the private credentials file to open Publish.', flush=True)
            if open_browser:
                import webbrowser
                webbrowser.open(browser_url)
        print('Keep this window open. Ctrl+C stops only these new review processes.', flush=True)
        while all(child.poll() is None for child in children): time.sleep(.5)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=8)
                except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'launch', 'start', '_seed', '_serve'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--catalogue-file', type=Path)
    parser.add_argument('--catalogue-url', default='https://platform.ai-effect.eu/api/services')
    parser.add_argument('--web-port', type=int, default=23125)
    parser.add_argument('--api-port', type=int, default=28189)
    parser.add_argument('--api-only', action='store_true')
    parser.add_argument('--dependencies-from', type=Path)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    if args.action in {'prepare', 'launch'} and not (args.action == 'launch' and args.directory.exists()):
        if args.catalogue_file:
            catalogue = json.loads(args.catalogue_file.read_text()); reference = str(args.catalogue_file.resolve())
        else:
            if args.catalogue_url != 'https://platform.ai-effect.eu/api/services':
                raise ValueError('For other catalogues, explicitly supply a local --catalogue-file')
            with urllib.request.urlopen(args.catalogue_url, timeout=20) as response: catalogue = json.load(response)
            reference = args.catalogue_url
        profile = prepare(args.directory, catalogue, reference, args.web_port, args.api_port, args.dependencies_from)
        print(json.dumps({'prepared': True, 'directory': profile['directory'], 'metadata_copies': profile['catalogue_count'], 'services_started': False}))
    if args.action in {'start', 'launch'}: start(args.directory, args.api_only, args.open_browser)
    elif args.action == '_seed': seed(args.directory)
    elif args.action == '_serve':
        import uvicorn
        _, profile = read_profile(args.directory)
        uvicorn.run(create_review_app(args.directory), host='127.0.0.1', port=profile['api_port'], log_level='warning', access_log=False)


if __name__ == '__main__':
    def stop(signum, frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try: main()
    except KeyboardInterrupt: pass
    except Exception as error:
        print(str(error), file=sys.stderr); sys.exit(1)
