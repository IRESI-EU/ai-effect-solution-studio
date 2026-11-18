"""Disposable instrumentation around unchanged source and real DGAN; no doubles.

Only install in a fresh private qualification container. No existing models
are loaded. Observations are written to its dedicated evidence volume.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/app')
import torch
import dgan

torch.set_num_threads(1)
original_train, original_save, original_generate = dgan.train, dgan.save_train_result, dgan.generate
observed = {}


def train(frame, **kwargs):
    observations = []
    callback = kwargs.get('progress_callback')
    def progress(info):
        observations.append({'epoch': info.epoch + 1, 'batch': info.batch + 1,
                             'total_epochs': info.total_epochs, 'total_batches': info.total_batches})
        if callback:
            callback(info)
    kwargs['progress_callback'] = progress
    result = original_train(frame, **kwargs)
    observed[id(result)] = {'fixture_only': True, 'algorithm_double': False,
        'requested': {k: v for k, v in kwargs.items() if k != 'progress_callback'},
        'effective': {k: result.model.config.to_dict()[k] for k in ('epochs', 'batch_size', 'max_sequence_len', 'sample_len')},
        'model_class': type(result.model).__module__ + '.' + type(result.model).__name__,
        'observed_training': observations, 'training_rows': len(frame)}
    return result


def save(result, path):
    original_save(result, path)
    folder = Path(path)
    record = observed.pop(id(result))
    # Deserialize only the model produced above in this fresh container.
    state = torch.load(str(folder / 'model.pt'), map_location='cpu')
    record['saved_config'] = {k: state['config'][k] for k in ('epochs', 'batch_size', 'max_sequence_len', 'sample_len')}
    record['tensor_counts'] = {key: sum(v.numel() for v in state[key].values()) for key in
                              ('generate_state_dict', 'feature_discriminator_state_dict')}
    record['model_files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    target = Path('/qualification-evidence') / (folder.name + '.json')
    with target.open('x') as stream:
        json.dump(record, stream, sort_keys=True)


def generate(result, num_examples=1):
    values = original_generate(result, num_examples=num_examples)
    assert len(values) == num_examples
    return values


dgan.train, dgan.save_train_result, dgan.generate = train, save, generate
import main
import uvicorn
uvicorn.run(main.app, host='0.0.0.0', port=600, log_level='warning')
