"""Opt-in disposable real-model qualification; does not activate contracts.

Requires the private provider-review profile, exact WP3 checkpoint tree and
already installed immutable ML image. All numeric bounds and data are fixtures.
Never reuse this project to bypass unresolved dispatch or reset retained state.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import secrets
import subprocess
import time
from uuid import uuid4

import requests

IMAGE = 'sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f'
TREE = 'd54bbfc62fa6f054a7e1d276ae1ab4092dcb980b'
HERE = Path(__file__).resolve().parent


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Docker operation failed; no fallback or reset attempted')
    return result.stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def request(client, method, url, **kwargs):
    response = client.request(method, url, timeout=20, allow_redirects=False, **kwargs)
    if response.status_code not in {200, 201}:
        raise RuntimeError('Qualification API rejected ' + method + ' request: ' + str(response.status_code))
    return response.json()


def prepare(args):
    root = args.directory.resolve()
    if root.exists():
        raise RuntimeError('Use a NEW ignored directory; existing experiments are never overwritten')
    source = args.wp3.resolve()
    tree = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    untracked = subprocess.check_output(['git', '-C', str(source), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    if any('__pycache__/' not in path and not path.startswith('pytest-cache-files-') for path in untracked):
        raise RuntimeError('Unexpected untracked source in the reproduced worktree')
    if tree != args.expected_tree or dirty:
        raise RuntimeError('Requires the clean reproduced checkpoint tree')
    profile = json.loads((args.review / 'profile.json').read_text())
    if profile.get('kind') != 'isolated-provider-review-v1':
        raise RuntimeError('Requires the isolated provider-review profile')
    api = 'http://127.0.0.1:' + str(profile['api_port'])
    client = requests.Session(); client.trust_env = False
    health = client.get(api + '/health', timeout=5)
    if health.headers.get('X-AI-Effect-Review-Profile') != profile['id']:
        raise RuntimeError('Review API identity differs')
    account = json.loads((args.review / 'credentials.private.json').read_text())['provider_portugal']
    request(client, 'POST', api + '/auth/login', json={k: account[k] for k in ('email', 'password')})
    services = request(client, 'GET', api + '/services?include_archived=true')
    root.mkdir(parents=True)
    # Keep all credentials/operator identities in ignored private local state.
    if __import__('os').name == 'nt':
        owner = subprocess.check_output(['whoami'], text=True).strip()
        subprocess.run(['icacls', str(root), '/inheritance:r', '/grant:r', owner + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], check=True, stdout=subprocess.DEVNULL)
    (root / 'contracts').mkdir(); (root / 'inputs').mkdir()
    common_root = 'use-cases/portugal-node-sidecar/common/'
    common = root / 'source/common'; common.mkdir(parents=True)
    names = subprocess.check_output(['git', '-C', str(source), 'ls-tree', '-r', '--name-only', 'HEAD', common_root], text=True).splitlines()
    source_manifest = {}
    for name in names:
        raw_source = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(source), 'show', 'HEAD:' + name])
        destination = root / 'source' / name.removeprefix('use-cases/portugal-node-sidecar/')
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(raw_source)
        source_manifest[name] = sha(raw_source)
    (root / 'source-manifest.private.json').write_text(json.dumps(source_manifest, indent=2))
    # Source interface bytes are read-only; no existing model/dataset volume.
    raw = docker('exec', 'ai-effect-pt-parameters-ml-1', 'python', '-c',
        "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:600/openapi.json').read().decode())")
    document = json.loads(raw)
    (root / 'source-openapi.private.json').write_text(json.dumps(document))
    contracts = {}
    for method, endpoint, verb, names in [('TrainModel', '/train', 'post', ['epochs', 'batch_size', 'sequence_len']),
                                          ('GenerateData', '/generate', 'get', ['number_of_examples'])]:
        selected_name = args.training_service_name if method == 'TrainModel' else args.generation_service_name
        candidates = [s for s in services if s['operation_name'] == method and s['owner_node'] == 'portugal'
                      and s['name'] == 'REVIEW COPY - ' + selected_name and s['lifecycle_status'] == 'active']
        if len(candidates) != 1:
            raise RuntimeError('Select an unambiguous normal review metadata copy')
        path = api + '/services/' + candidates[0]['id'] + '/parameter-onboarding'
        discovery = request(client, 'POST', path + '/discover', json={'document': document,
            'source_reference': 'local disposable qualification / exact inspected source image ' + IMAGE,
            'operation_id': document['paths'][endpoint][verb]['operationId']})
        parameters = []
        for candidate in discovery['candidates']:
            if candidate['name'] not in names:
                continue
            definition = deepcopy(candidate['definition']); definition.pop('default', None)
            definition.update(minimum=1, maximum=32, required=True,
                description='Disposable software qualification fixture only; no owner-approved limits/defaults')
            parameters.append({'name': candidate['name'], 'source_pointer': candidate['source_pointer'],
                'definition': definition, 'algorithm_mapping': 'Source query ' + candidate['name'] + '; effective model values inspected separately'})
        if {p['name'] for p in parameters} != set(names):
            raise RuntimeError('Source discovery lacks required fixture fields')
        contract = request(client, 'POST', path + '/review', json={'discovery_revision': discovery['revision'],
            'operation_identity': 'urn:local-qualification:fixture:' + method, 'contract_version': '0.1.0',
            'parameters': parameters, 'runtime_support_confirmed': False, 'normal_configuration_tested': False,
            'invalid_configuration_tested': False})
        export = request(client, 'GET', api + '/operation-contracts/' + contract['id'] + '/qualification-capability')
        assert export['qualification_only'] is True and contract['status'] == 'draft'
        assert request(client, 'GET', api + '/services/' + candidates[0]['id'] + '/operation-contract-resolution')['contract'] is None
        (root / 'contracts' / (method + '.json')).write_text(json.dumps(export))
        contracts[method] = contract
    key = secrets.token_urlsafe(48); suffix = uuid4().hex[:12]; project = 'aie-pt-qual-' + suffix
    state = {'project': project, 'namespace': 'fixture_' + suffix, 'image': IMAGE, 'wp3_tree': tree,
             'contracts': contracts, 'key': key, 'connector_url': 'http://127.0.0.1:28190', 'workflow_id': 'wf-qual-' + suffix}
    (root / 'operator.private.json').write_text(json.dumps(state))
    (root / 'control.private.env').write_text('SERVICE_API_KEY=' + key + '\n')
    fixture = 'datetime,load,temperature\n' + ''.join(f'2026-01-01T00:{i:02d}:00,{1 + math.sin(i / 4):.6f},{18 + math.cos(i / 5):.6f}\n' for i in range(32))
    (root / 'inputs' / 'fixture.csv').write_bytes(fixture.encode())
    def bind(path, target):
        return {'type': 'bind', 'source': str(path), 'target': target, 'read_only': True}
    compose = {'name': project, 'services': {
        'ml': {'image': IMAGE, 'pull_policy': 'never', 'command': ['python', '/qualification/ml_probe.py'],
            'environment': {'ML_GRETEL_RELOAD': 'False', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
            'volumes': [{'type': 'volume', 'source': 'models', 'target': '/app/models', 'volume': {'nocopy': True}},
                        'observations:/qualification-evidence', bind(HERE, '/qualification')],
            'networks': ['private'], 'cpus': 2, 'mem_limit': '2g'},
        'connector': {'image': IMAGE, 'pull_policy': 'never', 'command': ['python', '/qualification/connector.py'],
            'env_file': [str(root / 'control.private.env')], 'environment': {
                'SERVICE_PARAMETER_CONTRACT_DIR': '/contracts', 'CONTROL_PARAMETER_STATE_DIR': '/state',
                'CONTROL_PARAMETER_QUALIFICATION_MODE': 'true', 'SYNTHETIC_DATA_URL': 'http://ml:600',
                'SELF_URL': state['connector_url'], 'SYNTHETIC_DATA_USER_NAMESPACE': state['namespace'],
                'SYNTHETIC_DATA_INDEX_COLUMN': 'datetime', 'SYNTHETIC_DATA_INPUT_ROOT': '/inputs'},
            'ports': ['127.0.0.1:28190:8080'], 'networks': ['private', 'loopback'], 'volumes': [
                'state:/state', bind(HERE, '/qualification'), bind(common, '/qualification-source/common'),
                bind(root / 'contracts', '/contracts'), bind(root / 'inputs', '/inputs')]}
        }, 'networks': {'private': {'internal': True}, 'loopback': {}}, 'volumes': {'models': {}, 'observations': {}, 'state': {}}}
    (root / 'compose.private.json').write_text(json.dumps(compose, indent=2))
    print(json.dumps({'prepared': True, 'fixture_only': True, 'draft_exports': len(contracts), 'contracts_activated': 0,
                      'project': project, 'fresh_volumes': ['models', 'observations', 'state'], 'raw_ml_ports_published': 0}))


def run(args):
    root = args.directory.resolve(); state = json.loads((root / 'operator.private.json').read_text())
    compose = ['compose', '-p', state['project'], '-f', str(root / 'compose.private.json')]
    existing = docker('ps', '-a', '--filter', 'label=com.docker.compose.project=' + state['project'], '--format', '{{.ID}}').strip()
    attempt_suffix = ''
    if existing and args.resume_predispatch_failure:
        journal_check = "from pathlib import Path;import json,hashlib;print(json.dumps([{'state':json.loads(p.read_text())['state'],'dispatch_started':json.loads(p.read_text())['dispatch_started'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in Path('/state').glob('cfg-*.json')]))"
        prior = json.loads(docker(*compose, 'exec', '-T', 'connector', 'python', '-c', journal_check))
        models = docker(*compose, 'exec', '-T', 'ml', 'python', '-c', "from pathlib import Path;print(len(list(Path('/app/models').rglob('*'))))").strip()
        observations = docker(*compose, 'exec', '-T', 'ml', 'python', '-c', "from pathlib import Path;print(len(list(Path('/qualification-evidence').iterdir())))").strip()
        if (not prior or any(r['state'] != 'failed' or r['dispatch_started'] is not False for r in prior)
                or models != '0' or observations != '0'):
            raise RuntimeError('No safe pre-dispatch-only reconciliation is established; preserve all state')
        with (root / 'predispatch-reconciliation.private.json').open('x') as stream:
            json.dump({'prior_journals': prior, 'models': 0, 'observations': 0, 'action': 'new task identities; old failed receipts retained'}, stream)
        attempt_suffix = '_after_startup_check'
    elif existing:
        if not args.resume_undispatched:
            raise RuntimeError('Project already exists: inspect retained outcomes; never rerun or reset automatically')
        journals = docker(*compose, 'exec', '-T', 'connector', 'python', '-c', "from pathlib import Path;print(len(list(Path('/state').glob('cfg-*.json'))))").strip()
        observations = docker(*compose, 'exec', '-T', 'ml', 'python', '-c', "from pathlib import Path;print(len(list(Path('/qualification-evidence').iterdir())))").strip()
        if journals != '0' or observations != '0':
            raise RuntimeError('Existing work is present: preserve and reconcile; qualification was not restarted')
        inventory = "from pathlib import Path;import hashlib,json;root=Path('/app/models');print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},sort_keys=True))"
        mounted = docker(*compose, 'exec', '-T', 'ml', 'python', '-c', inventory).strip()
        embedded = docker('run', '--rm', '--network', 'none', '--read-only', '--entrypoint', 'python', IMAGE, '-c', inventory).strip()
        if mounted != embedded:
            raise RuntimeError('Model storage differs from untouched image seed; preserve and reconcile')
        configuration = json.loads((root / 'compose.private.json').read_text())
        configuration['networks']['loopback'] = {}
        configuration['services']['connector']['networks'] = ['private', 'loopback']
        # Docker copied an embedded model from the image into the first volume.
        # Preserve that volume; mount a NEW nocopy volume before any dispatch.
        configuration['volumes']['empty_models'] = {}
        configuration['services']['ml']['volumes'][0] = {'type': 'volume', 'source': 'empty_models', 'target': '/app/models', 'volume': {'nocopy': True}}
        (root / 'compose.private.json').write_text(json.dumps(configuration, indent=2))
    docker(*compose, 'up', '-d', '--no-build', '--pull', 'never')
    for _ in range(90):
        ready = subprocess.run(['docker', *compose, 'exec', '-T', 'connector', 'python', '-c',
            "import urllib.request;print(urllib.request.urlopen('http://ml:600/openapi.json',timeout=2).status)"], capture_output=True, text=True)
        if ready.returncode == 0 and ready.stdout.strip() == '200':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Raw ML interface not ready; no configured request was dispatched')
    client = requests.Session(); client.trust_env = False; client.headers['Authorization'] = 'Bearer ' + state['key']
    base = state['connector_url']
    for _ in range(90):
        try:
            if client.get(base + '/control/capabilities', timeout=2).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('New connector not ready; preserve project for operator inspection')
    # No API or progress-only claim: wait for immutable receipts, then inspect
    # the actual saved torch config and weights recorded by real DGAN.
    def configured(method, task, values, ref):
        contract = state['contracts'][method]
        return {'method': method, 'workflow_id': state['workflow_id'], 'task_id': task, 'inputs': [ref],
            'configuration': {'contract_id': contract['id'], 'contract_version': contract['contract_version'],
                'operation_identity': contract['operation_identity'], 'schema_version': '1.0',
                'instance_id': 'fixture-' + task, 'parameters': values}}
    def finish(payload):
        accepted = request(client, 'POST', base + '/control/execute', json=payload)
        task = accepted['task_id']; deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            receipt = request(client, 'GET', base + '/control/receipt/' + task)
            if receipt['state'] not in {'queued', 'running'}:
                if receipt['state'] != 'complete':
                    (root / 'failed-receipt.private.json').write_text(json.dumps(receipt))
                    raise RuntimeError('Model outcome did not establish completion; project retained, do not resubmit')
                return receipt
            time.sleep(.2)
        raise RuntimeError('Qualification time ceiling reached; preserve state and reconcile before any further dispatch')
    records = []; previous = []; private = []
    for index, epochs, sequences in [(1, 1, 2), (2, 2, 3)]:
        payload = configured('TrainModel', 'task_fixture_train_' + str(index) + attempt_suffix, {'epochs': epochs, 'batch_size': 16, 'sequence_len': 4},
            {'protocol': 'file', 'uri': '/inputs/fixture.csv', 'format': 'csv'})
        train = finish(payload)
        generate = finish(configured('GenerateData', 'task_fixture_generate_' + str(index) + attempt_suffix, {'number_of_examples': sequences}, train['output']))
        raw = client.get(generate['output']['uri'], timeout=10).content
        assert sha(raw) == generate['output_sha256'] and generate['observed_sequence_count'] == sequences
        assert generate['csv_data_rows'] == sequences * 4
        assert generate['model_binding']['producer_task_id'] == train['service_task_id']
        model_name = train['delivered_query']['model_name']
        model = json.loads(docker(*compose, 'exec', '-T', 'ml', 'python', '-c',
            "from pathlib import Path;print(Path('/qualification-evidence/" + model_name + ".json').read_text())"))
        assert model['saved_config'] == model['effective']
        assert model['effective']['epochs'] == epochs and model['effective']['batch_size'] == 8
        assert len(model['observed_training']) == epochs and model['tensor_counts']['generate_state_dict'] > 0
        for url, old in previous:
            assert client.get(url, timeout=10).content == old
        previous.append((generate['output']['uri'], raw))
        private.append({'train': train, 'generate': generate, 'payload': payload})
        records.append({'training_task': train['task_id'], 'generation_task': generate['task_id'],
            'requested': payload['configuration']['parameters'], 'effective': model['effective'], 'observed': model['observed_training'],
            'input_sha256': train['input_sha256'], 'model_files': model['model_files'], 'model_class': model['model_class'],
            'saved_config': model['saved_config'], 'tensor_counts': model['tensor_counts'],
            'output_sha256': generate['output_sha256'], 'csv_sequences': sequences, 'csv_data_rows': generate['csv_data_rows'],
            'upstream_interface_sha256': train['upstream_interface_sha256'], 'source_receipt_sha256': sha(json.dumps(train, sort_keys=True).encode())})
    invalid = deepcopy(private[0]['payload']); invalid['task_id'] = 'task_fixture_invalid'; invalid['configuration']['parameters']['epochs'] = True
    before = docker(*compose, 'exec', '-T', 'connector', 'python', '-c', "from pathlib import Path;print(len(list(Path('/state').glob('cfg-*.json'))))")
    assert client.post(base + '/control/execute', json=invalid, timeout=5).status_code == 422
    after = docker(*compose, 'exec', '-T', 'connector', 'python', '-c', "from pathlib import Path;print(len(list(Path('/state').glob('cfg-*.json'))))")
    assert before == after
    assert client.post(base + '/control/execute', json=private[0]['payload'], timeout=5).status_code == 409
    for url, old in previous:
        assert client.get(url, timeout=10).content == old
    assert requests.get(base + '/control/capabilities', timeout=5).status_code == 401
    (root / 'receipts.private.json').write_text(json.dumps(private, indent=2))
    evidence = {'status': 'PASS', 'fixture_only': True, 'real_model': True, 'algorithm_double': False,
        'image': IMAGE, 'wp3_tree': state['wp3_tree'], 'project': state['project'], 'workflow_id': state['workflow_id'],
        'fresh_model_state_observation_volumes': True, 'private_internal_network': True, 'raw_ml_published': False,
        'contracts_activated': 0, 'provider_review_attestations': False, 'runs': records,
        'invalid_caused_no_journal_or_dispatch': before == after, 'replay_denied': True, 'old_output_bytes_unchanged': True,
        'unauthenticated_control_denied': True, 'owner_limits_defaults_data_suitability_approved': False,
        'normal_portal_run_verified': False, 'paid_provider_calls': 0}
    (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'real_model_fixture_runs': 2, 'requested_batch': 16, 'effective_batch': 8,
                      'csv_sequences': [2, 3], 'csv_rows': [8, 12], 'old_bytes_unchanged': True, 'contracts_activated': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--wp3', type=Path)
    parser.add_argument('--expected-tree', default=TREE)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--training-service-name')
    parser.add_argument('--generation-service-name')
    parser.add_argument('--fixture-only', action='store_true', required=True)
    parser.add_argument('--resume-undispatched', action='store_true')
    parser.add_argument('--resume-predispatch-failure', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare': prepare(args)
    else: run(args)
