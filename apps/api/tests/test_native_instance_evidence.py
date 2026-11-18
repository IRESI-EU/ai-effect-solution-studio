"""Portable ownership/association/integrity cases; no algorithm claims here."""
import base64
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from app.core.config import settings
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.services import native_instance_evidence as native


@pytest.fixture
def proof(environment, db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'aie18_evidence_root', '')
    monkeypatch.setattr(settings, 'portuguese_evidence_root', '')
    monkeypatch.setattr(settings, 'aie37_qualification', False)
    monkeypatch.setenv('ARTIFACT_BASE_PATH', str(tmp_path))
    monkeypatch.setenv('ARTIFACT_BASE_PATHS', '')
    configuration = {'contract_id': 'c', 'contract_version': '1.0.0', 'operation_identity': 'urn:test:generic:operation',
                     'instance_id': 'instance', 'schema_version': '1.0', 'parameters': {'count': 2}}
    input_value = {'source': 'synthetic user input'}
    inputs = [{'protocol': 'inline', 'format': 'json', 'uri': base64.b64encode(json.dumps(input_value).encode()).decode()}]
    instance = {'instance_id': 'instance', 'task_id': 'task_test', 'node_key': 'generic:Run', 'operation_name': 'Run',
                'configuration': configuration, 'parameter_contract_sha256': 'a'*64, 'input_bindings': []}
    snapshot = {'runtime_destination': settings.orchestrator_base_url, 'request': {},
                'compiled': {'inputs': inputs, 'solution_studio_metadata': {'execution_instances': [instance]}}}
    row = ExecutionSubmission(id='native-submission', owner_user_id='designer', workflow_id='wf-native', phase='submitted',
                              submitted=snapshot, submitted_sha256=hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest())
    db.add(row); db.add(Deployment(id='native-deployment', workflow_id='wf-native', created_by_user_id='designer', name='Synthetic owned deployment')); db.commit()
    folder = tmp_path / 'wf-native'; folder.mkdir(); output = folder / 'task_test.json'
    value = {'execution': {'schema_version': '1.0', 'workflow_id': 'wf-native', 'task_id': 'task_test', 'instance_id': 'instance', 'operation_name': 'Run',
                          'configuration': deepcopy(configuration), 'algorithm_consumed': {'count': 2}, 'parameter_contract_sha256': 'a'*64,
                          'input_sha256': hashlib.sha256(native.canonical(input_value)).hexdigest(), 'instrumentation': 'Synthetic fixture only'}}
    output.write_text(json.dumps(value))
    observed = {'workflow_id': 'wf-native', 'tasks': [{'task_id': 'task_test', 'node_key': 'generic:Run', 'status': 'completed', 'input_refs': inputs,
                                                    'output_refs': [{'protocol': 'file', 'format': 'json', 'uri': str(output)}]}]}
    calls = []
    def tasks(workflow): calls.append(workflow); return observed
    monkeypatch.setattr(native, 'get_workflow_tasks', tasks)
    return SimpleNamespace(client=environment, row=row, output=output, value=value, observed=observed, calls=calls, db=db)


def inspect(proof):
    return proof.client.get('/workflows/wf-native/instance-evidence')


def test_generic_instrumentation_uses_existing_receipts_and_checks_content_changes(proof):
    value = inspect(proof).json()
    assert value['state'] == 'available' and value['instances'][0]['algorithm_consumed'] == {'count': 2}
    proof.value['unrelated_result'] = 'modified'
    proof.output.write_text(json.dumps(proof.value))
    assert inspect(proof).json()['instances'][0]['state'] == 'conflicting'


@pytest.mark.parametrize('mutation', ['workflow', 'task', 'instance', 'operation', 'configuration', 'boolean_type', 'consumption', 'digest', 'input_hash', 'task_node', 'duplicate_task', 'observed_input'])
def test_mismatched_observations_are_not_verified(proof, mutation):
    execution = proof.value['execution']
    for field, kind in [('workflow_id', 'workflow'), ('task_id', 'task'), ('instance_id', 'instance'), ('operation_name', 'operation')]:
        if mutation == kind: execution[field] = 'another'
    if mutation == 'configuration': execution['configuration']['contract_version'] = '2.0.0'
    if mutation == 'boolean_type': execution['algorithm_consumed']['count'] = True
    if mutation == 'consumption': execution['algorithm_consumed']['count'] = 3
    if mutation == 'digest': execution['parameter_contract_sha256'] = 'b'*64
    if mutation == 'input_hash': execution['input_sha256'] = 'b'*64
    if mutation == 'task_node': proof.observed['tasks'][0]['node_key'] = 'other:Run'
    if mutation == 'duplicate_task': proof.observed['tasks'].append(deepcopy(proof.observed['tasks'][0]))
    if mutation == 'observed_input': proof.observed['tasks'][0]['input_refs'] = []
    proof.output.write_text(json.dumps(proof.value))
    assert inspect(proof).json()['instances'][0]['state'] == 'conflicting'


def test_other_owner_is_denied_before_runtime_access(proof):
    proof.row.owner_user_id = 'other'; proof.db.commit()
    assert inspect(proof).status_code == 403 and proof.calls == []


def test_runtime_change_does_not_query_a_different_environment(proof, monkeypatch):
    monkeypatch.setattr(settings, 'orchestrator_base_url', 'http://other-runtime')
    assert inspect(proof).json()['state'] == 'unavailable' and proof.calls == []


def test_missing_mount_or_unsupported_output_does_not_claim_consumption(proof):
    proof.observed['tasks'][0]['output_refs'][0]['uri'] += '.missing'
    assert inspect(proof).json()['instances'][0]['state'] == 'inaccessible'
    proof.observed['tasks'][0]['output_refs'][0]['format'] = 'csv'
    assert inspect(proof).json()['instances'][0]['state'] == 'unavailable'
