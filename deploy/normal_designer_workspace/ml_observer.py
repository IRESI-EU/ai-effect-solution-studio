"""Opt-in real-DGAN observation adapter for a fresh private development runtime.

No model doubles. The unchanged source API binds CSV/query inputs. Observations
come from actual function arguments, real saved config and loaded weight tensors.
"""
from contextvars import ContextVar
from email.parser import BytesParser
from email.policy import default
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/observation-contract')
import runtime_observation as contract
import torch
import dgan

torch.set_num_threads(1)
current = ContextVar('real_execution', default=None)
original_train, original_save, original_load, original_generate = dgan.train, dgan.save_train_result, dgan.load_train_result, dgan.generate
models = {}
directory = Path('/qualification-evidence')


def model_record(result, path):
    model = result.model
    weight_hash = hashlib.sha256(); count = 0
    for group in ('generator', 'feature_discriminator', 'attribute_discriminator'):
        module = getattr(model, group, None)
        if module is None: continue
        for name, tensor in sorted(module.state_dict().items()):
            weight_hash.update((group + ':' + name).encode())
            weight_hash.update(tensor.detach().cpu().contiguous().numpy().tobytes())
            count += tensor.numel()
    return {'sha256': hashlib.sha256((Path(path) / 'model.pt').read_bytes()).hexdigest(),
            'weights_sha256': weight_hash.hexdigest(), 'weight_elements': count}


def observation(result, observed, path, basis):
    context = current.get()
    if context is None: return
    config = context['configuration']
    context['observation'] = {'schema_version': '1.0', 'kind': 'algorithm-settings-v1',
        'binding': {'workflow_id': context['workflow_id'], 'task_id': context['task_id'],
            'instance_id': config['instance_id'], 'operation_identity': config['operation_identity'],
            'configuration_sha256': contract.digest(config), 'parameter_contract_sha256': context['parameter_contract_sha256'],
            'input_sha256': context['input_sha256']},
        'requested_parameters': config['parameters'], 'observed_parameters': observed,
        'model': model_record(result, path), 'implementation': {'name': type(result.model).__module__ + '.' + type(result.model).__name__,
            'source_sha256': hashlib.sha256(Path('/app/dgan.py').read_bytes()).hexdigest(),
            'image_sha256': os.environ['OBSERVED_ML_IMAGE']}, 'basis': basis}


def train(frame, **kwargs):
    context = current.get()
    if context and any(kwargs.get(k) != v for k, v in context['configuration']['parameters'].items()):
        raise ValueError('Observed train arguments differ from execution context')
    return original_train(frame, **kwargs)


def save(result, path):
    original_save(result, path)
    # Inspect only the model just created inside this new runtime.
    saved = torch.load(str(Path(path) / 'model.pt'), map_location='cpu')
    config = result.model.config.to_dict()
    assert all(config[k] == saved['config'][k] for k in ('epochs', 'batch_size', 'max_sequence_len'))
    values = {'epochs': config['epochs'], 'batch_size': config['batch_size'], 'sequence_len': config['max_sequence_len']}
    context = current.get()
    if context:
        observation(result, {k: values[k] for k in context['configuration']['parameters']}, path,
            'Actual DGAN training returned; freshly saved model config and real trained weight tensors inspected')


def load(path):
    result = original_load(path)
    models[id(result)] = str(path)
    return result


def generate(result, num_examples=1):
    values = original_generate(result, num_examples=num_examples)
    path = models.pop(id(result))
    context = current.get()
    if context:
        observation(result, {'number_of_examples': num_examples}, path,
            'Actual DGAN generate call and freshly loaded model weights inspected; output CSV counted separately')
    return values


dgan.train, dgan.save_train_result, dgan.load_train_result, dgan.generate = train, save, load, generate
import main
from fastapi import Header, HTTPException, Request, Response


@main.app.middleware('http')
async def record_execution(request: Request, call_next):
    raw_context = request.headers.get('X-AI-Effect-Execution')
    if request.url.path not in {'/train', '/generate'} or raw_context is None:
        return await call_next(request)
    key = os.environ['RUNTIME_OBSERVATION_API_KEY']
    if not secrets.compare_digest(request.headers.get('X-AI-Effect-Observation-Key', ''), key):
        return Response(status_code=401)
    context = json.loads(raw_context)
    if not re.fullmatch('cfg-[a-f0-9]{64}', context['service_task_id']):
        return Response(status_code=422)
    if request.url.path == '/train':
        body = await request.body()
        multipart = BytesParser(policy=default).parsebytes(b'Content-Type: ' + request.headers['content-type'].encode() + b'\r\n\r\n' + body)
        inputs = [p.get_payload(decode=True) for p in multipart.iter_parts() if p.get_param('name', header='content-disposition') == 'uploaded_file']
        if len(inputs) != 1 or hashlib.sha256(inputs[0]).hexdigest() != context['input_sha256']:
            return Response(status_code=422)
    token = current.set(context)
    try:
        response = await call_next(request)
        body = b''.join([chunk async for chunk in response.body_iterator])
        if response.status_code == 200:
            document = context['observation']
            document['binding']['source_response_sha256'] = hashlib.sha256(body).hexdigest()
            contract.validate(document, workflow_id=context['workflow_id'], task_id=context['task_id'],
                configuration=context['configuration'], parameter_contract_sha256=context['parameter_contract_sha256'],
                input_sha256=context['input_sha256'], source_response_sha256=document['binding']['source_response_sha256'])
            with (directory / (context['service_task_id'] + '.json')).open('x') as stream:
                json.dump(document, stream, sort_keys=True, allow_nan=False)
        return Response(body, status_code=response.status_code, headers=dict(response.headers))
    finally:
        current.reset(token)


@main.app.get('/runtime-observations/{identity}')
def get_observation(identity: str, authorization: str = Header(default='')):
    if not secrets.compare_digest(authorization, 'Bearer ' + os.environ['RUNTIME_OBSERVATION_API_KEY']):
        raise HTTPException(401, 'Observation authorization required')
    if not re.fullmatch('cfg-[a-f0-9]{64}', identity): raise HTTPException(404, 'Unknown observation')
    path = directory / (identity + '.json')
    if not path.is_file(): raise HTTPException(404, 'Observation is not complete')
    return json.loads(path.read_text())


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(main.app, host='0.0.0.0', port=600, log_level='warning')
