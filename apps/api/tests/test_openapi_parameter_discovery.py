"""Source-interface onboarding, not Portuguese ML/runtime or owner approval."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from app.db import SessionLocal
from app.models.service import Service
from app.services.parameter_discovery import discover
from test_parameter_onboarding import publisher, review_payload, approve, state  # noqa: F401

PORTAL = Path(__file__).resolve().parents[3]
DOCUMENT = json.loads((PORTAL / 'docs/parameter-onboarding/portugal-source-openapi.json').read_text())
REFERENCE = DOCUMENT['x-ai-effect-source']['reference']


def operation(document, path):
    return next(v['operationId'] for k, v in document['paths'][path].items() if k in {'get', 'post'})


def test_portuguese_source_query_settings_and_training_upload_remain_separate():
    result = discover(DOCUMENT, REFERENCE, 'TrainModel', operation(DOCUMENT, '/train'))
    candidates = {c['name']: c for c in result['candidates']}
    supported = {name: c for name, c in candidates.items() if c['supported']}
    assert set(supported) == {'sequence_len', 'batch_size', 'epochs'}
    assert {name: c['definition']['default'] for name, c in supported.items()} == {'sequence_len': 100, 'batch_size': 1000, 'epochs': 10}
    assert all(c['source_location'] == 'query' for c in supported.values())
    assert all('minimum' not in c['definition'] and 'maximum' not in c['definition'] for c in supported.values())
    assert candidates['uploaded_file']['classification'] == 'data_input'
    assert candidates['model_name']['classification'] == 'data_input'
    assert candidates['user_id']['classification'] == candidates['overwrite']['classification'] == 'operator'
    assert 'default' not in candidates['user_id'] and 'definition' not in candidates['uploaded_file']
    assert not candidates['index_col']['supported']  # dataset-dependent, no invented enumeration
    for c in result['candidates']:
        value = DOCUMENT
        for key in c['source_pointer'][2:].split('/'):
            key = key.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
        assert isinstance(value, dict)
    generated = discover(DOCUMENT, REFERENCE, 'GenerateData', operation(DOCUMENT, '/generate'))
    assert [(c['name'], c['definition']['default']) for c in generated['candidates'] if c['supported']] == [('number_of_examples', 1)]
    assert generated['source_operation']['path'] == '/generate'
    assert generated['source_operation']['method'] == 'GET'


def query_document(parameters, **operation_fields):
    return {'openapi': '3.1.0', 'paths': {'/run/{resource}': {'get': {'operationId': 'Run', 'parameters': parameters, **operation_fields}}}}


def test_path_inheritance_override_local_refs_and_transport_values_are_not_settings():
    count = {'name': 'window', 'in': 'query', 'description': 'Provider-declared prediction window', 'required': True, 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 8}}
    document = query_document([{'$ref': '#/components/parameters/Window'}, {'name': 'session', 'in': 'cookie', 'schema': {'type': 'integer', 'default': 987654321}},
                               {'name': 'resource', 'in': 'path', 'required': True, 'schema': {'type': 'integer', 'default': 123456789}}])
    document['components'] = {'parameters': {'Window': count}}
    document['paths']['/run/{resource}']['parameters'] = [dict(count, schema={'type': 'integer', 'default': 999})]
    result = discover(document, 'provider@revision', 'Run')
    candidate = result['candidates'][0]
    assert candidate['source_pointer'] == '#/components/parameters/Window/schema'
    assert candidate['definition']['required'] and candidate['definition']['description'] == count['description']
    assert 'default' not in candidate['definition'] and candidate['definition']['maximum'] == 8
    assert candidate['supported']
    assert '987654321' not in str(result) and '123456789' not in str(result)
    assert all(not c['supported'] for c in result['candidates'][1:])


@pytest.mark.parametrize('mutation', ['duplicate', 'external_ref', 'invalid_required', 'missing_operation'])
def test_invalid_query_authority_never_fetches_or_guesses(mutation):
    parameter = {'name': 'iterations', 'in': 'query', 'schema': {'type': 'integer', 'default': 2}}
    document = query_document([parameter])
    if mutation == 'duplicate': document['paths']['/run/{resource}']['get']['parameters'].append(deepcopy(parameter))
    if mutation == 'external_ref': parameter.clear(); parameter['$ref'] = 'https://never-fetch.example/parameters'
    if mutation == 'invalid_required': parameter['required'] = 'yes'
    if mutation == 'missing_operation': document['paths']['/run/{resource}']['get']['operationId'] = 'Other'
    with pytest.raises(ValueError): discover(document, 'provider@revision', 'Run')


def test_complex_constraints_and_cross_location_duplicates_stay_unselectable():
    document = query_document([{'name': 'steps', 'in': 'query', 'allowEmptyValue': True, 'schema': {'type': 'integer', 'default': 2}}],
        requestBody={'content': {'application/json': {'schema': {'type': 'object', 'properties': {'steps': {'type': 'integer', 'default': 3}}}}}})
    candidates = discover(document, 'revision', 'Run')['candidates']
    assert len(candidates) == 2 and not any(c['supported'] for c in candidates)
    assert all('multiple input locations' in c['reason'] for c in candidates)
    assert all('default' not in c['definition'] for c in candidates)
    document['paths']['/run/{resource}']['get'].pop('requestBody')
    candidate = discover(document, 'revision', 'Run')['candidates'][0]
    assert not candidate['supported'] and 'allowEmptyValue' in candidate['reason']


def test_unsupported_body_is_visible_without_hiding_valid_query_settings():
    document = query_document([{'name': 'count', 'in': 'query', 'schema': {'type': 'integer'}}],
        requestBody={'content': {'application/octet-stream': {'schema': {'type': 'string', 'format': 'binary'}}}})
    result = discover(document, 'revision', 'Run')
    assert result['candidates'][0]['supported'] and result['limitations']
    document['paths']['/run/{resource}']['get']['requestBody']['content'] = {
        kind: {'schema': {'type': 'object', 'properties': {'ambiguous': {'type': 'boolean'}}}} for kind in ('application/json', 'multipart/form-data')}
    result = discover(document, 'revision', 'Run')
    assert len(result['candidates']) == 1 and 'Multiple' in result['limitations'][0]


@pytest.mark.parametrize('node_code', ['portugal', 'denmark', 'netherlands', 'germany'])
def test_same_provider_flow_persists_source_parameters_for_any_node(publisher, node_code):
    from app.models.user import User
    with SessionLocal() as db:
        db.get(User, 'provider').node = node_code
        service = db.get(Service, 'fixture-onboarded'); service.owner_node = node_code
        db.commit()
    path = '/services/fixture-onboarded/parameter-onboarding'
    response = publisher.post(path + '/discover', json={'document': DOCUMENT, 'source_reference': REFERENCE, 'operation_id': operation(DOCUMENT, '/train')})
    assert response.status_code == 200, response.text
    discovery = response.json()
    parameters = [{'name': c['name'], 'source_pointer': c['source_pointer'], 'definition': c['definition'],
                   'algorithm_mapping': 'Provider review pending: map the configuration key to the declared query input'} for c in discovery['candidates'] if c['supported']]
    response = publisher.post(path + '/review', json={'discovery_revision': discovery['revision'], 'operation_identity': 'urn:test:source-input-review', 'contract_version': '1.0.0',
        'parameters': parameters, 'runtime_support_confirmed': False, 'normal_configuration_tested': False, 'invalid_configuration_tested': False})
    assert response.status_code == 201, response.text
    contract = response.json()
    assert contract['status'] == 'draft'
    saved = publisher.get(path).json()['reviews'][contract['id']]
    assert all(value['source_location'] == 'query' for value in saved['mappings'].values())
    assert not saved['runtime_support_confirmed'] and not saved['evidence_reference']
    assert publisher.get('/services/fixture-onboarded/operation-contract-resolution').json()['contract'] is None


def test_non_control_service_can_save_review_but_cannot_publish_without_connector(publisher):
    payload = review_payload(publisher)
    with SessionLocal() as db:
        service = db.get(Service, 'fixture-onboarded'); service.interface_type = 'grpc'; db.commit()
    response = publisher.post('/services/fixture-onboarded/parameter-onboarding/review', json=payload)
    assert response.status_code == 201, response.text
    approve(publisher)
    response = publisher.post('/operation-contracts/' + response.json()['id'] + '/activate')
    assert response.status_code == 409 and 'connector' in response.text


def test_source_snapshot_is_reproducible_without_loading_service_or_ml():
    root = os.environ.get('WP3_SOURCE_ROOT')
    if not root: pytest.skip('WP3_SOURCE_ROOT required to verify the source interface snapshot')
    source = (Path(root) / 'use-cases/portugal-node-integrated/synthetic_data_generation/main.py').read_bytes().decode()
    assert hashlib.sha256(source.encode()).hexdigest() == DOCUMENT['x-ai-effect-source']['sha256']
    spec = importlib.util.spec_from_file_location('source_input_export', PORTAL / 'deploy/parameter_onboarding/export_fastapi_inputs.py')
    exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
    assert exporter.inspect_inputs(source, REFERENCE, ['/train', '/generate']) == DOCUMENT
    malicious = source.replace('Query(10,', 'Query(__import__("os").getcwd(),')
    with pytest.raises(ValueError): exporter.inspect_inputs(malicious, REFERENCE, ['/train'])


def test_source_query_definitions_reach_manual_and_same_solution_chat_controls(publisher, provider):
    """Synthetic qualification exercises UI authority; no ML/runtime claim."""
    from test_parameter_onboarding import manifest
    from app.main import app
    from app.schemas.solution_assistant import SavedSolutionResponse
    from app.services.design_ai_provider import get_provider
    client = publisher
    value = manifest('source-input-signature-train')
    value['service']['name'] = 'Source-signature training review fixture'
    value['interface'].pop('parameter_schema')
    value['interface'].update(operation_name='TrainModel', openapi=DOCUMENT, openapi_operation_id=operation(DOCUMENT, '/train'))
    response = client.post('/services/import/confirm-manual', json={'manifest': value})
    assert response.status_code == 200, response.text
    base = '/services/source-input-signature-train'
    discovered = client.post(base + '/parameter-onboarding/discover', json={'document': DOCUMENT, 'source_reference': REFERENCE, 'operation_id': operation(DOCUMENT, '/train')}).json()
    parameters = [{'name': c['name'], 'source_pointer': c['source_pointer'], 'definition': c['definition'],
                   'algorithm_mapping': f"Offline source-mapping fixture: configuration.parameters.{c['name']} maps to query.{c['name']}"}
                  for c in discovered['candidates'] if c['supported']]
    contract_response = client.post(base + '/parameter-onboarding/review', json={'discovery_revision': discovered['revision'], 'operation_identity': 'urn:test:source-input-signatures:train', 'contract_version': '1.0.0',
        'parameters': parameters, 'runtime_support_confirmed': True, 'normal_configuration_tested': True, 'invalid_configuration_tested': True,
        'evidence_reference': 'Synthetic qualification fixture only; not actual Portuguese model consumption or owner approval'})
    assert contract_response.status_code == 201, contract_response.text
    contract = contract_response.json()
    from test_parameter_onboarding import login
    login(client, 'admin@example.test')
    assert client.post(base + '/review/approve').status_code == 200
    login(client, 'provider@example.test')
    assert client.post('/operation-contracts/' + contract['id'] + '/activate').status_code == 200
    assert client.post('/auth/login', json={'email': 'designer@example.test', 'password': 'PilotTest12345'}).status_code == 200
    nodes = [{'id': name, 'position': {'x': index * 200, 'y': 0}, 'data': {'node_kind': 'service', 'service': {'id': value['service']['id']},
              'configuration': {'contract_id': contract['id'], 'contract_version': '1.0.0', 'parameters': {'epochs': epochs}}}}
             for index, (name, epochs) in enumerate([('first', 10), ('second', 15)])]
    response = client.post('/solutions', json={'name': 'Source-signature manual and chat fixture', 'nodes': nodes, 'edges': [], 'design_metadata': {'run_input': None}})
    assert response.status_code == 200, response.text
    solution_id = response.json()['id']
    before = client.get('/solutions/' + solution_id).json()
    context = client.get('/design-ai/solutions/' + solution_id).json()
    provider.turn = SavedSolutionResponse(outcome='proposal', message='Review twenty epochs on the second instance', clarification=None, assumptions=[],
                                 solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'second', 'value': '{"epochs":20}'}])
    app.dependency_overrides[get_provider] = lambda: provider
    proposal = client.post('/design-ai/solutions/' + solution_id + '/chat', json={'message': 'Change the second instance to twenty epochs',
        'expected_updated_at': context['expected_updated_at'], 'conversation_revision': context['conversation_revision']})
    assert proposal.status_code == 200, proposal.text
    assert client.get('/solutions/' + solution_id).json() == before
    pending = proposal.json()
    applied = client.post('/design-ai/solutions/' + solution_id + '/apply', json={'expected_updated_at': pending['expected_updated_at'], 'conversation_revision': pending['conversation_revision'], 'proposal_id': pending['pending']['id']})
    assert applied.status_code == 200, applied.text
    saved = client.get('/solutions/' + solution_id).json()
    service_nodes = [n for n in saved['nodes'] if n['data'].get('service')]
    assert [n['data']['configuration']['parameters']['epochs'] for n in service_nodes] == [10, 20]
    compiled = client.post('/workflows/compile', json={'name': saved['name'], 'solution_id': solution_id, 'expected_updated_at': saved['updated_at'], 'run_input': None,
        'nodes': [{'node_id': n['id'], 'service_id': value['service']['id'], 'container_name': 'ignored', 'operation_name': 'TrainModel', 'configuration': n['data']['configuration']} for n in service_nodes], 'edges': []})
    assert compiled.status_code == 200, compiled.text
    assert sorted(c['parameters']['epochs'] for c in compiled.json()['task_configurations'].values()) == [10, 20]
    assert all(c['parameters']['batch_size'] == 1000 and c['parameters']['sequence_len'] == 100 for c in compiled.json()['task_configurations'].values())

    destination = os.environ.get('SOURCE_PARAMETER_EVIDENCE_FILE')
    if destination:
        from datetime import datetime, timezone
        declarations = {}
        for path in ('/train', '/generate'):
            result = discover(DOCUMENT, REFERENCE, 'TrainModel' if path == '/train' else 'GenerateData', operation(DOCUMENT, path))
            declarations[path] = {'operation': result['source_operation'], 'settings': [c for c in result['candidates'] if c['supported']],
                                   'separate_or_unsupported': [{'name': c['name'], 'classification': c['classification'], 'reason': c.get('reason')} for c in result['candidates'] if not c['supported']]}
        Path(destination).write_text(json.dumps({'observed_at': datetime.now(timezone.utc).isoformat(), 'status': 'PASS',
            'scope': 'Source interface discovery and authenticated offline provider/designer API journey; not Portuguese ML execution',
            'source_reference': REFERENCE, 'source_sha256': DOCUMENT['x-ai-effect-source']['sha256'], 'declarations': declarations,
            'manual_then_chat': {'solution_id': solution_id, 'initial_epochs': [10, 15], 'saved_after_explicit_apply': [10, 20],
                'compiled_epochs': sorted(c['parameters']['epochs'] for c in compiled.json()['task_configurations'].values()),
                'proposal_did_not_save': True, 'shared_writer': True, 'provider': 'Injected offline structured response',
                'qualification_and_administrator_approval': 'Synthetic fixture only; not node approval'},
            'limitations': ['Input-signature export, not observed live OpenAPI', 'No actual Portuguese model or sidecar execution',
                'Bounds absent in source remain undeclared; no scientific or provider-approved limits invented',
                'SQLite API walkthrough and rendered component checks; browser and PostgreSQL not verified', 'Production unchanged; no paid provider calls']}, indent=2) + '\n')
