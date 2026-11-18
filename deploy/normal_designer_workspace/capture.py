"""Read-only diagnostics AFTER a browser-created Run; never dispatches tasks."""
import argparse
import hashlib
import json
from pathlib import Path

from fixtures import call, login, session


def capture(directory, workflow, label):
    p = json.loads((directory / 'profile.private.json').read_text())
    accounts = json.loads((directory / 'credentials.private.json').read_text())
    client = session(); login(client, p['api_url'], accounts['designer'])
    def get(path): return call(client, 'GET', p['api_url'], path)
    snapshot = get('/workflows/' + workflow + '/submitted-configuration')
    evidence = get('/workflows/' + workflow + '/instance-evidence')
    tasks = get('/orchestrator/workflows/' + workflow + '/tasks')['tasks']
    assert evidence['state'] == 'available', evidence
    control = session(); control.headers['Authorization'] = 'Bearer ' + p['control_key']
    records = []
    for task in tasks:
        if not task.get('output_refs'): continue
        ref = task['output_refs'][0]
        preview = call(client, 'POST', p['api_url'], '/data-references/preview', json={**ref, 'workflow_id': workflow, 'task_id': task['task_id']})
        physical = 'cfg-' + hashlib.sha256((workflow + '\0' + task['task_id']).encode()).hexdigest()
        receipt = call(control, 'GET', p['connector_url'], '/control/receipt/' + physical)
        response = control.get(p['connector_url'] + '/control/data/' + physical, timeout=10)
        response.raise_for_status(); raw = response.content
        assert hashlib.sha256(raw).hexdigest() == receipt['output_sha256']
        artifact = directory / (label + '-' + task['task_id'] + '.private.bin')
        if artifact.exists(): assert artifact.read_bytes() == raw
        else:
            with artifact.open('xb') as stream: stream.write(raw)
        records.append({'task': task, 'preview': preview, 'receipt': receipt})
    other = session(); login(other, p['api_url'], accounts['other_designer'])
    denied = {}
    for route in ('submitted-configuration', 'instance-evidence'):
        code = other.get(p['api_url'] + '/workflows/' + workflow + '/' + route, timeout=10).status_code
        assert code == 403; denied[route] = code
    code = other.get(p['api_url'] + '/orchestrator/workflows/' + workflow + '/tasks',timeout=10).status_code
    assert code == 403; denied['orchestrator_tasks'] = code
    task = records[-1]['task']; ref = task['output_refs'][0]
    code = other.post(p['api_url'] + '/data-references/preview', json={**ref,'workflow_id':workflow,'task_id':task['task_id']},timeout=10).status_code
    assert code == 403; denied['preview'] = code
    document = {'workflow_id': workflow, 'snapshot': snapshot, 'evidence': evidence, 'records': records, 'other_designer_denied': denied}
    destination = directory / (label + '.private.json')
    if destination.exists():
        old = json.loads(destination.read_text())
        assert old['snapshot'] == snapshot
        assert [(r['receipt']['output_sha256'],r['receipt']['runtime_observation_sha256']) for r in old['records']] == [(r['receipt']['output_sha256'],r['receipt']['runtime_observation_sha256']) for r in records]
        print(json.dumps({'workflow':workflow,'original_snapshot_observations_and_output_bytes_unchanged':True}))
    else:
        destination.write_text(json.dumps(document, indent=2))
        print(json.dumps({'workflow':workflow,'tasks':len(records),'owned_preview_verified':True,'other_designer_denied':denied}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--workflow',required=True);parser.add_argument('--label',required=True)
    args=parser.parse_args();capture(args.directory.resolve(),args.workflow,args.label)
