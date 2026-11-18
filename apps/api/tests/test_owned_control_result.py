"""Owned API routes against a real authenticated loopback Control double.

This verifies transport/authority/integrity, never algorithm consumption.
"""
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread

import pytest
from test_native_instance_evidence import proof
from app.core.config import settings
from app.services import owned_artifact_preview as owned
from app.services import owned_control_result as control


@pytest.fixture
def remote(proof, monkeypatch, tmp_path):
    physical = 'cfg-' + control.digest(b'wf-native\0task_test')
    calls = []; responses = {}; key = 'disposable-control-fixture'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            calls.append((self.path, self.headers.get('Authorization') == 'Bearer ' + key))
            if self.headers.get('Authorization') != 'Bearer ' + key:
                self.send_response(401); self.end_headers(); return
            status, raw = responses.get(self.path, (404, b''))
            self.send_response(status); self.end_headers(); self.wfile.write(raw)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    snapshot = deepcopy(proof.row.submitted)
    node = snapshot['compiled']['solution_studio_metadata']['execution_instances'][0]
    snapshot['compiled']['dockerinfo'] = {'docker_info_list': [{'container_name': 'generic', 'ip_address': '127.0.0.1', 'port': str(server.server_port)}]}
    proof.row.submitted = snapshot
    proof.row.submitted_sha256 = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    proof.db.commit()
    raw = b'example,value\n1,1.2\n2,2.4\n'
    output = {'protocol': 'http', 'uri': base + '/control/data/' + physical, 'format': 'csv'}
    receipt = {'workflow_id': 'wf-native', 'task_id': 'task_test', 'service_task_id': physical,
        'method': 'Run', 'state': 'complete', 'configuration': node['configuration'], 'parameter_contract_sha256': 'a'*64,
        'delivered_query': {'count': 2}, 'upstream_interface_sha256': 'b'*64, 'output': output,
        'output_sha256': control.digest(raw), 'output_bytes': len(raw), 'observed_sequence_count': 2, 'csv_data_rows': 2}
    responses['/control/data/' + physical] = (200, raw)
    responses['/control/receipt/' + physical] = (200, json.dumps(receipt).encode())
    target = tmp_path / 'targets.private.json'
    target.write_text(json.dumps({'targets': [{'base_url': base, 'token': key, 'runtime_destination': settings.orchestrator_base_url}]}))
    monkeypatch.setattr(settings, 'owned_control_targets_file', str(target))
    proof.observed['tasks'][0]['output_refs'] = [output]
    monkeypatch.setattr(owned, 'get_workflow_tasks', lambda _: proof.observed)
    proof.remote = dict(base=base, responses=responses, receipt=receipt, calls=calls, physical=physical, output=output, target=target)
    yield proof
    server.shutdown(); server.server_close(); thread.join(2)


def preview(remote, **changes):
    return remote.client.post('/data-references/preview', json={'workflow_id': 'wf-native', 'task_id': 'task_test',
        **remote.remote['output'], **changes})


def test_authenticated_csv_preview_and_evidence_share_immutable_receipt(remote):
    result = preview(remote)
    assert result.status_code == 200, result.text
    assert result.json()['rows'][1]['value'] == '2.4'
    evidence = remote.client.get('/workflows/wf-native/instance-evidence').json()
    record = evidence['instances'][0]
    assert record['evidence_level'] == 'authenticated_runtime_receipt'
    assert record['delivered_parameters'] == {'count': 2}
    assert 'algorithm_consumed' not in record and 'Not established' in record['algorithm_consumption']
    assert all(authorized for _, authorized in remote.remote['calls'])


@pytest.mark.parametrize('kind', ['other_owner', 'snapshot', 'runtime', 'endpoint', 'task_node', 'duplicate', 'input', 'arbitrary_url'])
def test_bad_authority_denied_before_control_fetch(remote, kind, monkeypatch):
    if kind == 'other_owner': remote.row.owner_user_id = 'other'; remote.db.commit()
    if kind == 'snapshot': remote.row.submitted_sha256 = 'changed'; remote.db.commit()
    if kind == 'runtime': monkeypatch.setattr(settings, 'orchestrator_base_url', 'http://different-runtime')
    if kind == 'endpoint':
        doc = json.loads(remote.remote['target'].read_text()); doc['targets'][0]['base_url'] = 'http://unapproved.invalid'; remote.remote['target'].write_text(json.dumps(doc))
    if kind == 'task_node': remote.observed['tasks'][0]['node_key'] = 'other:Run'
    if kind == 'duplicate': remote.observed['tasks'].append(deepcopy(remote.observed['tasks'][0]))
    if kind == 'input': remote.observed['tasks'][0]['input_refs'] = []
    changes = {'uri': 'http://arbitrary.invalid/secret'} if kind == 'arbitrary_url' else {}
    assert preview(remote, **changes).status_code in {403, 404, 409}
    assert remote.remote['calls'] == []


@pytest.mark.parametrize('field', ['workflow_id', 'task_id', 'service_task_id', 'method', 'state', 'configuration', 'parameter_contract_sha256', 'delivered_query', 'output_sha256', 'output_bytes', 'output', 'csv_data_rows', 'observed_sequence_count'])
def test_conflicting_receipt_never_exposes_bytes(remote, field):
    receipt = deepcopy(remote.remote['receipt'])
    receipt[field] = {'count': True} if field == 'delivered_query' else 'changed'
    remote.remote['responses']['/control/receipt/' + remote.remote['physical']] = (200, json.dumps(receipt).encode())
    assert preview(remote).status_code == 409


def test_changed_bytes_or_receipt_cannot_replace_prior_output(remote):
    assert preview(remote).status_code == 200
    receipt = deepcopy(remote.remote['receipt']); receipt['extra'] = 'changed observation'
    remote.remote['responses']['/control/receipt/' + remote.remote['physical']] = (200, json.dumps(receipt).encode())
    assert preview(remote).status_code == 409
    remote.remote['responses']['/control/receipt/' + remote.remote['physical']] = (200, json.dumps(remote.remote['receipt']).encode())
    remote.remote['responses']['/control/data/' + remote.remote['physical']] = (200, b'changed output')
    assert preview(remote).status_code == 409


def test_redirect_or_oversized_receipt_is_refused(remote):
    remote.remote['responses']['/control/receipt/' + remote.remote['physical']] = (302, b'')
    assert preview(remote).status_code == 409
    remote.remote['responses']['/control/receipt/' + remote.remote['physical']] = (200, b'x' * 256001)
    assert preview(remote).status_code == 409


def test_uninstalled_target_and_logged_out_user_never_fetch(remote, monkeypatch):
    monkeypatch.setattr(settings, 'owned_control_targets_file', '')
    assert preview(remote).status_code == 409 and remote.remote['calls'] == []
    remote.client.post('/auth/logout')
    assert preview(remote).status_code == 401 and remote.remote['calls'] == []
