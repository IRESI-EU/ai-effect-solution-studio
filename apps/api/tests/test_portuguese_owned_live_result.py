"""Opt-in owned API inspection of already produced real local qualification bytes.

No dispatch. SQLite and explicit task observations are fixtures; no claim of a
normal Portal Run or live orchestrator acceptance. Uses the real Control reader.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest
from app.core.config import settings
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.services import native_instance_evidence, owned_artifact_preview
from app.services.parameter_values import parameter_contract_digest


def test_real_qualification_bytes_through_owned_preview_and_receipt_routes(environment, db, monkeypatch, tmp_path):
    profile = os.getenv('PORTUGUESE_QUALIFICATION_PROFILE')
    if not profile:
        pytest.skip('Explicit disposable qualification profile is required; this never dispatches')
    directory = Path(profile)
    operator = json.loads((directory / 'operator.private.json').read_text())
    runs = json.loads((directory / 'receipts.private.json').read_text())
    workflow = operator['workflow_id']; base = operator['connector_url']
    nodes, tasks, requested, endpoints = [], [], [], []
    first_ref = runs[0]['payload']['inputs']
    for run in runs:
        source_instance = run['train']['configuration']['instance_id']
        for label in ('train', 'generate'):
            receipt = run[label]; config = receipt['configuration']; task_id = receipt['task_id']
            container = 'fixture-' + task_id
            export = json.loads((directory / 'contracts' / (receipt['method'] + '.json')).read_text())
            contract_hash = parameter_contract_digest(export['operations'][0]['execution_parameters'])
            node = {'instance_id': config['instance_id'], 'task_id': task_id, 'node_key': container + ':' + receipt['method'],
                'operation_name': receipt['method'], 'configuration': config, 'parameter_contract_sha256': contract_hash,
                'input_bindings': [] if label == 'train' else [source_instance]}
            nodes.append(node)
            inputs = first_ref if label == 'train' else [run['train']['output']]
            tasks.append({'task_id': task_id, 'node_key': node['node_key'], 'status': 'completed',
                'input_refs': inputs, 'output_refs': [receipt['output']]})
            requested.append({'node_id': config['instance_id'], 'configuration': config})
            endpoints.append({'container_name': container, 'ip_address': '127.0.0.1', 'port': '28190'})
    monkeypatch.setattr(settings, 'orchestrator_base_url', 'http://qualification-task-observation-fixture.invalid')
    monkeypatch.setattr(settings, 'portuguese_evidence_root', '')
    monkeypatch.setattr(settings, 'aie18_evidence_root', '')
    monkeypatch.setattr(settings, 'aie37_qualification', False)
    snapshot = {'runtime_destination': settings.orchestrator_base_url, 'request': {'nodes': requested},
        'compiled': {'inputs': first_ref, 'dockerinfo': {'docker_info_list': endpoints},
            'solution_studio_metadata': {'execution_instances': nodes}}}
    row = ExecutionSubmission(id='real-model-owned-fixture', owner_user_id='designer', workflow_id=workflow, phase='submitted',
        submitted=snapshot, submitted_sha256=hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest())
    db.add(row); db.add(Deployment(id='real-model-owned-fixture', created_by_user_id='designer', workflow_id=workflow, name='Disposable model fixture inspection'))
    db.commit()
    target = tmp_path / 'targets.private.json'
    target.write_text(json.dumps({'targets': [{'base_url': base, 'token': operator['key'], 'runtime_destination': settings.orchestrator_base_url}]}))
    monkeypatch.setattr(settings, 'owned_control_targets_file', str(target))
    observed = {'workflow_id': workflow, 'tasks': tasks}
    monkeypatch.setattr(native_instance_evidence, 'get_workflow_tasks', lambda _: deepcopy(observed))
    monkeypatch.setattr(owned_artifact_preview, 'get_workflow_tasks', lambda _: deepcopy(observed))
    for run in runs:
        receipt = run['generate']
        response = environment.post('/data-references/preview', json={'workflow_id': workflow,
            'task_id': receipt['task_id'], **receipt['output']})
        assert response.status_code == 200, response.text
        result = response.json()
        assert len(result['rows']) == receipt['csv_data_rows']
        assert result['evidence']['output_sha256'] == receipt['output_sha256']
        assert result['evidence']['summary']['observed_sequence_count'] == receipt['observed_sequence_count']
    evidence = environment.get('/workflows/' + workflow + '/instance-evidence').json()
    assert len(evidence['instances']) == 4 and evidence['state'] == 'available', evidence
    assert all(r['evidence_level'] == 'authenticated_runtime_receipt' and 'algorithm_consumed' not in r for r in evidence['instances'])
    row.owner_user_id = 'other'
    db.query(Deployment).filter(Deployment.workflow_id == workflow).one().created_by_user_id = 'other'
    db.commit()
    assert environment.post('/data-references/preview', json={'workflow_id': workflow,
        'task_id': runs[0]['generate']['task_id'], **runs[0]['generate']['output']}).status_code == 403
