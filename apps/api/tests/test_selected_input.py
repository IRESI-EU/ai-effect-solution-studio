"""Owned saved CSV selection and inline delivery; no file/URL authority expansion."""
import base64
from copy import deepcopy
import json

import pytest
from fastapi import HTTPException
from app.services.selected_input import KEY, compile_input
from app.services.workflow_compiler import compile_to_wp3_payload
from app.schemas.workflow_submit import WorkflowSubmitRequest


def csv_input(content='datetime,value\n2026-01-01,2\n'):
    return {KEY: {'schema_version': '1.0', 'kind': 'inline_csv', 'name': 'chosen.csv', 'content': content}}


def test_csv_is_data_not_a_json_wrapped_setting():
    selected = csv_input()
    result = compile_to_wp3_payload(WorkflowSubmitRequest(name='Selected data', nodes=[], edges=[], run_input=selected))
    ref = result['inputs'][0]
    assert ref['protocol'] == 'inline' and ref['format'] == 'csv'
    assert base64.b64decode(ref['uri']).decode() == selected[KEY]['content']
    legacy = compile_input({'prompt': 'Existing JSON input'})
    assert legacy['format'] == 'json' and json.loads(base64.b64decode(legacy['uri'])) == {'prompt': 'Existing JSON input'}


@pytest.mark.parametrize('older', ['wp3', 'connector'])
def test_old_csv_capability_rejected_without_any_dispatch(monkeypatch, older):
    """Explicit HTTP-response doubles at the preflight adapter boundary."""
    from types import SimpleNamespace
    from app.services.orchestrator_adapter import require_parameter_transport
    config={'operation_identity':'urn:fixture:train','contract_version':'1.0.0','schema_version':'1.0'}
    node={'node_key':'fixture:Train','configuration':config,'parameter_contract_sha256':'a'*64,'input_bindings':[]}
    compiled={'inputs':[{'protocol':'inline','format':'csv','uri':'eAoxCg=='}],
        'solution_studio_metadata':{'execution_instances':[node]}}
    capability={'capability_schema_version':'1.0','transports':['http-parameters-v1'],'parameter_validation':'wrapper-contract-v1'}
    if older=='connector':capability['input_transport_validation']='wrapper-input-v1'
    calls=[]
    def get(url,**kwargs):
        calls.append(('GET',url));assert url.endswith('/capabilities')
        return SimpleNamespace(status_code=200,json=lambda:capability)
    def post(url,**kwargs):
        calls.append(('POST',url));assert url.endswith('/workflows/check-compatibility')
        return SimpleNamespace(status_code=200,json=lambda:{'status':'ready',
            'checks':{'fixture:Train':{**config,'parameter_contract_sha256':'a'*64}},'input_checks':{}})
    monkeypatch.setattr('app.services.orchestrator_adapter.requests.get',get)
    monkeypatch.setattr('app.services.orchestrator_adapter.requests.post',post)
    with pytest.raises(HTTPException) as error:require_parameter_transport(compiled)
    assert error.value.status_code==409
    assert len(calls)==(1 if older=='wp3' else 2)


@pytest.mark.parametrize('change', ['url', 'path', 'huge', 'version', 'name', 'header', 'rows', 'nul', 'extra'])
def test_invalid_csv_or_reference_rejected_before_compilation(change):
    value = csv_input()
    if change in {'url', 'path'}: value[KEY] = {'protocol': 'http' if change == 'url' else 'file', 'uri': 'private'}
    if change == 'huge': value[KEY]['content'] = 'col\n' + 'a'*60001
    if change == 'version': value[KEY]['schema_version'] = '2.0'
    if change == 'name': value[KEY]['name'] = '../private.csv'
    if change == 'header': value[KEY]['content'] = 'x,x\n1,2\n'
    if change == 'rows': value[KEY]['content'] = 'x,y\n1\n'
    if change == 'nul': value[KEY]['content'] += '\0'
    if change == 'extra': value['prompt'] = 'ambiguous'
    with pytest.raises(HTTPException) as exc: compile_input(value)
    assert exc.value.status_code == 422


def test_owned_save_reload_stale_input_and_assistant_privacy(environment, provider):
    client = environment
    selected = csv_input('datetime,private_feature\n2026-01-01,PRIVATE_CSV_SENTINEL\n')
    assert client.post('/workflows/submit-to-orchestrator', json={'name': 'Unsaved data', 'nodes': [], 'edges': [], 'run_input': selected}).status_code == 422
    response = client.post('/solutions', json={'name': 'Private selected data', 'nodes': [], 'edges': [], 'design_metadata': {'run_input': selected}})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert client.get('/solutions/' + saved['id']).json()['design_metadata']['run_input'] == selected
    from app.schemas.solution_assistant import SavedSolutionResponse
    provider.turn = SavedSolutionResponse(outcome='answer', message='Selected data stays private', clarification=None, assumptions=[], solution_edits=[])
    response = client.post('/design-ai/solutions/' + saved['id'] + '/chat', json={'message': 'Describe my solution', 'expected_updated_at': saved['updated_at'], 'conversation_revision': 0})
    assert response.status_code == 200, response.text
    assert 'PRIVATE_CSV_SENTINEL' not in json.dumps(provider.contexts)
    assert provider.contexts[0]['solution']['workflow_input_selected'] is True
    from app.models.solution import Solution
    from app.db import SessionLocal
    from app.services.solution_editing import require_saved_input
    with SessionLocal() as db:
        row = db.get(Solution, saved['id'])
        with pytest.raises(HTTPException) as stale:
            require_saved_input(row, WorkflowSubmitRequest(name='Changed data', nodes=[], edges=[], run_input=csv_input('x\n2\n')))
        assert stale.value.status_code == 409
    bad = client.put('/solutions/' + saved['id'], json={'expected_updated_at': saved['updated_at'], 'design_metadata': {'run_input': csv_input('x,x\n1,2\n')}})
    assert bad.status_code == 422
    assert client.get('/solutions/' + saved['id']).json() == saved
    from app.core.security import hash_password
    from app.models.user import User
    with SessionLocal() as db:
        db.add(User(id='csv-other', email='csv-other@example.test', display_name='Other designer', password_hash=hash_password('DisposableTest12345'), role='solution_designer', status='active')); db.commit()
    assert client.post('/auth/login', json={'email': 'csv-other@example.test', 'password': 'DisposableTest12345'}).status_code == 200
    assert client.get('/solutions/' + saved['id']).status_code == 403
