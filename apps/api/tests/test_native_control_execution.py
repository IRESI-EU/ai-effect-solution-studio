"""Opt-in real HTTP/Redis/algorithm manual API journey; not browser acceptance.

WP3_SOURCE_ROOT names the matching isolated WP3 branch. Portal uses the existing
SQLite harness; all approvals and limits are synthetic fixtures, never partner
approval. No network or algorithm doubles are used. Assistant mode injects a structured
response double at the provider boundary; no paid providers are used.
"""
from contextlib import contextmanager, ExitStack
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from uuid import uuid4

import pytest
from app.core.config import settings
from test_parameter_onboarding import publisher, login  # noqa: F401


@contextmanager
def server(app):
    import uvicorn
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    runtime = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False))
    thread = threading.Thread(target=runtime.run, kwargs={'sockets': [sock]}, daemon=True); thread.start()
    deadline = time.monotonic() + 10
    try:
        while not runtime.started and thread.is_alive() and time.monotonic() < deadline: time.sleep(.01)
        assert runtime.started, 'Disposable HTTP server could not start'
        yield port
    finally: runtime.should_exit = True; thread.join(5); sock.close()


@contextmanager
def redis_runtime(directory):
    import redis
    executable = shutil.which('redis-server')
    if not executable:
        package = importlib.util.find_spec('redislite')
        executable = str(Path(package.origin).parent / 'bin/redis-server') if package else None
    if not executable: pytest.skip('Install native Redis or the test-only redislite wheel')
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]; sock.close()
    with (directory / 'redis.log').open('w') as log:
        process = subprocess.Popen([executable, '--bind', '127.0.0.1', '--port', str(port), '--save', '', '--appendonly', 'no', '--dir', str(directory)], stdout=log, stderr=subprocess.STDOUT)
        client = redis.Redis(host='127.0.0.1', port=port, socket_timeout=2)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    if client.ping(): break
                except redis.ConnectionError: time.sleep(.01)
            assert client.ping()
            yield client
        finally: client.close(); process.terminate(); process.wait(timeout=5)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path); value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value; spec.loader.exec_module(value); return value


@pytest.mark.parametrize("edit_mode", ["manual", "assistant"])
def test_manual_onboarding_two_runs_and_owned_results(publisher, tmp_path, monkeypatch, edit_mode):
    root = os.environ.get('WP3_SOURCE_ROOT')
    if not root: pytest.skip('WP3_SOURCE_ROOT required for real cross-repository runtime verification')
    root = Path(root).resolve(); node = root / 'use-cases/denmark-node'
    assert (node / 'common/configuration.py').is_file(), 'Matching WP3 configuration branch is required'
    for path in (root / 'orchestrator/src', node, node / 'services/topology_generator', node / 'services/draw_topology'): monkeypatch.syspath_prepend(str(path))
    from common import concurrent
    from services.control_client import ControlClient
    from services.workflow_engine import WorkflowEngine
    from services.state_store import RedisStateStore
    from services.task_queue import RedisTaskQueue
    from services.blueprint_parser import BlueprintParser
    from services.dockerinfo_parser import DockerInfoParser, ServiceEndpoint
    from services.worker import Worker
    from api.app import OrchestratorAPI
    from app.services.orchestrator_adapter import get_workflow_tasks
    generator = module('portal_native_generator', node / 'services/topology_generator/service.py')
    renderer = module('portal_native_renderer', node / 'services/draw_topology/service.py')
    manager = concurrent.TaskManager(); monkeypatch.setattr(concurrent, 'task_manager', manager)
    output_root = tmp_path / 'outputs'; installed = tmp_path / 'runtime-contract.json'
    for service in (generator, renderer):
        monkeypatch.setattr(service, 'task_manager', manager); monkeypatch.setattr(service, 'DATA_DIR', output_root)
    for key, value in {'SERVICE_PARAMETER_CONTRACT_FILE': str(installed), 'SERVICE_API_KEY': 'test-service-authority', 'ORCHESTRATOR_API_KEY': 'test-orchestrator-authority', 'NO_PROXY': '127.0.0.1,localhost', 'ARTIFACT_BASE_PATH': str(output_root)}.items(): monkeypatch.setenv(key, value)
    monkeypatch.setattr(settings, 'orchestrator_api_key', 'test-orchestrator-authority')
    monkeypatch.setattr(settings, 'orchestrator_services_api_key', 'test-service-authority')
    monkeypatch.setattr(settings, 'design_ai_enabled', edit_mode == 'assistant')
    client = publisher
    with ExitStack() as stack:
        redis = stack.enter_context(redis_runtime(tmp_path))
        gen_port = stack.enter_context(server(concurrent.create_app(generator)))
        render_port = stack.enter_context(server(concurrent.create_app(renderer)))
        engine = WorkflowEngine(RedisStateStore(redis), RedisTaskQueue(redis), redis)
        api_port = stack.enter_context(server(OrchestratorAPI(engine, BlueprintParser(), DockerInfoParser(), redis).create_app()))
        monkeypatch.setattr(settings, 'orchestrator_base_url', f'http://127.0.0.1:{api_port}')
        prefix = 'source-runtime-' + uuid4().hex
        schema = {'type': 'object', 'properties': {
            'allow_hx': {'type': 'boolean', 'title': 'Heat exchangers', 'description': 'Source-runtime fixture', 'default': True},
            'allow_bypass': {'type': 'boolean', 'title': 'Bypasses', 'description': 'Source-runtime fixture', 'default': True},
            'how_many': {'type': 'integer', 'title': 'Topology cap', 'description': 'Synthetic limits, not node approval', 'minimum': 1, 'maximum': 4}}}
        services = []
        for suffix, operation, port in [('gen', 'GenerateTopology', gen_port), ('render', 'RenderTopologies', render_port)]:
            manifest = {'schema_version': '1.0', 'service': {'id': prefix+suffix, 'name': 'Source runtime '+suffix, 'provider': 'Disposable test', 'category': 'Test', 'description': 'Synthetic registration'},
                        'runtime': {'image': 'source:development', 'container_name': 'source-runtime-'+suffix, 'internal_host': '127.0.0.1', 'internal_port': str(port)},
                        'interface': {'type': 'control', 'operation_name': operation, 'input_type': 'JSON', 'output_type': 'JSON'}}
            if suffix == 'gen': manifest['interface']['parameter_schema'] = schema
            response = client.post('/services/import/confirm-manual', json={'manifest': manifest})
            assert response.status_code == 200, response.text
            services.append(response.json())
        gen, rendered = services
        discovery = client.get(f"/services/{gen['id']}/parameter-onboarding").json()['discovery']
        response = client.post(f"/services/{gen['id']}/parameter-onboarding/review", json={
            'discovery_revision': discovery['revision'], 'operation_identity': 'urn:test:source-runtime:generate', 'contract_version': '1.0.0',
            'parameters': [{'name': c['name'], 'source_pointer': c['source_pointer'], 'definition': c['definition'], 'algorithm_mapping': 'Source GenerateTopology enumerator argument'} for c in discovery['candidates']],
            'runtime_support_confirmed': False, 'normal_configuration_tested': False, 'invalid_configuration_tested': False,
            'evidence_reference': ''})
        assert response.status_code == 201, response.text
        contract = response.json()
        # Resolve the onboarding dependency in its real order: save -> install
        # qualification draft -> valid/invalid runtime checks -> attest -> publish.
        export = client.get(f"/operation-contracts/{contract['id']}/qualification-capability")
        assert export.status_code == 200, export.text
        installed.write_text(json.dumps(export.json()))
        monkeypatch.setenv('CONTROL_PARAMETER_QUALIFICATION_MODE','true')
        import requests
        headers = {'Authorization': 'Bearer test-service-authority'}
        qualification_input = tmp_path / 'qualification-input.json'
        qualification_input.write_text(json.dumps({'run_config': {'supplies': ['310-D::CHP'], 'loads': ['716-D::Dumpload']}}))
        config = {'contract_id': contract['id'], 'contract_version': contract['contract_version'], 'operation_identity': contract['operation_identity'],
                  'schema_version': '1.0', 'instance_id': 'qualification', 'parameters': {'allow_hx': True, 'allow_bypass': True, 'how_many': 1}}
        request = {'method': 'GenerateTopology', 'workflow_id': 'wf-qualification', 'task_id': 'qualification-valid',
                   'inputs': [{'protocol': 'file', 'uri': str(qualification_input), 'format': 'json'}], 'configuration': config}
        invalid = json.loads(json.dumps(request)); invalid['task_id'] = 'qualification-invalid'; invalid['configuration']['parameters']['how_many'] = 99
        assert requests.post(f'http://127.0.0.1:{gen_port}/control/execute', headers=headers, json=invalid, timeout=5).status_code == 422
        accepted = requests.post(f'http://127.0.0.1:{gen_port}/control/execute', headers=headers, json=request, timeout=5)
        assert accepted.status_code == 200, accepted.text
        task_id = accepted.json()['task_id']; deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = requests.get(f'http://127.0.0.1:{gen_port}/control/status/{task_id}', headers=headers, timeout=5).json()
            if status['status'] != 'running': break
            time.sleep(.01)
        assert status['status'] == 'complete', status
        artifact = requests.get(f'http://127.0.0.1:{gen_port}/control/output/{task_id}', headers=headers, timeout=5).json()['output']
        qualified = json.loads(Path(artifact['uri']).read_text())
        assert qualified['execution']['algorithm_consumed'] == config['parameters'] and qualified['topology_count'] == 1
        review = client.get(f"/services/{gen['id']}/parameter-onboarding").json()['reviews'][contract['id']]
        confirmed = client.post(f"/services/{gen['id']}/parameter-onboarding/reviews/{contract['id']}/confirm-runtime", json={
            'reviewed_contract_sha256': review['reviewed_contract_sha256'], 'runtime_support_confirmed': True,
            'normal_configuration_tested': True, 'invalid_configuration_tested': True, 'evidence_reference': 'Disposable real source-runtime HTTP qualification; synthetic limits, not partner approval'})
        assert confirmed.status_code == 200, confirmed.text
        login(client, 'admin@example.test')
        for service in services: assert client.post(f"/services/{service['id']}/review/approve").status_code == 200
        login(client, 'provider@example.test')
        assert client.post(f"/operation-contracts/{contract['id']}/activate").status_code == 200
        export = client.get(f"/operation-contracts/{contract['id']}/runtime-capability")
        assert export.status_code == 200, export.text
        installed.write_text(json.dumps(export.json()))
        assert client.post('/auth/login', json={'email': 'designer@example.test', 'password': 'PilotTest12345'}).status_code == 200
        run_input = {'run_config': {'supplies': ['310-D::CHP'], 'loads': ['716-D::Dumpload']}}
        nodes = [{'id': 'generate', 'position': {'x': 0, 'y': 0}, 'data': {'node_kind': 'service', 'service': {'id': gen['id']}, 'configuration': {'contract_id': contract['id'], 'contract_version': '1.0.0', 'parameters': {'how_many': 1}}}},
                 {'id': 'render', 'position': {'x': 200, 'y': 0}, 'data': {'node_kind': 'service', 'service': {'id': rendered['id']}}}]
        edges = [{'id': 'gen-render', 'source': 'generate', 'target': 'render'}]
        response = client.post('/solutions', json={'name': 'Manual native runtime', 'nodes': nodes, 'edges': edges, 'design_metadata': {'run_input': run_input}})
        assert response.status_code == 200, response.text
        saved = client.get('/solutions/' + response.json()['id']).json(); completed = []
        for count in (1, 3):
            if count == 3:
                nodes[0]['data']['configuration']['parameters']['how_many'] = count
                if edit_mode == 'manual':
                    response = client.put(f"/solutions/{saved['id']}", json={'name': saved['name'], 'nodes': nodes, 'edges': edges, 'expected_updated_at': saved['updated_at']})
                    assert response.status_code == 200, response.text
                    saved = response.json()
                else:
                    from app.main import app
                    from app.services.design_ai_provider import get_provider
                    from app.schemas.design_ai import AssistantTurn
                    from conftest import TestProvider
                    offline = TestProvider(AssistantTurn(message='Review a topology cap of three', template_key=None, expected_revision=None, edits=[],
                        solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'generate', 'value': '{"how_many":3}'}]))
                    app.dependency_overrides[get_provider] = lambda: offline
                    base = f"/design-ai/solutions/{saved['id']}"
                    before = client.get(base).json()
                    response = client.post(base + '/chat', json={'message': 'Generate up to three topologies', 'expected_updated_at': before['expected_updated_at'], 'conversation_revision': before['conversation_revision']})
                    assert response.status_code == 200, response.text
                    assert client.get('/solutions/' + saved['id']).json() == saved
                    proposal = response.json()
                    assert client.post(base + '/apply', json={'expected_updated_at': proposal['expected_updated_at'], 'conversation_revision': proposal['conversation_revision'], 'proposal_id': proposal['pending']['id']}).status_code == 200
                    saved = client.get('/solutions/' + saved['id']).json()
                    app.dependency_overrides.pop(get_provider)
            workflow = {'name': saved['name'], 'solution_id': saved['id'], 'expected_updated_at': saved['updated_at'], 'run_input': run_input,
                'nodes': [{'node_id': n['id'], 'service_id': n['data']['service']['id'], 'container_name': 'ignored', 'operation_name': 'GenerateTopology' if n['id'] == 'generate' else 'RenderTopologies',
                           **({'configuration': n['data']['configuration']} if 'configuration' in n['data'] else {})} for n in saved['nodes']], 'edges': [{'source': 'generate', 'target': 'render'}]}
            readiness = client.post('/workflows/runtime-preflight', json=workflow)
            if readiness.status_code != 200:
                import requests
                compiled_response = client.post('/workflows/compile', json=workflow)
                assert compiled_response.status_code == 200, compiled_response.text
                compiled = compiled_response.json()
                checks = requests.post(f'http://127.0.0.1:{api_port}/workflows/check-compatibility',
                    headers={'Authorization': 'Bearer test-orchestrator-authority'}, json={
                    **{k: compiled[k] for k in ('blueprint', 'dockerinfo', 'task_configurations')}, 'services_api_key': 'test-service-authority'})
                native = requests.get(f'http://127.0.0.1:{gen_port}/control/capabilities', headers={'Authorization': 'Bearer test-service-authority'})
                pytest.fail(f'Preflight {readiness.status_code}: {readiness.text}; WP3 {checks.status_code}: {checks.text}; native {native.status_code}: {native.text}')
            assert readiness.json()['status'] == 'ready', readiness.text
            response = client.post('/workflows/submit-to-orchestrator', json=workflow)  # Explicit normal Run.
            assert response.status_code == 200, response.text
            wf = response.json()['workflow_id']
            endpoints = {(k.decode() if isinstance(k, bytes) else k): ServiceEndpoint.model_validate_json(v) for k, v in redis.hgetall(f'endpoints:{wf}').items()}
            Worker(engine, ControlClient(api_key='test-service-authority'), endpoints, poll_interval=.01).run(wf)
            tasks = get_workflow_tasks(wf)['tasks']
            assert len(tasks) == 2 and all(t['status'] == 'completed' for t in tasks), tasks
            snapshot = client.get(f'/workflows/{wf}/submitted-configuration').json()
            instance = next(n for n in snapshot['submitted']['compiled']['solution_studio_metadata']['execution_instances'] if n['instance_id'] == 'generate')
            assert instance['configuration']['parameters']['how_many'] == count
            gen_task = next(t for t in tasks if t['task_id'] == instance['task_id'])
            reference = gen_task['output_refs'][0]; output = json.loads(Path(reference['uri']).read_text())
            assert output['topology_count'] == count and output['execution']['configuration'] == instance['configuration']
            assert output['execution']['algorithm_arguments']['max_results'] == count
            association = next(a for a in engine.get_instance_associations(wf) if a['task_id'] == instance['task_id'])
            assert association['service_task_id'] == output['execution']['service_task_id']
            preview = client.post('/data-references/preview', json={'workflow_id': wf, 'task_id': instance['task_id'], 'protocol': 'file', 'uri': reference['uri'], 'format': 'json'})
            assert preview.status_code == 200 and preview.json()['available'], preview.text
            render_task = next(t for t in tasks if t['task_id'] != instance['task_id'])
            visual = json.loads(Path(render_task['output_refs'][0]['uri']).read_text())
            assert visual['drawing_count'] == count and visual['upstream_execution'] == output['execution']
            evidence = client.get(f'/workflows/{wf}/instance-evidence')
            assert evidence.status_code == 200 and evidence.json()['state'] == 'available', evidence.text
            assert evidence.json()['instances'][0]['algorithm_consumed']['how_many'] == count
            assert evidence.json()['instances'][0]['input_binding_verified'] is True
            completed.append((wf, snapshot, reference['uri'], Path(reference['uri']).read_bytes()))
        first, second = completed
        assert first[0] != second[0] and first[2] != second[2]
        assert Path(first[2]).read_bytes() == first[3]
        assert client.get(f'/workflows/{first[0]}/submitted-configuration').json() == first[1]
        assert client.get(f'/workflows/{first[0]}/instance-evidence').json()['instances'][0]['algorithm_consumed']['how_many'] == 1
        # Corrupt only this disposable test's artifact, then restore it.
        changed = json.loads(first[3]); changed['topology_count'] = 99
        Path(first[2]).write_text(json.dumps(changed))
        assert client.get(f'/workflows/{first[0]}/instance-evidence').json()['instances'][0]['state'] == 'conflicting'
        Path(first[2]).write_bytes(first[3])
        assert client.get(f'/workflows/{first[0]}/instance-evidence').json()['state'] == 'available'
        login(client, 'provider@example.test')
        assert client.get(f'/workflows/{first[0]}/instance-evidence').status_code == 403
        assert client.get(f'/workflows/{first[0]}/submitted-configuration').status_code == 403
        assert client.post('/data-references/preview', json={'workflow_id': first[0], 'task_id': instance['task_id'], 'protocol': 'file', 'uri': first[2]}).status_code == 403
        # Optional sanitized checkpoint from the completed real-runtime run.
        destination = os.environ.get('NATIVE_CONTROL_EVIDENCE_FILE') if edit_mode == 'assistant' else None
        if destination:
            import hashlib
            from datetime import datetime, timezone
            runs = []
            for workflow_id, snapshot, _, raw in completed:
                output = json.loads(raw); execution = output['execution']
                requested = next(n for n in snapshot['submitted']['request']['nodes'] if n['node_id'] == 'generate')['configuration']['parameters']
                runs.append({'workflow_id': workflow_id, 'task_id': execution['task_id'], 'service_task_id': execution['service_task_id'],
                             'requested': requested, 'effective': execution['configuration']['parameters'], 'algorithm_consumed': execution['algorithm_consumed'],
                             'topology_count': output['topology_count'], 'svg_count': output['topology_count'],
                             'parameter_contract_sha256': execution['parameter_contract_sha256'], 'output_sha256': hashlib.sha256(raw).hexdigest()})
            portal_root = Path(__file__).resolve().parents[3]
            source_files = {**{'portal/' + path: hashlib.sha256((portal_root / path).read_bytes()).hexdigest() for path in (
                'apps/api/app/main.py', 'apps/api/app/routers/operation_contracts.py', 'apps/api/app/routers/parameter_onboarding.py',
                'apps/api/app/routers/solution_assistant.py', 'apps/api/app/services/solution_assistant.py', 'apps/api/app/services/solution_editing.py',
                'apps/api/app/services/operation_contract_registry.py', 'apps/api/app/services/design_ai_provider.py',
                'apps/api/app/services/native_instance_evidence.py', 'apps/api/app/services/owned_artifact_preview.py')},
                **{'wp3/' + path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in (
                'use-cases/denmark-node/common/configuration.py', 'use-cases/denmark-node/common/concurrent.py',
                'use-cases/denmark-node/services/topology_generator/service.py', 'use-cases/denmark-node/services/draw_topology/service.py')}}
            Path(destination).write_text(json.dumps({'observed_at': datetime.now(timezone.utc).isoformat(), 'status': 'PASS', 'source_files_sha256': source_files,
                'journey': 'normal authenticated provider/admin/designer API routes -> real HTTP WP3 -> native Redis -> Worker -> real topology enumerator and SVG renderer -> owned result preview and instance evidence',
                'edit_mode': edit_mode, 'provider': 'Explicit offline structured response double; not live model acceptance', 'qualification': 'Saved draft -> exported isolated contract -> real valid/invalid HTTP checks -> provider confirmation -> publication',
                'runs': runs, 'history_after_edit': 'PASS', 'cross_owner_denial': 'PASS', 'artifact_change_detection': 'PASS',
                'limitations': ['Synthetic node approvals and test limits; not Danish owner confirmation', 'Portal SQLite test database; PostgreSQL not verified',
                                'Automated API walkthrough; browser and independent human acceptance not performed', 'Native processes; Docker and production unchanged', 'No paid provider calls']}, indent=2) + '\n')
