"""OFFLINE fixtures only: schema/adapter/state checks, never model intent evidence.

Behaviour and permitted alternatives were fixed first in
docs/SAVED_SOLUTION_CONVERSATION_EVALUATION_2026-11-19.md.
"""
import asyncio
from copy import deepcopy
import json
import logging
import sqlite3

import httpx
from openai import AsyncOpenAI
from pydantic import ValidationError
import pytest

from app.core.config import settings
from app.db import SessionLocal
from app.models.execution_submission import ExecutionSubmission
from app.models.operation_contract import OperationContract
from app.schemas.design_ai import AssistantTurn
from app.schemas.solution_assistant import SavedSolutionResponse, as_assistant_turn
from app.services import design_ai_provider, provider_evidence
from test_saved_solution_assistant import bound, configured, saved, node, scope, turn, apply  # noqa: F401
from test_assistant_journey import send


def response(outcome='answer', **values):
    return {'outcome': outcome, 'message': 'Explicit offline response fixture',
            'clarification': None, 'solution_edits': [], 'assumptions': [], 'edit_base': ({'kind':'saved','expected_updated_at':'FIXTURE-BIND-BEFORE-SEND','conversation_revision':0,'proposal_id':None,'candidate_sha256':None} if outcome=='proposal' else None), **values}


@pytest.mark.parametrize('bad', [
    response(message=' '), response(outcome='unknown'), response(clarification='Which copy?'),
    response('clarification'), response('clarification', clarification=' '),
    response('clarification', clarification='Which?', solution_edits=[{'kind': 'rename', 'value': 'No'}]),
    response('proposal'), response('proposal', clarification='Which?', solution_edits=[{'kind': 'rename', 'value': 'No'}]),
    response('unsupported', solution_edits=[{'kind': 'rename', 'value': 'No'}]),
    response(assumptions=['A silent choice']), response(template_key='legacy-authority'),
    response(recommended_seed=42), response(solution_edits=[{'kind': 'run', 'value': 'dispatch'}]),
    response('proposal', solution_edits=[{'kind': 'rename', 'value': 'OK'}], assumptions=[' ']),
    response('proposal', solution_edits=[{'kind': 'rename', 'value': 'OK'}], assumptions='not-a-list'),
])
def test_focused_schema_rejects_conflicting_contents_and_legacy_authority(bad):
    with pytest.raises(ValidationError):
        SavedSolutionResponse.model_validate(bad)


@pytest.mark.parametrize('outcome', ['answer', 'clarification', 'proposal', 'unsupported'])
def test_explicit_adapter_has_no_legacy_or_execution_authority(outcome):
    value = response(outcome)
    if outcome == 'clarification': value['clarification'] = 'Which displayed copy?'
    if outcome == 'proposal': value['solution_edits'] = [{'kind': 'rename', 'value': 'Reviewed name'}]
    focused = SavedSolutionResponse.model_validate(value)
    adapted = as_assistant_turn(focused)
    assert isinstance(adapted, AssistantTurn) and adapted.message == focused.message
    assert adapted.template_key is None and adapted.expected_revision is None and adapted.edits == []
    assert adapted.recommended_seed is None and adapted.composition_settings is None and adapted.registered_settings is None
    assert adapted.solution_edits == focused.solution_edits
    assert (adapted.discovery.question if adapted.discovery else None) == focused.clarification


@pytest.fixture
def policy(configured):
    """Synthetic count/defaults solely for policy tests, not provider limits."""
    with SessionLocal() as db:
        contract = db.get(OperationContract, 'fixture-contract')
        definition = deepcopy(contract.definition)
        definition['execution_parameters']['properties'].update({
            'limit': {'type': 'integer', 'title': 'Candidate limit', 'description': 'Synthetic fixture maximum', 'minimum': 1, 'maximum': 4, 'default': 1},
            'include_links': {'type': 'boolean', 'title': 'Include links', 'description': 'Synthetic fixture flag', 'default': True}})
        contract.definition = definition; db.commit()
    return configured


# Supplied outcomes deliberately test both allowed alternatives. They do not
# evaluate whether a real model will select those outcomes for these sentences.
CASES = [
    ('information', 'What processing services are listed, and what are their limits?', response(message='The accessible generator has published settings; compatibility and runtime readiness are separate.')),
    ('incomplete-goal', 'Help me design alternatives, but I have not decided which existing copy to use.', response('clarification', clarification='Which displayed copy should generate the alternatives?')),
    ('specified-goal', 'On the first copy, set the candidate maximum to two.', response('proposal', solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"limit":2}'}])),
    ('defaults', 'Use the published defaults on the first copy for a single-candidate study.', response('proposal', message='Review the published defaults for this instance.', solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"seed":42,"limit":1,"include_links":true}'}])),
    ('inadequate-default-question', 'I want to compare layouts generated by the first copy.', response('clarification', message='The default allows up to one candidate, which cannot support comparison.', clarification='How many candidates would you like to compare?')),
    ('inadequate-default-assumption', 'Let us compare a few layouts from the first copy.', response('proposal', message='Review a supported small comparison limit; fewer results may be returned.', solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"limit":2}'}], assumptions=['Propose up to two candidates for comparison, using the fixture contract range; this is not your stated choice or scientific approval.'])),
    ('ambiguous-instance', 'Increase the generator limit to three.', response('clarification', clarification='Should I change the first or second generator copy?')),
    ('unsupported', 'Enable a quantum_optimizer setting.', response('unsupported', message='The published contract has no quantum_optimizer setting; the current design is retained.')),
]


@pytest.mark.parametrize('case,message,fixture', CASES, ids=[case[0] for case in CASES])
def test_offline_policy_outcomes_flow_through_review_and_preserve_state(policy, provider, case, message, fixture):
    client = policy
    from app.services.workflow_boundaries import complete
    nodes, edges = [node('first'), node('second', 43)], []
    complete(nodes, edges)
    # Start with normal workflow display boundaries already present, so this
    # test checks exact connection preservation rather than boundary creation.
    solution = client.post('/solutions', json={'name': 'Policy fixture', 'nodes': nodes, 'edges': edges,
        'design_metadata': {'run_input': {'selected': 'private-input-body'}}}).json()
    solution = client.get('/solutions/' + solution['id']).json()
    provider.turn = turn([{'kind': 'rename', 'value': 'Prior reviewed proposal'}])
    old = send(client, solution, provider, 'Rename the saved design for review').json()
    provider.turn = SavedSolutionResponse.model_validate(fixture)
    actual = send(client, solution, provider, message)
    assert actual.status_code == 200, actual.text
    state = actual.json()
    assert client.get('/solutions/' + solution['id']).json() == solution
    assert state['messages'][-1]['content'] == fixture['message']
    if fixture['outcome'] == 'proposal':
        assert state['pending']['id'] != old['pending']['id']
        disclosures = [c['after'] for c in state['pending']['changes'] if c['action'] == 'proposed_assumption']
        assert disclosures == fixture['assumptions']
        # Reopening retains the complete review disclosure before Apply.
        assert client.get(scope(solution)).json()['pending'] == state['pending']
        assert apply(client, solution, state).status_code == 200
        changed = client.get('/solutions/' + solution['id']).json()
        assert changed['design_metadata'] == solution['design_metadata'] and changed['edges'] == solution['edges']
        copies = [n for n in changed['nodes'] if n['data'].get('service')]
        assert copies[1]['data'] == solution['nodes'][1]['data']
        assert copies[0]['data']['configuration']['parameters']['seed'] == 42
    else:
        assert state['pending'] == old['pending']
        assert (state['clarification']['question'] if state['clarification'] else None) == fixture['clarification']
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count() == 0


def test_pending_explanation_detour_short_reply_and_partial_patch(policy, provider):
    client = policy; solution = saved(client)
    provider.turn = turn([{'kind': 'rename', 'value': 'Existing review'}])
    prior = send(client, solution, provider, 'Use a useful title').json()
    provider.turn = turn(outcome='clarification', clarification='What maximum should the first copy use?')
    question = send(client, solution, provider, 'Compare candidates on the first copy').json()
    provider.turn = turn(message='The pending rename is reviewed separately; nothing runs until Builder Run.')
    explanation = send(client, solution, provider, 'What would happen before I apply?').json()
    assert explanation['pending'] == prior['pending'] and explanation['clarification'] == question['clarification']
    provider.turn = turn([{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"limit":3}'}])
    proposed = send(client, solution, provider, 'Three please').json()
    context = provider.contexts[-1]
    assert context['pending_clarification'] == question['clarification']
    assert context['pending_candidate'] == prior['pending']['candidate']
    assert context['request'] == 'Three please'
    assert proposed['clarification'] is None
    assert apply(client, solution, proposed).status_code == 200
    changed = client.get('/solutions/' + solution['id']).json()
    assert changed['nodes'][0]['data']['configuration']['parameters'] == {'seed': 42, 'limit': 3}
    assert changed['design_metadata'] == solution['design_metadata']


def test_existing_offline_ui_double_uses_focused_contract_only(environment, tmp_path, monkeypatch):
    """Maintenance of the retained scripted double, not a new demonstration."""
    from pathlib import Path
    from app.main import app
    from app.services.design_ai_provider import get_provider
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / 'deploy/assistant_acceptance'))
    from offline_provider import OfflineProvider
    double = OfflineProvider(tmp_path)
    app.dependency_overrides[get_provider] = lambda: double
    solution = environment.post('/solutions', json={'name': 'Offline double compatibility', 'nodes': [], 'edges': []}).json()
    actual = send(environment, solution, double, 'Explain the current design')
    assert actual.status_code == 200, actual.text
    assert actual.json()['messages'][-1]['outcome'] == 'answer'
    assert actual.json()['pending'] is None
    trace = json.loads((tmp_path / 'assistant-trace.private.jsonl').read_text(encoding='utf-8'))
    assert SavedSolutionResponse.model_validate(trace['response']).outcome == 'answer'
    assert 'EXPLICIT OFFLINE' in trace['boundary']


def test_confirmation_of_matching_pending_proposal_needs_no_duplicate_edits(policy, provider):
    client = policy; solution = saved(client)
    provider.turn = turn([{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"limit":2}'}],
        assumptions=['Propose up to two candidates for this fixture comparison.'])
    proposed = send(client, solution, provider, 'Prepare a small comparison').json()
    provider.turn = turn(message='Confirmed: the existing review already proposes up to two; it has not been applied.')
    confirmed = send(client, solution, provider, 'Yes, up to two please').json()
    assert confirmed['pending'] == proposed['pending']
    assert client.get('/solutions/' + solution['id']).json() == solution
    reopened = client.get(scope(solution)).json()
    assert reopened['pending']['changes'][0]['action'] == 'proposed_assumption'
    assert reopened['pending']['changes'][0]['after'] == proposed['pending']['changes'][0]['after']
    assert provider.contexts[-1]['pending_candidate'] == proposed['pending']['candidate']
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count() == 0


@pytest.mark.parametrize('use_test_catalogue_ids', [False, True])
def test_recorded_genuine_confirmation_rejection_preserves_existing_review(bound, provider, use_test_catalogue_ids):
    """Actual failed I3 reply; mapped variant checks the same catalogue/instance confusion.

    This verifies rejection/preservation, never successful model confirmation.
    """
    from pathlib import Path
    from test_saved_solution_assistant import chat
    client, _ = bound
    solution = client.post('/solutions', json={'name': 'Recorded I3 failure replay', 'nodes': [], 'edges': []}).json()
    edits = [{'kind': 'add_service', 'value': json.dumps({'service_id': sid, 'local_ref': ref})}
             for sid, ref in [('dutch-ConfigureAndSynthesize', 'source'), ('dutch-RunBenchmark', 'view')]]
    edits.append({'kind': 'connect', 'value': '{"source":"source","target":"view","source_slot":"grid","target_slot":"grid"}'})
    pending = chat(client, solution, provider, edits).json()
    recorded = json.loads((Path(__file__).parent/'fixtures/controlled-rejected-proposal-20261119.json').read_text(encoding='utf-8'))
    assert provider_evidence.digest(recorded) == 'b653d30e97f74245072430465172533d48368200d3555052c0e1cd8a69fd9a3f'
    if use_test_catalogue_ids:
        recorded['solution_edits'][0]['node_id'] = 'dutch-ConfigureAndSynthesize'
        value = json.loads(recorded['solution_edits'][1]['value'])
        value.update(source='dutch-ConfigureAndSynthesize', target='dutch-RunBenchmark')
        recorded['solution_edits'][1]['value'] = json.dumps(value)
    # Preserve the exact historical edit payload; only wrap the new explicit base.
    recorded['edit_base'] = response('proposal')['edit_base']
    provider.turn = SavedSolutionResponse.model_validate(recorded)
    result = send(client, solution, provider, 'Confirm the already matching pending design')
    assert result.status_code == 422 and result.json()['detail']['stage'] == 'application_validation'
    assert 'Select one existing service instance' in result.json()['detail']['message']
    assert client.get(scope(solution)).json() == pending
    assert client.get('/solutions/' + solution['id']).json() == solution
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count() == 0


@pytest.mark.parametrize('invalid', [response('answer', solution_edits=[{'kind': 'rename', 'value': 'No'}]),
    response(template_key='legacy'), response('proposal', solution_edits=[{'kind': 'set_node_parameters', 'node_id': 'first', 'value': '{"undeclared":true}'}])])
def test_invalid_response_and_unsupported_proposal_retain_saved_and_pending(policy, provider, invalid):
    client = policy; solution = saved(client)
    provider.turn = turn([{'kind': 'rename', 'value': 'Retain review'}])
    old = send(client, solution, provider, 'Propose a name').json()
    provider.turn = invalid  # Deliberately unvalidated provider double.
    result = send(client, solution, provider, 'An invalid structured fixture')
    assert result.status_code in (409, 422, 502)
    assert client.get(scope(solution)).json() == old
    assert client.get('/solutions/' + solution['id']).json() == solution


@pytest.mark.parametrize('consistent', [True, False])
def test_focused_sdk_wire_schema_budget_audit_and_parser_are_identical(environment, tmp_path, monkeypatch, caplog, consistent):
    """Actual SDK serialization over offline HTTP; synthetic disposable ledger only."""
    from test_scoped_ai_acceptance import new, SCOPE
    from app.services.scoped_ai_acceptance import MODEL
    budget = new(tmp_path)
    for key, value in {'design_ai_scoped_acceptance_file': str(budget.path), 'design_ai_model': MODEL,
        'design_ai_reasoning_effort': 'none', 'design_ai_max_output_tokens': 3000,
        'openai_api_key': 'OFFLINE DOUBLE NEVER TRANSMITTED'}.items(): monkeypatch.setattr(settings, key, value)
    caplog.set_level(logging.DEBUG, logger='design_ai.provider.audit')
    expected = SavedSolutionResponse.model_validate(response('clarification', clarification='Which labelled instance?'))
    calls = []
    def handler(request):
        body = json.loads(request.content); calls.append(body)
        assert budget.availability()['request_count'] == 1
        format = body['text']['format']
        assert format == provider_evidence.response_format(SavedSolutionResponse)
        assert set(format['schema']['properties']) == {'outcome', 'message', 'clarification', 'solution_edits', 'assumptions', 'edit_base'}
        assert set(format['schema']['required']) == set(format['schema']['properties'])
        assert format['schema']['additionalProperties'] is False
        assert not {'AssistantTurn', 'CompositionSettings', 'Edit', 'DiscoveryDecision'} & set(format['schema']['$defs'])
        return httpx.Response(200, json={'id': 'resp_offline_fixture', 'object': 'response', 'created_at': 0,
            'status': 'completed', 'model': MODEL, 'service_tier': 'default',
            'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120},
            'output': [{'type': 'message', 'id': 'msg_offline_fixture', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': expected.model_dump_json() if consistent else json.dumps(response(clarification='Invalid question on answer')), 'annotations': []}]}]})
    monkeypatch.setattr(design_ai_provider, 'AsyncOpenAI', lambda **kwargs: AsyncOpenAI(**kwargs,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    context = {'mode': 'saved_solution', 'request': 'Which copy?', '_acceptance_binding': SCOPE}
    if consistent:
        assert asyncio.run(design_ai_provider.OpenAIProvider().respond(context)) == expected
    else:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:
            asyncio.run(design_ai_provider.OpenAIProvider().respond(context))
        assert error.value.detail['stage'] == 'sdk_parse'
        assert not budget.availability()['can_request']
    assert len(calls) == 1
    body = calls[0]; format = body['text']['format']
    bound = sum(len(item['content'].encode('utf-8')) for item in body['input']) + len(json.dumps(format).encode('utf-8')) + 8192
    with sqlite3.connect(budget.path) as db:
        assert db.execute('SELECT input_bound FROM acceptance_requests').fetchone()[0] == bound
    audit = json.loads(next(r.message for r in caplog.records if r.name == 'design_ai.provider.audit'))
    assert audit['response_schema_name'] == 'SavedSolutionResponse'
    assert audit['response_schema_sha256'] == provider_evidence.digest(format['schema'])
    assert audit['validated_response'] == (expected.model_dump(mode='json') if consistent else None)
    assert audit['validated_response_sha256'] == (provider_evidence.digest(expected.model_dump(mode='json')) if consistent else None)
    assert audit['request_sha256'] == provider_evidence.digest({'configuration': audit['requested_configuration'], 'input': body['input'], 'schema': format['schema']})
