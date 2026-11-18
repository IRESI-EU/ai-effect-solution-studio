"""Explicit synthetic observation records; not real model/browser acceptance."""
from copy import deepcopy
import json

import pytest
from app.models.execution_submission import InstanceEvidenceReceipt
from app.services import runtime_observation as observation
from test_owned_control_result import remote, preview  # noqa: F401
from test_native_instance_evidence import proof  # noqa: F401


def install(remote):
    receipt = remote.remote['receipt']
    receipt['input_sha256'] = 'd' * 64; receipt['source_response_sha256'] = receipt['output_sha256']
    config = receipt['configuration']
    value = {'schema_version':'1.0','kind':'algorithm-settings-v1',
        'binding':{'workflow_id':receipt['workflow_id'],'task_id':receipt['task_id'],'instance_id':config['instance_id'],
            'operation_identity':config['operation_identity'],'configuration_sha256':observation.digest(config),
            'parameter_contract_sha256':receipt['parameter_contract_sha256'],'input_sha256':receipt['input_sha256'],
            'source_response_sha256':receipt['source_response_sha256']},
        'requested_parameters':config['parameters'],'observed_parameters':{'count':1},
        'model':{'sha256':'a'*64,'weights_sha256':'b'*64,'weight_elements':12},
        'implementation':{'name':'EXPLICIT TEST DOUBLE','source_sha256':'c'*64,'image_sha256':'sha256:'+'e'*64},
        'basis':'Synthetic observation fixture, no algorithm claim'}
    receipt['runtime_observation'] = value; receipt['runtime_observation_sha256'] = observation.digest(value)
    targets=json.loads(remote.remote['target'].read_text());targets['targets'][0]['observation_contracts']=['algorithm-settings-v1']
    remote.remote['target'].write_text(json.dumps(targets))
    def save():
        remote.remote['responses']['/control/receipt/'+remote.remote['physical']]=(200,json.dumps(receipt).encode())
    save();return value,receipt,save


def test_explicit_verified_observation_can_differ_from_requested_delivery(remote):
    install(remote)
    response=preview(remote)
    assert response.status_code==200,response.text
    proof=response.json()['evidence']
    assert proof['delivered_parameters']=={'count':2} and proof['algorithm_consumed']=={'count':1}
    assert proof['evidence_level']=='authenticated_algorithm_observation'


@pytest.mark.parametrize('field',['workflow_id','task_id','instance_id','operation_identity','configuration_sha256','parameter_contract_sha256','input_sha256','source_response_sha256'])
def test_observation_wrong_binding_is_rejected_before_receipt_is_pinned(remote,field):
    value,receipt,save=install(remote);value['binding'][field]='changed';receipt['runtime_observation_sha256']=observation.digest(value);save()
    assert preview(remote).status_code==409
    assert remote.db.get(InstanceEvidenceReceipt,(remote.row.id,'task_test')) is None


@pytest.mark.parametrize('change',['digest','untrusted','type','keys','model','weights','future','shape','requested'])
def test_observation_must_be_explicit_typed_complete_and_hash_bound(remote,change):
    value,receipt,save=install(remote)
    if change=='untrusted':
        targets=json.loads(remote.remote['target'].read_text());targets['targets'][0].pop('observation_contracts');remote.remote['target'].write_text(json.dumps(targets))
    if change=='type':value['observed_parameters']['count']=True
    if change=='keys':value['observed_parameters']['other']=1
    if change=='model':value['model']['sha256']='bad'
    if change=='weights':value['model']['weight_elements']=0
    if change=='future':value['schema_version']='99'
    if change=='shape':value['unknown']=True
    if change=='requested':value['requested_parameters']={'count':3}
    receipt['runtime_observation_sha256']='f'*64 if change=='digest' else observation.digest(value);save()
    assert preview(remote).status_code==409
    assert remote.db.get(InstanceEvidenceReceipt,(remote.row.id,'task_test')) is None
