"""Real isolated API processes and optional real Next build/proxy; no ML/LLM calls."""
import hashlib
import http.cookiejar
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'deploy/parameter_onboarding/review_workspace.py'
spec = importlib.util.spec_from_file_location('isolated_review_workspace', SCRIPT)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); return sock.getsockname()[1]


def request(client, base, path, body=None):
    value = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers={} if body is None else {'Content-Type': 'application/json'})
    try:
        with client.open(value, timeout=5) as response: return response.status, json.load(response), response.headers
    except urllib.error.HTTPError as response: return response.code, json.load(response), response.headers


def catalogue():
    path = os.environ.get('REVIEW_CATALOGUE_SNAPSHOT')
    if path:
        return [{**row['metadata'], 'id': row['source_id'], 'owner_node': row['owner_node'], 'status': row['source_status']}
                for row in json.loads(Path(path).read_text())]
    return [{'id': 'source-' + owner, 'name': 'Provider-owned ' + owner, 'provider': 'Source catalogue fixture', 'category': 'Review',
             'owner_node': owner, 'status': 'approved', 'lifecycle_status': 'active', 'interface_type': 'control',
             'operation_name': 'TrainModel', 'container_name': 'unqualified', 'image': 'source-declared:unqualified'} for owner in ('portugal', 'denmark')]


def test_review_bootstrap_normal_auth_saved_draft_and_process_boundaries(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://do-not-connect.invalid/protected')
    monkeypatch.setenv('OPENAI_API_KEY', 'sentinel-never-used')
    monkeypatch.setenv('DESIGN_AI_ACCEPTANCE_BUDGET_FILE', '/do-not-open/closed-ledger')
    backup = ROOT / 'local-backups'; backup.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=backup, prefix='workspace-check-') as temp:
        directory = Path(temp) / 'fresh-review'
        profile = module.prepare(directory, catalogue(), 'public-catalogue-review-copy', free_port(), free_port())
        before_credentials = hashlib.sha256((directory / 'credentials.private.json').read_bytes()).hexdigest()
        with pytest.raises(RuntimeError, match='NEW directory'):
            module.prepare(directory, catalogue(), 'not-replaced')
        assert hashlib.sha256((directory / 'credentials.private.json').read_bytes()).hexdigest() == before_credentials
        clean = module.clean_environment(profile)
        assert clean['DATABASE_URL'].startswith('sqlite:///') and clean['OPENAI_API_KEY'] == ''
        assert 'DESIGN_AI_ACCEPTANCE_BUDGET_FILE' not in clean
        assert os.environ['DATABASE_URL'].endswith('/protected')
        assert os.environ['OPENAI_API_KEY'] == 'sentinel-never-used'
        with_web = os.environ.get('REVIEW_TEST_WEB') == '1'
        original = {p: p.read_bytes() for p in (ROOT / 'apps/web/next-env.d.ts', ROOT / 'apps/web/tsconfig.json')}
        with (directory / 'launcher.log').open('w') as log:
            command = [sys.executable, str(SCRIPT), 'start', '--directory', str(directory)] + ([] if with_web else ['--api-only'])
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), urllib.request.ProxyHandler({}))
            api = f"http://127.0.0.1:{profile['api_port']}"
            try:
                module.wait_http(api + '/health', process, expected_profile=profile['id'])
                if with_web:
                    module.wait_http(f"http://127.0.0.1:{profile['web_port']}/login", process, timeout=120)
                    base = f"http://127.0.0.1:{profile['web_port']}/api"
                else: base = api
                accounts = json.loads((directory / 'credentials.private.json').read_text())
                status, user, headers = request(client, base, '/auth/login', {key: accounts['provider_portugal'][key] for key in ('email', 'password')})
                assert status == 200 and user['role'] == 'node_manager', (status, user)
                assert profile['cookie'] in headers.get('set-cookie') and 'ai_effect_session=' not in headers.get('set-cookie')
                status, services, _ = request(client, base, '/services?include_archived=true')
                assert status == 200 and services and all(s['owner_node'] == 'portugal' for s in services)
                assert all(s['status'] == 'pending_review' and not s['interface_contract']['review_source']['runtime_qualified'] for s in services)
                selected = next(s for s in services if s['operation_name'] == 'TrainModel' and s['lifecycle_status'] == 'active')
                path = '/services/' + selected['id'] + '/parameter-onboarding'
                document = json.loads((ROOT / 'docs/parameter-onboarding/portugal-source-openapi.json').read_text())
                status, discovery, _ = request(client, base, path + '/discover', {'document': document, 'source_reference': document['x-ai-effect-source']['reference'], 'operation_id': document['paths']['/train']['post']['operationId']})
                assert status == 200, discovery
                parameters = [{'name': c['name'], 'source_pointer': c['source_pointer'], 'definition': c['definition'], 'algorithm_mapping': 'Review pending: actual runtime query consumption must be qualified'} for c in discovery['candidates'] if c['supported']]
                status, contract, _ = request(client, base, path + '/review', {'discovery_revision': discovery['revision'], 'operation_identity': 'urn:aieffect:review:input-declaration', 'contract_version': '0.1.0', 'parameters': parameters,
                    'runtime_support_confirmed': False, 'normal_configuration_tested': False, 'invalid_configuration_tested': False})
                assert status == 201 and contract['status'] == 'draft', (status, contract)
                assert request(client, base, '/services/' + selected['id'] + '/operation-contract-resolution')[1]['contract'] is None
                for blocked in ['/workflows/submit', '/workflows/submit-to-orchestrator', '/workflows/runtime-preflight', '/services/' + selected['id'] + '/runtime/verify',
                                '/design-ai/solutions/any/chat', '/design-ai/chat', '/design-ai/drafts/any/execute', '/operation-contracts/' + contract['id'] + '/activate', path + '/reviews/' + contract['id'] + '/confirm-runtime']:
                    assert request(client, base, blocked, {})[0] == 409, blocked
                status, config, _ = request(client, base, '/design-ai/config')
                assert status == 200 and config['enabled'] and config['saved_solution_workspace'] and not config['provider_configured']
                status, _, _ = request(client, base, '/auth/login', {key: accounts['provider_denmark'][key] for key in ('email', 'password')})
                assert status == 200 and request(client, base, path)[0] == 403
                assert all(p.read_bytes() == before for p, before in original.items())
                verification = {'status': 'PASS', 'catalogue_metadata_copies': profile['catalogue_count'],
                        'accounts': len(accounts), 'provider_nodes': sorted({a['node'] for a in accounts.values() if a['node']}),
                        'frontend_build_and_proxy': with_web, 'normal_provider_login': True, 'distinct_cookie': True,
                        'discovered': [p['name'] for p in parameters], 'draft_saved': True, 'published_contract': False,
                        'cross_node_ownership_denied': True, 'runtime_publication_execution_chat_blocked': True, 'source_files_preserved': True,
                        'limitations': ['Native processes and SQLite; not PostgreSQL/Docker qualification', 'HTTP proxy checks; no browser acceptance',
                                       'Not installed on the user Windows computer', 'No paid provider calls or ML/runtime execution', 'Production and retained demo unchanged']}
            finally:
                process.send_signal(signal.SIGINT)
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5); pytest.fail('New review process did not stop cleanly')
        module.check_port(profile['api_port'])
        if with_web: module.check_port(profile['web_port'])
        verification['clean_shutdown'] = True
        evidence = os.environ.get('REVIEW_WORKSPACE_EVIDENCE_FILE')
        if evidence: Path(evidence).write_text(json.dumps(verification, indent=2) + '\n')


def test_rejects_retained_ports_before_creating_profile(tmp_path):
    target = tmp_path / 'do-not-create'
    with pytest.raises(ValueError, match='retained demo'):
        module.prepare(target, catalogue(), 'fixture', 23124, 28189)
    assert not target.exists()


def test_cli_prepare_exits_without_starting_services(tmp_path):
    source = tmp_path / 'catalogue.json'; source.write_text(json.dumps(catalogue()))
    directory = tmp_path / 'prepared-only'; web, api = free_port(), free_port()
    result = subprocess.run([sys.executable, str(SCRIPT), 'prepare', '--directory', str(directory), '--catalogue-file', str(source),
        '--web-port', str(web), '--api-port', str(api)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=25)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)['services_started'] is False
    module.check_port(web); module.check_port(api)
