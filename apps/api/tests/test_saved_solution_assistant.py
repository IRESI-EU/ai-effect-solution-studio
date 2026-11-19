"""Ordinary saved-solution API journeys. Responses are explicit offline doubles;
these tests make no paid calls and do not establish live model acceptance.
"""
from copy import deepcopy
import json

import pytest

from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models.design_ai import DesignDraft
from app.models.execution_submission import ExecutionSubmission
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services.design_ai_provider import get_provider
from conftest import TestProvider
from test_instance_parameters import configured, node, workflow  # noqa: F401
from test_capability_bindings import bound, SLOT  # noqa: F401


def saved(client, nodes=None):
    response = client.post('/solutions', json={'name': 'One saved solution', 'nodes': nodes or [node('first'), node('second')], 'edges': [], 'design_metadata': {'run_input': {'selected': 'private-input-body'}}})
    assert response.status_code == 200, response.text
    return client.get('/solutions/' + response.json()['id']).json()


def scope(solution): return '/design-ai/solutions/' + solution['id']

def turn(edits=None, message='Review these changes'):
    return AssistantTurn(message=message, template_key=None, expected_revision=None, edits=[], solution_edits=edits or [])


def chat(client, solution, provider, edits=None, message='Please edit my solution'):
    provider.turn = turn(edits)
    before = client.get(scope(solution)).json()
    return client.post(scope(solution) + '/chat', json={
        'message': message, 'expected_updated_at': before['expected_updated_at'], 'conversation_revision': before['conversation_revision']})


def apply(client, solution, state):
    return client.post(scope(solution) + '/apply', json={key: state[key] for key in ('expected_updated_at', 'conversation_revision')} | {'proposal_id': state['pending']['id']})


def test_chat_review_apply_manual_reload_undo_and_legacy_isolation(configured, provider):
    solution = saved(configured)
    proposed = chat(configured, solution, provider, [{'kind': 'set_node_parameters', 'node_id': 'second', 'value': '{"seed":43}'}])
    assert proposed.status_code == 200, proposed.text
    state = proposed.json()
    assert configured.get('/solutions/' + solution['id']).json() == solution
    assert 'private-input-body' not in json.dumps(provider.contexts)
    assert provider.contexts[-1]['mode'] == 'saved_solution'
    assert 'internal_host' not in json.dumps(provider.contexts)
    # Legacy draft APIs cannot list or interpret canonical conversations as graphs.
    assert configured.get('/design-ai/drafts').json() == []
    with SessionLocal() as db:
        row = db.query(DesignDraft).one(); identifier = row.id
        assert row.state['solution_id'] == solution['id'] and 'design' not in row.state
        assert db.query(ExecutionSubmission).count() == 0
    assert configured.get('/design-ai/drafts/' + identifier).status_code == 404
    response = apply(configured, solution, state)
    assert response.status_code == 200, response.text
    changed = configured.get('/solutions/' + solution['id']).json()
    assert changed['id'] == solution['id']
    assert [n['data']['configuration']['parameters']['seed'] for n in changed['nodes'] if n['data'].get('service')] == [42, 43]
    compiled = configured.post('/workflows/compile', json=workflow(changed))
    assert compiled.status_code == 200, compiled.text
    assert [p['parameters']['seed'] for p in compiled.json()['task_configurations'].values()] == [42, 43]
    assert apply(configured, solution, state).status_code == 409
    state = response.json()
    undone = configured.post(scope(solution) + '/undo', json={key: state[key] for key in ('expected_updated_at', 'conversation_revision')})
    assert undone.status_code == 200, undone.text
    restored = configured.get('/solutions/' + solution['id']).json()
    assert restored['nodes'] == solution['nodes'] and restored['design_metadata'] == solution['design_metadata']
    assert not undone.json()['can_undo']


def test_rejection_failure_and_manual_edit_preserve_prior_proposal(configured, provider):
    solution = saved(configured)
    first = chat(configured, solution, provider, [{'kind': 'rename', 'value': 'Reviewed proposal'}]).json()
    for edits in ([{'kind': 'set_node_parameters', 'node_id': 'second', 'value': '{"seed":99}'}],
                  [{'kind': 'add_service', 'value': '{"service_id":"invented","local_ref":"new"}'}],
                  [{'kind': 'set_node_parameters', 'node_id': 'missing', 'value': '{"seed":43}'}]):
        response = chat(configured, solution, provider, edits)
        assert response.status_code in (409, 422), response.text
        assert response.json()['detail']['stage'] == 'application_validation'
        assert configured.get(scope(solution)).json() == first
    # Provider failure does not discard a proposal the designer already reviewed.
    provider.error = ValueError('synthetic schema failure')
    response = chat(configured, solution, provider)
    assert response.status_code == 502
    assert configured.get(scope(solution)).json() == first
    provider.error = None
    clarified = chat(configured, solution, provider, message='Explain that proposal').json()
    assert clarified['pending'] == first['pending']
    assert provider.contexts[-1]['pending_proposal']==first['pending']
    manual = configured.put('/solutions/' + solution['id'], json={'name': 'Manual changed', 'expected_updated_at': solution['updated_at']})
    assert manual.status_code == 200, manual.text
    current = configured.get(scope(solution)).json()
    assert apply(configured, solution, current).status_code == 409
    assert configured.get('/solutions/' + solution['id']).json()['name'] == 'Manual changed'


def test_authorisation_profiles_archived_and_cross_site(configured, provider, monkeypatch):
    solution = saved(configured)
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, 'other')
        assert configured.get(scope(solution)).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    version = {'expected_updated_at': solution['updated_at'], 'conversation_revision': 0, 'message': 'Rename'}
    assert configured.post(scope(solution) + '/chat', json=version, headers={'sec-fetch-site': 'cross-site'}).status_code == 403
    monkeypatch.setattr(settings, 'design_ai_restricted_beta', True)
    assert configured.get(scope(solution)).status_code == 403
    monkeypatch.setattr(settings, 'design_ai_restricted_beta', False)
    assert configured.put('/solutions/' + solution['id'], json={'status': 'archived', 'expected_updated_at': solution['updated_at']}).status_code == 200
    assert configured.post(scope(solution) + '/chat', json=version).status_code == 409
    assert not provider.contexts


def test_manual_input_is_part_of_reviewed_execution(configured, monkeypatch):
    import app.main as main
    solution = saved(configured)
    monkeypatch.setattr(main, 'run_runtime_preflight', lambda *a: pytest.fail('Input drift must fail before preflight'))
    response = configured.post('/workflows/submit-to-orchestrator', json=workflow(solution) | {'run_input': {'selected': 'different'}})
    assert response.status_code == 409 and 'input differs' in response.text
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count() == 0


def test_three_step_catalogue_proposal_uses_declared_io_and_same_compile(bound, provider):
    client, payload = bound
    with SessionLocal() as db:
        source = db.get(OperationContract, 'source')
        # Independent fixtures declared by the synthetic provider, not inferred JSON compatibility.
        operation = 'ActualC'; service = db.get(Service, 'portugal-' + operation)
        db.add(OperationContract(id='middle', service_id=service.id, status='active', operation_identity='urn:test:middle', runtime_operation_name=operation,
            contract_version='1.0.0', schema_version='1.0', source_kind='manual', definition={
                'operation_role': 'transformer', 'binding_transport': 'whole-output-v1',
                'inputs': [{**SLOT, 'required': True, 'source_requirement': 'upstream_operation'}], 'outputs': [SLOT]}))
        db.commit()
    response = client.post('/solutions', json={'name': 'New connected design', 'nodes': [], 'edges': [], 'design_metadata': {'run_input': None}})
    solution = response.json()
    edits = [{'kind': 'add_service', 'value': json.dumps({'service_id': sid, 'local_ref': ref})}
             for sid, ref in [('dutch-ConfigureAndSynthesize', 'start'), ('portugal-ActualC', 'middle'), ('dutch-RunBenchmark', 'finish')]]
    edits += [{'kind': 'connect', 'value': json.dumps({'source': a, 'target': b, 'source_slot': 'grid', 'target_slot': 'grid'})} for a, b in [('start', 'middle'), ('middle', 'finish')]]
    proposal = chat(client, solution, provider, edits)
    assert proposal.status_code == 200, proposal.text
    assert len(proposal.json()['pending']['changes']) == 6
    assert proposal.json()['pending']['changes'][-1]['action']=='workflow_boundaries'
    assert client.get('/solutions/' + solution['id']).json()['nodes'] == []
    result = apply(client, solution, proposal.json())
    assert result.status_code == 200, result.text
    saved_solution = client.get('/solutions/' + solution['id']).json()
    assert len(saved_solution['nodes']) == 5 and len(saved_solution['edges']) == 4
    from test_capability_bindings import workflow as bound_workflow
    compiled = client.post('/workflows/compile', json=bound_workflow(saved_solution))
    assert compiled.status_code == 200, compiled.text
    assert compiled.json()['solution_studio_metadata']['capability_bindings']['status'] == 'verified'
    # Replace with a real service whose I/O lacks a declared contract: reject atomically.
    target = saved_solution['nodes'][1]['id']
    response = chat(client, saved_solution, provider, [{'kind': 'replace_service', 'node_id': target, 'value': '{"service_id":"portugal-ActualD"}'}])
    assert response.status_code == 422, response.text
    assert client.get('/solutions/' + solution['id']).json() == saved_solution


def test_provider_race_and_undo_never_overwrite_manual_writes(configured, provider):
    solution = saved(configured)
    initial = chat(configured, solution, provider, [{'kind': 'rename', 'value': 'Apply this'}]).json()
    applied = apply(configured, solution, initial).json()
    current = configured.get('/solutions/' + solution['id']).json()
    manual = configured.put('/solutions/' + solution['id'], json={'name': 'Manual wins', 'expected_updated_at': current['updated_at']}).json()
    view = configured.get(scope(solution)).json()
    assert not view['can_undo']
    assert configured.post(scope(solution) + '/undo', json={key: view[key] for key in ('expected_updated_at', 'conversation_revision')}).status_code == 409
    class RacingProvider:
        async def respond(self, context):
            import anyio
            response = await anyio.to_thread.run_sync(lambda: configured.put('/solutions/' + solution['id'], json={'name': 'Changed during request', 'expected_updated_at': manual['updated_at']}))
            assert response.status_code == 200, response.text
            return turn([{'kind': 'rename', 'value': 'Stale model suggestion'}])
    app.dependency_overrides[get_provider] = RacingProvider
    response = configured.post(scope(solution) + '/chat', json={'message': 'Rename', **{key: view[key] for key in ('expected_updated_at', 'conversation_revision')}})
    assert response.status_code == 409, response.text
    assert configured.get('/solutions/' + solution['id']).json()['name'] == 'Changed during request'


def test_apply_rechecks_catalogue_authority_and_undo_rechecks_registry(configured, provider):
    solution = saved(configured)
    proposal = chat(configured, solution, provider, [{"kind": "set_node_parameters", "node_id": "second", "value": '{"seed":43}'}]).json()
    with SessionLocal() as db:
        service = db.get(Service, "dutch-ConfigureAndSynthesize"); service.image = "different:runtime"; db.commit()
    response = apply(configured, solution, proposal)
    assert response.status_code == 409 and "Catalogue settings changed" in response.text
    unchanged = configured.get('/solutions/' + solution['id']).json()
    assert unchanged['updated_at'] == solution['updated_at']
    assert [n['data']['configuration'] for n in unchanged['nodes']] == [n['data']['configuration'] for n in solution['nodes']]


def test_new_saved_input_declaration_also_pins_unconfigured_graph(environment, monkeypatch):
    import app.main as main
    response = environment.post('/solutions', json={"name": "Declared input", "nodes": [{"id": "one", "data": {"service": {"id": "dutch-RunBenchmark"}}}], "edges": [], "design_metadata": {"run_input": None}})
    solution = response.json()
    monkeypatch.setattr(main, 'run_runtime_preflight', lambda *a: pytest.fail('Graph drift must fail before preflight'))
    workflow_request = {"name": solution["name"], "solution_id": solution["id"], "expected_updated_at": solution["updated_at"], "run_input": None,
        "nodes": [{"node_id": "one", "service_id": "germany-ProvideData", "container_name": "ignored", "operation_name": "ignored"}], "edges": []}
    result = environment.post('/workflows/submit-to-orchestrator', json=workflow_request)
    assert result.status_code == 409 and "Submitted instances" in result.text
