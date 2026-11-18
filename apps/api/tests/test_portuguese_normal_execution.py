"""Normal role/API Run through real HTTP WP3/Redis/Control and owned CSV results.

The unchanged Portuguese source API executes at the ML boundary with an explicit
DGAN dependency double. Fixture approvals/bounds are not partner acceptance.
Assistant mode substitutes only the assistant response. No paid calls.
"""
import base64
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

import pytest
import requests
from app.core.config import settings
from test_parameter_onboarding import publisher, login
from test_native_control_execution import server, redis_runtime
from test_selected_input import csv_input


@pytest.fixture
def portuguese(tmp_path, monkeypatch):
    root = os.environ.get('WP3_SOURCE_ROOT')
    if not root: pytest.skip('WP3_SOURCE_ROOT required for cross-repository HTTP journey')
    path = Path(root).resolve() / 'tests/test_portuguese_configured_runtime.py'
    if not path.is_file(): pytest.skip('Matching Portuguese configured runtime source required')
    pytest.importorskip('pandas')
    spec = importlib.util.spec_from_file_location('normal_portuguese_fixture', path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    values = module.runtime.__wrapped__(tmp_path, monkeypatch)
    runtime = next(values); runtime.module = module
    try: yield runtime
    finally: next(values, None)


@pytest.mark.parametrize('edit_mode', ['manual', 'assistant'])
def test_normal_saved_csv_run_to_owned_http_results(publisher, portuguese, monkeypatch, tmp_path, edit_mode):
    root = Path(os.environ['WP3_SOURCE_ROOT']).resolve()
    monkeypatch.syspath_prepend(str(root / 'orchestrator/src'))
    from services.control_client import ControlClient
    from services.workflow_engine import WorkflowEngine
    from services.state_store import RedisStateStore
    from services.task_queue import RedisTaskQueue
    from services.blueprint_parser import BlueprintParser
    from services.dockerinfo_parser import DockerInfoParser, ServiceEndpoint
    from services.worker import Worker
    from api.app import OrchestratorAPI
    from app.services.orchestrator_adapter import get_workflow_tasks
    from app.db import SessionLocal
    from app.models.user import User
    from app.services.parameter_values import parameter_contract_digest
    # A test node-manager account follows real ownership checks, not auth overrides.
    with SessionLocal() as db:
        db.get(User, 'provider').node = 'portugal'; db.commit()
    client = publisher
    monkeypatch.setenv('ORCHESTRATOR_API_KEY', 'disposable-orchestrator-key')
    monkeypatch.setenv('NO_PROXY', '127.0.0.1,localhost')
    monkeypatch.setattr(settings, 'orchestrator_api_key', 'disposable-orchestrator-key')
    monkeypatch.setattr(settings, 'orchestrator_services_api_key', portuguese.env['SERVICE_API_KEY'])
    monkeypatch.setattr(settings, 'portuguese_evidence_root', '')
    monkeypatch.setattr(settings, 'aie18_evidence_root', '')
    monkeypatch.setattr(settings, 'aie37_qualification', False)
    with ExitStack() as stack:
        redis = stack.enter_context(redis_runtime(tmp_path))
        port = stack.enter_context(server(portuguese.module.control.create_app(portuguese.handlers)))
        base = f'http://127.0.0.1:{port}'; portuguese.connector.self_url = base
        engine = WorkflowEngine(RedisStateStore(redis), RedisTaskQueue(redis), redis)
        api_port = stack.enter_context(server(OrchestratorAPI(engine, BlueprintParser(), DockerInfoParser(), redis).create_app()))
        monkeypatch.setattr(settings, 'orchestrator_base_url', f'http://127.0.0.1:{api_port}')
        targets = tmp_path / 'targets.private.json'
        targets.write_text(json.dumps({'targets': [{'base_url': base, 'token': portuguese.env['SERVICE_API_KEY'], 'runtime_destination': settings.orchestrator_base_url}]}))
        monkeypatch.setattr(settings, 'owned_control_targets_file', str(targets))
        prefix = 'normal-' + uuid4().hex
        reviewed = []; capabilities = {'capability_schema_version': '1.0', 'transports': ['http-parameters-v1'], 'qualification_only': True, 'operations': []}
        portuguese.connector.qualification = True
        installed = tmp_path / 'contracts/reviewed.json'
        for method, inputs, outputs, names in [('TrainModel', 'CSV', 'JSON', ['epochs', 'batch_size', 'sequence_len']), ('GenerateData', 'JSON', 'CSV', ['number_of_examples'])]:
            props = {name: {'type': 'integer', 'title': name, 'description': 'Software fixture limits; not owner approval', 'minimum': 1, 'maximum': 32} for name in names}
            manifest = {'schema_version': '1.0', 'service': {'id': prefix + method, 'name': 'Software fixture ' + method, 'provider': 'Disposable test node', 'category': 'Test'},
                        'runtime': {'image': 'fixture:source', 'container_name': prefix + '-' + method.lower(), 'internal_host': '127.0.0.1', 'internal_port': str(port)},
                        'interface': {'type': 'control', 'operation_name': method, 'input_type': inputs, 'output_type': outputs, 'parameter_schema': {'type': 'object', 'properties': props, 'required': names}}}
            response = client.post('/services/import/confirm-manual', json={'manifest': manifest}); assert response.status_code == 200, response.text
            service = response.json(); discovery = client.get('/services/' + service['id'] + '/parameter-onboarding').json()['discovery']
            payload = {'discovery_revision': discovery['revision'], 'operation_identity': 'urn:software-fixture:' + prefix + method, 'contract_version': '1.0.0',
                       'parameters': [{'name': c['name'], 'source_pointer': c['source_pointer'], 'definition': c['definition'], 'algorithm_mapping': 'Source API query ' + c['name']} for c in discovery['candidates']],
                       'runtime_support_confirmed': False, 'normal_configuration_tested': False, 'invalid_configuration_tested': False, 'evidence_reference': ''}
            response = client.post('/services/' + service['id'] + '/parameter-onboarding/review', json=payload); assert response.status_code == 201, response.text
            contract = response.json(); export = client.get('/operation-contracts/' + contract['id'] + '/qualification-capability'); assert export.status_code == 200
            capabilities['operations'].extend(export.json()['operations']); installed.write_text(json.dumps(capabilities))
            reviewed.append((service, contract))
        headers = {'Authorization': 'Bearer ' + portuguese.env['SERVICE_API_KEY']}
        selected = csv_input('datetime,value\n2026-01-01,1\n2026-01-02,2\n')
        ref = {'protocol': 'inline', 'format': 'csv', 'uri': base64.b64encode(selected['$ai_effect_input']['content'].encode()).decode()}
        def qualify(index, values, reference):
            service, contract = reviewed[index]
            config = {'contract_id': contract['id'], 'contract_version': '1.0.0', 'operation_identity': contract['operation_identity'], 'schema_version': '1.0', 'instance_id': 'qualification-' + str(index), 'parameters': values}
            body = {'method': service['operation_name'], 'workflow_id': 'wf-new-qualification', 'task_id': 'qualification-' + str(index), 'inputs': [reference], 'configuration': config}
            bad = deepcopy(body); bad['configuration']['parameters'][next(iter(values))] = True
            before = len(portuguese.calls)
            assert requests.post(base + '/control/execute', json=bad, headers=headers, timeout=5).status_code == 422
            assert len(portuguese.calls) == before
            response = requests.post(base + '/control/execute', json=body, headers=headers, timeout=5); assert response.status_code == 200, response.text
            physical = response.json()['task_id']; deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                receipt = requests.get(base + '/control/receipt/' + physical, headers=headers, timeout=5).json()
                if receipt['state'] not in {'queued', 'running'}: break
                time.sleep(.01)
            assert receipt['state'] == 'complete', receipt
            review = client.get('/services/' + service['id'] + '/parameter-onboarding').json()['reviews'][contract['id']]
            confirmed = client.post('/services/' + service['id'] + '/parameter-onboarding/reviews/' + contract['id'] + '/confirm-runtime', json={
                'reviewed_contract_sha256': review['reviewed_contract_sha256'], 'runtime_support_confirmed': True, 'normal_configuration_tested': True, 'invalid_configuration_tested': True,
                'evidence_reference': 'Source API plus explicit DGAN double; software fixture approval only'})
            assert confirmed.status_code == 200, confirmed.text
            return receipt['output']
        model = qualify(0, {'epochs': 1, 'batch_size': 16, 'sequence_len': 4}, ref)
        qualify(1, {'number_of_examples': 2}, model)
        login(client, 'admin@example.test')
        for service, _ in reviewed: assert client.post('/services/' + service['id'] + '/review/approve').status_code == 200
        login(client, 'provider@example.test')
        capabilities.pop('qualification_only'); capabilities['operations'] = []
        for _, contract in reviewed:
            assert client.post('/operation-contracts/' + contract['id'] + '/activate').status_code == 200
            export = client.get('/operation-contracts/' + contract['id'] + '/runtime-capability'); assert export.status_code == 200
            capabilities['operations'].extend(export.json()['operations'])
        installed.write_text(json.dumps(capabilities)); portuguese.connector.qualification = False
        assert client.post('/auth/login', json={'email': 'designer@example.test', 'password': 'PilotTest12345'}).status_code == 200
        nodes = [{'id': label, 'position': {'x': index * 220, 'y': 0}, 'data': {'node_kind': 'service', 'service': {'id': service['id']},
                  'configuration': {'contract_id': contract['id'], 'contract_version': '1.0.0', 'parameters': {'epochs': 1, 'batch_size': 16, 'sequence_len': 4} if index == 0 else {'number_of_examples': 2}}}}
                 for index, ((service, contract), label) in enumerate(zip(reviewed, ['train', 'generate']))]
        edges = [{'id': 'train-generate', 'source': 'train', 'target': 'generate'}]
        saved = client.post('/solutions', json={'name': 'Normal selected CSV', 'nodes': nodes, 'edges': edges, 'design_metadata': {'run_input': selected}})
        assert saved.status_code == 200, saved.text
        saved = client.get('/solutions/' + saved.json()['id']).json(); runs = []
        for epochs, sequences in [(1, 2), (2, 3)]:
            if epochs == 2:
                if edit_mode == 'manual':
                    nodes = deepcopy(saved['nodes']); nodes[0]['data']['configuration']['parameters']['epochs'] = epochs; nodes[1]['data']['configuration']['parameters']['number_of_examples'] = sequences
                    response = client.put('/solutions/' + saved['id'], json={'nodes': nodes, 'expected_updated_at': saved['updated_at']}); assert response.status_code == 200, response.text
                else:
                    from app.main import app
                    from app.services.design_ai_provider import get_provider
                    from app.schemas.design_ai import AssistantTurn
                    from conftest import TestProvider
                    provider = TestProvider(AssistantTurn(message='Review changed settings', edits=[], expected_revision=None, template_key=None, solution_edits=[
                        {'kind': 'set_node_parameters', 'node_id': 'train', 'value': '{"epochs":2}'}, {'kind': 'set_node_parameters', 'node_id': 'generate', 'value': '{"number_of_examples":3}'}]))
                    app.dependency_overrides[get_provider] = lambda: provider
                    route = '/design-ai/solutions/' + saved['id']; before = client.get(route).json()
                    proposed = client.post(route + '/chat', json={'message': 'Use two epochs and generate three sequences', 'expected_updated_at': before['expected_updated_at'], 'conversation_revision': before['conversation_revision']})
                    assert proposed.status_code == 200, proposed.text
                    proposal = proposed.json(); assert client.get('/solutions/' + saved['id']).json() == saved
                    response = client.post(route + '/apply', json={'expected_updated_at': proposal['expected_updated_at'], 'conversation_revision': proposal['conversation_revision'], 'proposal_id': proposal['pending']['id']})
                    assert response.status_code == 200, response.text
                    assert '$ai_effect_input' not in json.dumps(provider.contexts)
                    app.dependency_overrides.pop(get_provider)
                saved = client.get('/solutions/' + saved['id']).json()
            assert saved['design_metadata']['run_input'] == selected
            payload = {'name': saved['name'], 'solution_id': saved['id'], 'expected_updated_at': saved['updated_at'], 'run_input': selected,
                       'nodes': [{'node_id': n['id'], 'service_id': n['data']['service']['id'], 'container_name': 'ignored', 'operation_name': reviewed[i][0]['operation_name'], 'configuration': n['data']['configuration']} for i,n in enumerate(saved['nodes'])],
                       'edges': [{'source': 'train', 'target': 'generate'}]}
            if not runs:
                original = portuguese.connector.capabilities
                def old_capabilities():
                    document = original()
                    for op in document['operations']: op.pop('input_transports', None)
                    return document
                with monkeypatch.context() as old_runtime:
                    old_runtime.setattr(portuguese.connector, 'capabilities', old_capabilities)
                    count = len(portuguese.calls)
                    assert client.post('/workflows/runtime-preflight', json=payload).status_code == 409
                    assert client.post('/workflows/submit-to-orchestrator', json=payload).status_code == 409
                    assert len(portuguese.calls) == count
            ready = client.post('/workflows/runtime-preflight', json=payload); assert ready.status_code == 200 and ready.json()['status'] == 'ready', ready.text
            before_dispatch = len(portuguese.calls)
            assert before_dispatch == 2 + 2 * len(runs)  # qualification plus only explicit earlier Runs
            changed = deepcopy(payload); changed['run_input'] = csv_input('x\n999\n')
            assert client.post('/workflows/submit-to-orchestrator', json=changed).status_code == 409
            assert len(portuguese.calls) == before_dispatch
            response = client.post('/workflows/submit-to-orchestrator', json=payload); assert response.status_code == 200, response.text
            wf = response.json()['workflow_id']; endpoints = {(k.decode() if isinstance(k, bytes) else k): ServiceEndpoint.model_validate_json(v) for k,v in redis.hgetall('endpoints:' + wf).items()}
            Worker(engine, ControlClient(api_key=portuguese.env['SERVICE_API_KEY']), endpoints, poll_interval=.01).run(wf)
            tasks = get_workflow_tasks(wf)['tasks']; assert len(tasks) == 2 and all(t['status'] == 'completed' for t in tasks), tasks
            snapshot = client.get('/workflows/' + wf + '/submitted-configuration').json()
            instance = next(n for n in snapshot['submitted']['compiled']['solution_studio_metadata']['execution_instances'] if n['instance_id'] == 'generate')
            task = next(t for t in tasks if t['task_id'] == instance['task_id'])
            preview = client.post('/data-references/preview', json={'workflow_id': wf, 'task_id': task['task_id'], **task['output_refs'][0]})
            assert preview.status_code == 200 and preview.json()['available'], preview.text
            assert preview.json()['evidence']['summary'] == {'observed_sequence_count': sequences, 'csv_data_rows': sequences * 4}
            evidence = client.get('/workflows/' + wf + '/instance-evidence').json(); assert evidence['state'] == 'available', evidence
            assert all(p['evidence_level'] == 'authenticated_runtime_receipt' and p['input_references_verified'] and 'algorithm_consumed' not in p for p in evidence['instances'])
            train_proof = next(p for p in evidence['instances'] if p['instance_id'] == 'train'); assert train_proof['delivered_parameters']['epochs'] == epochs and train_proof['input_content_verified'] is True
            runs.append({'workflow_id': wf, 'snapshot': snapshot, 'preview': preview.json(), 'evidence': evidence})
        assert runs[0]['workflow_id'] != runs[1]['workflow_id']
        assert client.get('/workflows/' + runs[0]['workflow_id'] + '/submitted-configuration').json() == runs[0]['snapshot']
        assert client.get('/workflows/' + runs[0]['workflow_id'] + '/instance-evidence').json() == runs[0]['evidence']
        with SessionLocal() as db:
            user = db.get(User, 'other'); user.password_hash = __import__('app.core.security', fromlist=['hash_password']).hash_password('OtherDesigner12345'); db.commit()
        assert client.post('/auth/login', json={'email': 'other@example.test', 'password': 'OtherDesigner12345'}).status_code == 200
        assert client.get('/workflows/' + runs[0]['workflow_id'] + '/instance-evidence').status_code == 403
        assert client.get('/solutions/' + saved['id']).status_code == 403
        if os.environ.get('AIE_NORMAL_CSV_EVIDENCE'):
            destination = Path(os.environ['AIE_NORMAL_CSV_EVIDENCE']); destination.mkdir(parents=True, exist_ok=True)
            (destination / (edit_mode + '.json')).write_text(json.dumps({'boundary': 'normal authenticated API -> real HTTP WP3/Redis/Worker/Control/source API -> owned HTTP results',
                'algorithm_double': True, 'assistant_double': edit_mode == 'assistant', 'fixture_limits_approvals': True, 'browser_acceptance': False,
                'runs': [{'workflow_id': r['workflow_id'], 'delivered': r['evidence']['instances'][0]['delivered_parameters'], 'csv': r['preview']['evidence']['summary'], 'output_sha256': r['preview']['evidence']['output_sha256']} for r in runs],
                'history_unchanged': True, 'cross_owner_denied': True, 'changed_input_denied_before_dispatch': True, 'paid_calls': 0}, indent=2) + '\n')
