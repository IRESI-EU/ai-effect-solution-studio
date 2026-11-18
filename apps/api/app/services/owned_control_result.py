"""Authenticated, explicitly installed Control results for an owned submission.

Targets are private operator configuration, never supplied by a browser or a
catalogue record. An HTTP receipt establishes delivered settings and byte
integrity, not independent model consumption. Existing receipt rows pin bytes.
"""
import hashlib
import csv
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.execution_submission import InstanceEvidenceReceipt
from app.services.execution_submission import view

MAX_BYTES = 5_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(target, path, limit):
    # No redirects, proxy inheritance, retries or request-provided URLs/headers.
    try:
        with requests.Session() as client:
            client.trust_env = False
            with client.get(target['base_url'] + path, headers={'Authorization': 'Bearer ' + target['token']},
                            timeout=(3, 10), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise ValueError('Control result is not available')
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > limit:
                        raise ValueError('Control result exceeds the inspection byte ceiling')
                return bytes(data)
    except requests.RequestException:
        raise HTTPException(503, 'Authenticated Control result is unavailable') from None


def target_for(row, node):
    if not settings.owned_control_targets_file:
        raise HTTPException(409, 'Remote preview transport has no qualified ownership boundary')
    document = json.loads(Path(settings.owned_control_targets_file).read_text())
    compiled = row.submitted['compiled']
    container = node['node_key'].rsplit(':', 1)[0]
    endpoints = [item for item in compiled['dockerinfo']['docker_info_list'] if item['container_name'] == container]
    if len(endpoints) != 1:
        raise ValueError('Submitted endpoint is ambiguous')
    endpoint = endpoints[0]
    targets = []
    for target in document['targets']:
        parsed = urlsplit(target['base_url'])
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment or not target.get('token')):
            raise ValueError('Invalid installed Control target')
        if (target['runtime_destination'] == row.submitted.get('runtime_destination') == settings.orchestrator_base_url
                and parsed.hostname == endpoint['ip_address']
                and (parsed.port or (443 if parsed.scheme == 'https' else 80)) == int(endpoint['port'])):
            targets.append(target)
    if len(targets) != 1:
        raise ValueError('No unambiguous installed target for this submitted runtime endpoint')
    return targets[0]


def inspect(row, node, task, db, tasks):
    """Caller has checked deployment ownership; recheck immutable associations."""
    from app.models.deployment import Deployment
    view(row)
    deployment = db.query(Deployment).filter(Deployment.workflow_id == row.workflow_id).first()
    if (row.phase != 'submitted' or not deployment or not row.owner_user_id
            or deployment.created_by_user_id != row.owner_user_id or deployment.solution_id != row.solution_id):
        raise HTTPException(409, 'Owned submission association is unavailable')
    try:
        target = target_for(row, node)
        configuration = node['configuration']
        if (not configuration or task['task_id'] != node['task_id'] or task['node_key'] != node['node_key']
                or task['status'] not in {'complete', 'completed'}):
            raise ValueError('Completed task association differs')
        compiled = row.submitted['compiled']
        expected = compiled.get('inputs', [])
        if node['input_bindings']:
            expected = []
            for source_id in node['input_bindings']:
                sources = [n for n in compiled['solution_studio_metadata']['execution_instances'] if n['instance_id'] == source_id]
                if len(sources) != 1:
                    raise ValueError('Upstream instance is ambiguous')
                upstream = [t for t in tasks if t.get('task_id') == sources[0]['task_id'] and t.get('node_key') == sources[0]['node_key']]
                if len(upstream) != 1 or upstream[0].get('status') not in {'complete', 'completed'}:
                    raise ValueError('Upstream task association differs')
                expected.extend(upstream[0].get('output_refs', []))
        core = lambda refs: [{k: r[k] for k in ('protocol', 'uri', 'format')} for r in refs]
        if canonical(core(task.get('input_refs', []))) != canonical(core(expected)):
            raise ValueError('Observed input bindings differ from submitted inputs')
        physical = 'cfg-' + digest((row.workflow_id + '\0' + node['task_id']).encode())
        output = {'protocol': urlsplit(target['base_url']).scheme,
                  'uri': target['base_url'] + '/control/data/' + physical,
                  'format': task['output_refs'][0]['format']}
        if task['output_refs'] != [output] or output['format'] not in {'json', 'csv'}:
            raise ValueError('Observed output is not the exact configured task output')
        receipt_raw = fetch(target, '/control/receipt/' + physical, 256_000)
        receipt = json.loads(receipt_raw)
        if (any(receipt.get(k) != v for k, v in {'workflow_id': row.workflow_id, 'task_id': node['task_id'],
                'service_task_id': physical, 'method': node['operation_name'], 'state': 'complete', 'output': output}.items())
                or canonical(receipt.get('configuration')) != canonical(configuration)
                or receipt.get('parameter_contract_sha256') != node['parameter_contract_sha256']
                or not re.fullmatch('[a-f0-9]{64}', receipt.get('upstream_interface_sha256', ''))
                or any(canonical(receipt['delivered_query'].get(k)) != canonical(v) for k, v in configuration['parameters'].items())):
            raise ValueError('Receipt differs from submitted task or delivered settings')
        raw = fetch(target, '/control/data/' + physical, MAX_BYTES)
        if digest(raw) != receipt['output_sha256'] or len(raw) != receipt['output_bytes']:
            raise ValueError('Control output bytes differ from receipt')
        if output['format'] == 'csv' and any(k in receipt for k in ('csv_data_rows', 'observed_sequence_count')):
            rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
            if 'csv_data_rows' in receipt and (type(receipt['csv_data_rows']) is not int or len(rows) != receipt['csv_data_rows']):
                raise ValueError('CSV row observation differs from output bytes')
            if 'observed_sequence_count' in receipt and (type(receipt['observed_sequence_count']) is not int
                    or not rows or any(not r.get('example') for r in rows)
                    or len({r['example'] for r in rows}) != receipt['observed_sequence_count']):
                raise ValueError('CSV sequence observation differs from output bytes')
        receipt_hash = digest(canonical(receipt))
        old = db.get(InstanceEvidenceReceipt, (row.id, node['task_id']))
        if old and old.manifest_sha256 != receipt_hash:
            raise ValueError('Previously inspected Control receipt changed')
        if old is None:
            db.add(InstanceEvidenceReceipt(submission_id=row.id, task_id=node['task_id'], manifest_sha256=receipt_hash))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                old = db.get(InstanceEvidenceReceipt, (row.id, node['task_id']))
                if old is None or old.manifest_sha256 != receipt_hash:
                    raise ValueError('Concurrent Control receipt differs')
        proof = {key: node[key] for key in ('instance_id', 'task_id', 'node_key', 'operation_name')}
        proof.update(state='available', evidence_level='authenticated_runtime_receipt',
                     wrapper_received=configuration['parameters'], delivered_parameters={k: receipt['delivered_query'][k] for k in configuration['parameters']},
                     algorithm_consumption='Not established by this receipt; independent model/runtime evidence is required',
                     output_sha256=digest(raw), manifest_sha256=receipt_hash,
                     upstream_interface_sha256=receipt['upstream_interface_sha256'],
                     summary={k: receipt[k] for k in ('observed_sequence_count', 'csv_data_rows') if k in receipt})
        return raw, proof
    except (ValueError, KeyError, TypeError, OSError, IndexError, AttributeError):
        raise HTTPException(409, 'Control result failed endpoint, task, configuration or integrity validation') from None


def preview(row, payload, task, db, tasks):
    compiled = row.submitted.get('compiled')
    metadata = compiled.get('solution_studio_metadata') if isinstance(compiled, dict) else None
    nodes = metadata.get('execution_instances') if isinstance(metadata, dict) else None
    matches = [node for node in nodes if isinstance(node, dict) and node.get('task_id') == payload.task_id] if isinstance(nodes, list) else []
    if len(matches) != 1:
        raise HTTPException(409, 'Submitted instance association is unavailable')
    if not any((r.get('protocol'), r.get('uri')) == (payload.protocol, payload.uri) for r in task.get('output_refs', [])):
        raise HTTPException(403, 'Reference is not an output of this task')
    raw, proof = inspect(row, matches[0], task, db, tasks)
    from app.services.data_reference_service import parse_content_preview
    try:
        content = raw.decode('utf-8')
    except UnicodeError:
        raise HTTPException(409, 'Control result is not a supported UTF-8 preview') from None
    result = parse_content_preview(content, task['output_refs'][0]['format'], payload.uri, 'http')
    return {**result, 'evidence': proof}
