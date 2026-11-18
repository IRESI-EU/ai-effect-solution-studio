"""Read-only reinspection of fresh trusted local models in the private ML container."""
import hashlib
from enum import Enum
import json
from pathlib import Path
import sys

sys.path.insert(0, '/app')
import dgan

records=[]
def encode_enum(value):
    if isinstance(value,Enum): return {'enum_type':type(value).__module__+'.'+type(value).__name__,'name':value.name,'value':value.value}
    raise TypeError('Unrecognized saved configuration value')

for model_file in sorted(Path('/app/models').glob('*/*/model.pt')):
    result=dgan.load_train_result(str(model_file.parent))
    digest=hashlib.sha256();count=0
    for group in ('generator','feature_discriminator','attribute_discriminator'):
        module=getattr(result.model,group,None)
        if module is None:continue
        for name,tensor in sorted(module.state_dict().items()):
            digest.update((group+':'+name).encode());digest.update(tensor.detach().cpu().contiguous().numpy().tobytes());count+=tensor.numel()
    config=result.model.config.to_dict()
    records.append({'model_sha256':hashlib.sha256(model_file.read_bytes()).hexdigest(),
        'weights_sha256':digest.hexdigest(),'weight_elements':count,
        'saved_configuration_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False,default=encode_enum).encode()).hexdigest(),
        'saved_configuration':{k:config[k] for k in ('epochs','batch_size','max_sequence_len')}})
print(json.dumps({'boundary':'Fresh saved model reload in an independent read-only process; no training dispatch','models':records}))
