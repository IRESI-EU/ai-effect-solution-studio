"""Normal provider/admin onboarding of Danish SOFTWARE FIXTURES, no DB seeding."""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat
import sys
import time
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'normal_designer_workspace'))
from fixtures import call,session,login


def complete(client,base,payload):
    accepted=call(client,'POST',base,'/control/execute',json=payload)
    physical=accepted['task_id'];deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        value=call(client,'GET',base,'/control/status/'+physical)
        if value['status'] not in {'queued','running'}:break
        time.sleep(.1)
    if value['status']!='complete':raise RuntimeError('Real native fixture qualification failed; preserve private diagnostics')
    return call(client,'GET',base,'/control/output/'+physical)['output']


def readonly_export(directory,value,phase):
    raw=(json.dumps(value,indent=2)+'\n').encode();archive=directory/'contracts'/('generator-'+phase+'.json')
    with archive.open('xb') as stream:stream.write(raw)
    archive.chmod(stat.S_IREAD)
    current=directory/'contracts/generator.json'
    if current.exists():current.chmod(stat.S_IREAD|stat.S_IWRITE)
    current.write_bytes(raw);current.chmod(stat.S_IREAD)
    return hashlib.sha256(raw).hexdigest()


def onboard(directory):
    p=json.loads((directory/'profile.private.json').read_text());accounts=json.loads((directory/'credentials.private.json').read_text())
    if (directory/'fixtures.private.json').exists():raise RuntimeError('Fixture onboarding already recorded; never duplicate it')
    base=p['api_url'];admin=session();login(admin,base,accounts['administrator'])
    for role,node,key in [('node_manager','denmark','provider'),('solution_designer',None,'designer'),('solution_designer',None,'other_designer')]:
        user=call(admin,'POST',base,'/auth/register',json={**accounts[key],'display_name':'Development '+key.replace('_',' '),'requested_role':role,'node':node})
        call(admin,'POST',base,'/admin/users/'+user['id']+'/approve',json={'role':role,'node':node})
    provider=session();login(provider,base,accounts['provider'])
    control=session();control.headers['Authorization']='Bearer '+p['control_key']
    values={'allow_hx':True,'allow_bypass':True,'how_many':1}
    schema={'type':'object','properties':{
        'allow_hx':{'type':'boolean','title':'Heat exchangers','description':'Source enumerator allow_hx argument; DEVELOPMENT SOFTWARE FIXTURE only','default':True},
        'allow_bypass':{'type':'boolean','title':'Bypasses','description':'Source enumerator allow_bypass argument; DEVELOPMENT SOFTWARE FIXTURE only','default':True},
        'how_many':{'type':'integer','title':'Maximum candidate layouts','description':'Source enumerate_networks max_results; up to this number; DEVELOPMENT SOFTWARE FIXTURE bounds, not Danish scientific approval','default':1,'minimum':1,'maximum':4}}}
    topology={'name':'networks','semantic_concept':'urn:development-fixture:danish-topologies','schema_ref':'urn:development-fixture:danish-topology-report:1',
        'value_representation':'data_reference','data_reference_protocols':['file'],'content_types':['application/json'],'min_cardinality':1,'max_cardinality':1}
    run_input={**topology,'name':'run_configuration','semantic_concept':'urn:development-fixture:danish-run-configuration',
        'schema_ref':'urn:development-fixture:danish-run-config:1','data_reference_protocols':['inline','file'],'required':True,'source_requirement':'workflow_input'}
    rendered={**topology,'name':'rendered_report','semantic_concept':'urn:development-fixture:danish-drawings','schema_ref':'urn:development-fixture:danish-rendered-report:1'}
    records=[]
    for suffix,operation,port in [('Generator','GenerateTopology',28196),('Drawing A','RenderTopologies',28197),('Drawing B','RenderTopologies',28198)]:
        manifest={'schema_version':'1.0','service':{'id':'dev-danish-'+uuid4().hex,'name':'DEVELOPMENT SOFTWARE FIXTURE — Danish '+suffix,
            'provider':'Danish source software acceptance fixture','category':'Development software fixtures',
            'description':('Enumerates feasible district-heating topology candidates from separate run configuration; adjustable maximum count.' if operation=='GenerateTopology'
                else 'Renders drawings from the published topology report. Compatible drawing view '+suffix[-1]+'. No editable settings.')+' Software evidence only; no Danish partner scientific approval.'},
            'runtime':{'image':'host-source:windows-python-3.12.14','container_name':'dev-danish-'+uuid4().hex[:12], 'internal_host':'127.0.0.1','internal_port':str(port)},
            'interface':{'type':'control','operation_name':operation,'input_type':'JSON','output_type':'JSON'}}
        if operation=='GenerateTopology':manifest['interface']['parameter_schema']=schema
        service=call(provider,'POST',base,'/services/import/confirm-manual',json={'manifest':manifest})
        definition={'operation_role':'source' if operation=='GenerateTopology' else 'reporter','binding_transport':'whole-output-v1',
            'inputs':[run_input] if operation=='GenerateTopology' else [{**topology,'required':True,'source_requirement':'upstream_operation'}],
            'outputs':[topology] if operation=='GenerateTopology' else [rendered],
            'compatibility_notes':['Source-derived whole JSON output reference; no projection, conversion or scientific approval. Separate run configuration supplies/loads are selected in Builder.']}
        contract=call(provider,'POST',base,'/services/'+service['id']+'/operation-contracts',json={
            'operation_identity':'urn:development-fixture:danish:'+service['id'],'runtime_operation_name':operation,
            'contract_version':'1.0.0','source_kind':'manual','source_reference':'Inspected WP3 Danish native source, development fixture only','definition':definition})
        records.append({'service':service,'io_contract':contract,'base_url':'http://127.0.0.1:'+str(port)})
    # Small source-bounded I/O checks, BEFORE publishing only these fixture services.
    workflow='wf-danish-io-qualification-'+uuid4().hex[:8]
    fixture=json.loads((directory/'fixture-input.json').read_text());fixture['run_config']['how_many']=1
    reference={'protocol':'inline','format':'json','uri':base64.b64encode(json.dumps(fixture).encode()).decode()}
    upstream=complete(control,records[0]['base_url'],{'method':'GenerateTopology','workflow_id':workflow,'task_id':'io-generator','inputs':[reference]})
    for index,record in enumerate(records[1:]):
        complete(control,record['base_url'],{'method':'RenderTopologies','workflow_id':workflow,'task_id':'io-drawing-'+str(index),'inputs':[upstream]})
    for record in records:call(admin,'POST',base,'/services/'+record['service']['id']+'/review/approve')
    for record in records:call(provider,'POST',base,'/operation-contracts/'+record['io_contract']['id']+'/activate')
    # Existing normal review preserves the active I/O definition in the new parameter version.
    gen=records[0];path='/services/'+gen['service']['id']+'/parameter-onboarding'
    discovery=call(provider,'GET',base,path)['discovery']
    contract=call(provider,'POST',base,path+'/review',json={'discovery_revision':discovery['revision'],
        'operation_identity':gen['io_contract']['operation_identity'],'contract_version':'1.1.0','operation_role':'source',
        'parameters':[{'name':c['name'],'source_pointer':c['source_pointer'],'definition':c['definition'],
            'algorithm_mapping':'Inspected GenerateTopology passes '+('how_many as enumerate_networks max_results' if c['name']=='how_many' else c['name'])} for c in discovery['candidates']],
        'runtime_support_confirmed':False,'normal_configuration_tested':False,'invalid_configuration_tested':False})
    assert contract['definition']['inputs'] and contract['definition']['outputs']
    export=call(provider,'GET',base,'/operation-contracts/'+contract['id']+'/qualification-capability')
    qualification_hash=readonly_export(directory,export,'qualification')
    configuration={'contract_id':contract['id'],'contract_version':contract['contract_version'],'operation_identity':contract['operation_identity'],
        'schema_version':'1.0','instance_id':'development-qualification','parameters':values}
    payload={'method':'GenerateTopology','workflow_id':'wf-danish-parameter-qualification-'+uuid4().hex[:8],
        'task_id':'parameter-valid','inputs':[reference],'configuration':configuration}
    invalid=deepcopy(payload);invalid['task_id']='parameter-invalid';invalid['configuration']['parameters']['how_many']=True
    assert control.post(gen['base_url']+'/control/execute',json=invalid,timeout=5).status_code==422
    qualified=complete(control,gen['base_url'],payload)
    artifact=Path(qualified['uri']).resolve();assert artifact.is_relative_to((directory/'outputs').resolve())
    output=json.loads(artifact.read_text());assert output['execution']['algorithm_consumed']==values
    assert output['execution']['algorithm_arguments']['max_results']==1 and output['topology_count']==1
    review=call(provider,'GET',base,path)['reviews'][contract['id']]
    call(provider,'POST',base,path+'/reviews/'+contract['id']+'/confirm-runtime',json={'reviewed_contract_sha256':review['reviewed_contract_sha256'],
        'runtime_support_confirmed':True,'normal_configuration_tested':True,'invalid_configuration_tested':True,
        'evidence_reference':'DEVELOPMENT SOFTWARE FIXTURE: new real native HTTP enumerator/render I/O and valid/invalid parameter checks; no Danish partner approval'})
    call(provider,'POST',base,'/operation-contracts/'+contract['id']+'/activate')
    runtime=call(provider,'GET',base,'/operation-contracts/'+contract['id']+'/runtime-capability')
    active_hash=readonly_export(directory,runtime,'active')
    for kind,record in zip(('renderer-a','renderer-b'),records[1:]):
        value=call(provider,'GET',base,'/operation-contracts/'+record['io_contract']['id']+'/runtime-capability')
        target=directory/'contracts'/(kind+'.json')
        with target.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
        target.chmod(stat.S_IREAD)
    records[0]['contract']=contract
    (directory/'fixtures.private.json').write_text(json.dumps(records,indent=2))
    (directory/'onboarding-evidence.private.json').write_text(json.dumps({'source_io_qualified':True,'actual_enumerator_parameters':output['execution'],
        'qualification_export_sha256':qualification_hash,'active_export_sha256':active_hash,'fixture_services':len(records),'actual_partner_contracts_changed':0},indent=2))
    print(json.dumps({'normal_role_fixture_services':3,'new_danish_node_fixture':True,'actual_enumerator_and_renderer':True,'valid_invalid_qualified':True,
        'reviewed_parameter_and_io_versions_preserved':True,'exports_read_only':True,'paid_calls':0,'designer_workflows_yet':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    onboard(parser.parse_args().directory.resolve())
