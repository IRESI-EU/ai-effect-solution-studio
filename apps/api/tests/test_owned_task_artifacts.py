"""Synthetic artifact bindings at the real authenticated owned preview route."""
import hashlib
import json

import pytest
from app.models.execution_submission import ExecutionSubmission,InstanceEvidenceReceipt
from app.core.config import settings
from test_owned_artifact_preview import observed,request


def install(observed,db):
    state,_,parent=observed;task=state['tasks'][0]
    task.update(node_key='generic:Draw',status='completed',output_refs=[{'protocol':'file','uri':'/data/wf-owned/result.json','format':'json'}])
    task.pop('result')
    row=db.get(ExecutionSubmission,'submitted-owned')
    value={'request':{},'runtime_destination':settings.orchestrator_base_url,'compiled':{'solution_studio_metadata':{'execution_instances':[
        {'task_id':'task_owned','node_key':'generic:Draw','configuration':None}]}}}
    row.submitted=value;row.submitted_sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest();db.commit()
    svg=parent.parent/'task_owned_network_001.svg';svg.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><text>FIXTURE</text></svg>')
    item={'protocol':'file','uri':'/data/wf-owned/'+svg.name,'format':'svg','sha256':hashlib.sha256(svg.read_bytes()).hexdigest(),'bytes':svg.stat().st_size}
    manifest={'schema_version':'1.0','kind':'task-artifacts-v1','workflow_id':'wf-owned','task_id':'task_owned','files':[item]}
    parent.write_text(json.dumps({'artifact_manifest':manifest}))
    return parent,svg,manifest,item


def test_owned_task_derivative_hashes_and_parent_are_pinned(environment,observed,db):
    parent,svg,manifest,item=install(observed,db)
    response=request(environment,uri=item['uri'],format='svg')
    assert response.status_code==200 and response.json()['available']
    assert db.get(InstanceEvidenceReceipt,('submitted-owned','task_owned'))
    # Rehashing replacement SVG bytes inside a modified parent cannot change history.
    svg.write_bytes(b'<svg>CHANGED</svg>');item.update(sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),bytes=svg.stat().st_size)
    parent.write_text(json.dumps({'artifact_manifest':manifest}))
    assert request(environment,uri=item['uri'],format='svg').status_code==409


@pytest.mark.parametrize('mutation',['workflow','task','node','schema','digest','bytes','other-task','xml','duplicate'])
def test_invalid_artifact_does_not_gain_authority_or_pin_receipt(environment,observed,db,mutation):
    parent,svg,manifest,item=install(observed,db)
    if mutation=='workflow':manifest['workflow_id']='wf-other'
    if mutation=='task':manifest['task_id']='task_other'
    if mutation=='node':observed[0]['tasks'][0]['node_key']='wrong:Task'
    if mutation=='schema':manifest['schema_version']='99'
    if mutation=='digest':item['sha256']='a'*64
    if mutation=='bytes':item['bytes']=True
    if mutation=='other-task':
        other=svg.with_name('other_network_001.svg');other.write_bytes(svg.read_bytes());item['uri']='/data/wf-owned/'+other.name
    if mutation=='xml':
        svg.write_bytes(b'<!DOCTYPE svg><svg/>');item.update(sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),bytes=svg.stat().st_size)
    if mutation=='duplicate':manifest['files'].append(dict(item))
    parent.write_text(json.dumps({'artifact_manifest':manifest}))
    assert request(environment,uri=item['uri'],format='svg').status_code in (403,409)
    assert db.get(InstanceEvidenceReceipt,('submitted-owned','task_owned')) is None
