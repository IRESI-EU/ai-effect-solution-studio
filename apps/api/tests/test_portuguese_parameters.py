"""Offline actual Portal routes; catalogue contracts are the experimental export.

No algorithm, provider, runtime qualification or PostgreSQL concurrency claim.
"""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.operation_contract import OperationContractWrite
from app.services.parameter_values import effective_parameters
from app.models.execution_submission import ExecutionSubmission

CONTRACTS=json.loads((Path(__file__).resolve().parents[3]/'deploy/portuguese_sandbox/contracts.json').read_text())


@pytest.fixture
def registered(environment):
    with SessionLocal() as db:
        for record in CONTRACTS:
            value=OperationContractWrite.model_validate({k:v for k,v in record.items() if k not in {'id','service_id'}})
            db.add(Service(id=record['service_id'],name='EXPERIMENTAL '+value.runtime_operation_name,
                provider='Platform-controlled sandbox; no partner approval',category='experimental-portuguese',
                description='Isolated parameter qualification only',input_type='opaque reference',output_type='sequences',
                status='approved',lifecycle_status='active',operation_name=value.runtime_operation_name,container_name='pt-'+value.runtime_operation_name,
                interface_type='control',orchestration_mode='sidecar',adapter_type='platform-experimental',
                contract_uri=value.operation_identity,internal_host='pt-adapter',internal_port='8080'))
            db.flush()
            values=value.model_dump()
            values['definition']=value.definition.model_dump(mode='json',exclude_none=True)
            db.add(OperationContract(id=record['id'],service_id=record['service_id'],status='active',**values))
        db.commit()
    return environment


def node(identifier,count):
    return {'id':identifier,'type':'default','position':{'x':100,'y':100},'data':{'node_kind':'service',
        'service':{'id':'pt-experimental-GenerateData'},'configuration':{'contract_id':'pt-sandbox-generate-v1',
        'contract_version':'0.1.0','parameters':{'number_of_examples':count}}}}


def workflow(saved):
    return {'name':saved['name'],'solution_id':saved['id'],'expected_updated_at':saved['updated_at'],
        'nodes':[{'node_id':n['id'],'service_id':n['data']['service']['id'],'container_name':'ignored',
            'operation_name':'GenerateData','configuration':n['data']['configuration']} for n in saved['nodes']],
        'edges':[],'run_input':{'model_ref':'pt-approved-test-model'}}


def test_save_copy_compile_independent_instances_and_defaults(registered):
    client=registered
    assert effective_parameters(CONTRACTS[0]['definition']['execution_parameters'],{})=={'number_of_examples':10}
    saved=client.post('/solutions',json={'name':'EXPERIMENTAL Portuguese sequences','nodes':[node('first',10),node('second',20)],'edges':[]})
    assert saved.status_code==200,saved.text
    saved=client.get('/solutions/'+saved.json()['id']).json()
    copy=client.post('/solutions',json={'name':'Independent experimental copy','nodes':deepcopy(saved['nodes']),'edges':[]}).json()
    assert copy['id']!=saved['id'] and copy['nodes']==saved['nodes']
    response=client.post('/workflows/compile',json=workflow(copy));assert response.status_code==200,response.text
    compiled=response.json();configs=compiled['task_configurations']
    assert {v['instance_id']:v['parameters']['number_of_examples'] for v in configs.values()}=={'first':10,'second':20}
    assert len(configs)==2 and all(v['operation_identity']=='urn:aieffect:experimental:portuguese:generate-data' for v in configs.values())
    assert 'services_api_key' not in compiled
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.models.user import User
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,'other')
        assert client.get('/solutions/'+saved['id']).status_code==403
    app.dependency_overrides.pop(get_current_user)


def test_submitted_parameters_are_immutable_after_saved_design_changes(registered):
    from app.services.workflow_compiler import compile_to_wp3_payload
    from app.schemas.workflow_submit import WorkflowSubmitRequest
    from app.services import execution_submission
    from app.models.user import User
    client=registered;saved=client.post('/solutions',json={'name':'Experimental immutable','nodes':[node('first',10)],'edges':[]}).json()
    request=WorkflowSubmitRequest.model_validate(workflow(saved))
    with SessionLocal() as db:
        compiled=compile_to_wp3_payload(request,db)
        record=execution_submission.prepare(db,db.get(User,'designer'),request,compiled)
        snapshot=deepcopy(execution_submission.view(record));identity=record.id
    updated=deepcopy(saved['nodes']);updated[0]['data']['configuration']['parameters']['number_of_examples']=20
    assert client.put('/solutions/'+saved['id'],json={'nodes':updated,'expected_updated_at':saved['updated_at']}).status_code==200
    with SessionLocal() as db:assert execution_submission.view(db.get(ExecutionSubmission,identity))==snapshot
