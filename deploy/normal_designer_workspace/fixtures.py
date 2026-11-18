"""Normal role/routes install explicitly labelled development software fixtures.

Operator qualification is separate from the independent browser designer Runs.
Never enables or approves actual Portuguese provider contracts.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

import requests


def call(client, method, base, path, **kwargs):
    response = client.request(method, base + path, timeout=20, allow_redirects=False, **kwargs)
    if response.status_code not in {200, 201, 204}:
        raise RuntimeError(f'Fixture route rejected {method} {path}: {response.status_code}: {response.text[:1200]}')
    return response.json() if response.content else None


def session():
    client = requests.Session(); client.trust_env = False; return client


def login(client, base, account):
    return call(client, 'POST', base, '/auth/login', json={k:account[k] for k in ('email', 'password')})


def drafts(directory):
    p = json.loads((directory / 'profile.private.json').read_text()); accounts = json.loads((directory / 'credentials.private.json').read_text())
    destination = directory / 'fixtures.private.json'
    if destination.exists(): raise RuntimeError('Fixture records already exist; do not create duplicate services')
    base = p['api_url']; admin = session(); login(admin, base, accounts['administrator'])
    for role, node, key in [('node_manager', 'portugal', 'provider'), ('solution_designer', None, 'designer'), ('solution_designer', None, 'other_designer')]:
        account = accounts[key]
        user = call(admin, 'POST', base, '/auth/register', json={**account, 'display_name': 'Development ' + key.replace('_', ' '), 'requested_role': role, 'node': node})
        call(admin, 'POST', base, '/admin/users/' + user['id'] + '/approve', json={'role': role, 'node': node})
    provider = session(); login(provider, base, accounts['provider'])
    records = []; capabilities = {'capability_schema_version': '1.0', 'transports': ['http-parameters-v1'], 'qualification_only': True, 'operations': []}
    for method, inputs, outputs, values in [('TrainModel', 'CSV', 'JSON', {'epochs':1,'batch_size':16,'sequence_len':4}), ('GenerateData','JSON','CSV', {'number_of_examples':2})]:
        properties = {name: {'type':'integer','title':name,'description':'DEVELOPMENT SOFTWARE FIXTURE bounds/default only; no Portuguese scientific approval',
            'minimum':1,'maximum':32,'default':default} for name,default in values.items()}
        manifest = {'schema_version':'1.0','service':{'id':'dev-fixture-' + uuid4().hex, 'name':'DEVELOPMENT SOFTWARE FIXTURE — ' + method,
            'provider':'Isolated development software qualification', 'category':'Development software fixtures'},
            'runtime':{'image':'sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f','container_name':'dev-' + method.lower(), 'internal_host':'127.0.0.1','internal_port':'28193'},
            'interface':{'type':'control','operation_name':method,'input_type':inputs,'output_type':outputs,
                'parameter_schema':{'type':'object','properties':properties,'required':list(values)}}}
        service = call(provider,'POST',base,'/services/import/confirm-manual',json={'manifest':manifest})
        path = '/services/' + service['id'] + '/parameter-onboarding'
        discovery = call(provider,'GET',base,path)['discovery']
        contract = call(provider,'POST',base,path + '/review',json={'discovery_revision':discovery['revision'],
            'operation_identity':'urn:development-software-fixture:' + method.lower(), 'contract_version':'1.0.0',
            'parameters':[{'name':c['name'],'source_pointer':c['source_pointer'],'definition':c['definition'],'algorithm_mapping':'Actual source API query ' + c['name']} for c in discovery['candidates']],
            'runtime_support_confirmed':False,'normal_configuration_tested':False,'invalid_configuration_tested':False})
        export = call(provider,'GET',base,'/operation-contracts/' + contract['id'] + '/qualification-capability')
        capabilities['operations'].extend(export['operations']);records.append({'service':service,'contract':contract})
    (directory / 'contracts/installed.json').write_text(json.dumps(capabilities))
    destination.write_text(json.dumps(records,indent=2))
    print(json.dumps({'registered_accounts':3,'fixture_services_created_via_normal_routes':2,'fixture_contracts':'draft','actual_provider_contracts_changed':0}))


def qualify_and_publish(directory):
    p = json.loads((directory / 'profile.private.json').read_text()); accounts = json.loads((directory / 'credentials.private.json').read_text())
    records = json.loads((directory / 'fixtures.private.json').read_text());base=p['api_url'];provider=session();login(provider,base,accounts['provider'])
    control=session();control.headers['Authorization']='Bearer ' + p['control_key']
    fixture=(directory/'inputs/DEVELOPMENT-SOFTWARE-FIXTURE.csv').read_bytes()
    reference={'protocol':'inline','format':'csv','uri':base64.b64encode(fixture).decode()}
    receipts=[];workflow='wf-fixture-qualification-' + uuid4().hex[:12]
    for index,record in enumerate(records):
        c=record['contract']; values={'epochs':1,'batch_size':16,'sequence_len':4} if index==0 else {'number_of_examples':2}
        payload={'workflow_id':workflow,'task_id':'qualification-' + str(index),'method':record['service']['operation_name'],'inputs':[reference],
            'configuration':{'contract_id':c['id'],'contract_version':c['contract_version'],'operation_identity':c['operation_identity'],
                'schema_version':'1.0','instance_id':'fixture-qualification-' + str(index),'parameters':values}}
        invalid=deepcopy(payload);invalid['configuration']['parameters'][next(iter(values))]=True
        assert control.post(p['connector_url']+'/control/execute',json=invalid,timeout=5).status_code==422
        accepted=call(control,'POST',p['connector_url'],'/control/execute',json=payload);deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            receipt=call(control,'GET',p['connector_url'],'/control/receipt/'+accepted['task_id'])
            if receipt['state'] not in {'queued','running'}:break
            time.sleep(.2)
        if receipt['state']!='complete':
            (directory/'failed-qualification.private.json').write_text(json.dumps(receipt,indent=2));raise RuntimeError('Qualification failed; preserve outcome and reconcile before any further dispatch')
        assert receipt['runtime_observation']['model']['weight_elements']>0
        receipts.append(receipt);reference=receipt['output']
        review=call(provider,'GET',base,'/services/'+record['service']['id']+'/parameter-onboarding')['reviews'][c['id']]
        call(provider,'POST',base,'/services/'+record['service']['id']+'/parameter-onboarding/reviews/'+c['id']+'/confirm-runtime',json={
            'reviewed_contract_sha256':review['reviewed_contract_sha256'],'runtime_support_confirmed':True,'normal_configuration_tested':True,
            'invalid_configuration_tested':True,'evidence_reference':'DEVELOPMENT SOFTWARE FIXTURE only: new private real DGAN valid/invalid check with authenticated bound observations; no partner scientific approval'})
    admin=session();login(admin,base,accounts['administrator'])
    for record in records:call(admin,'POST',base,'/services/'+record['service']['id']+'/review/approve')
    capabilities={'capability_schema_version':'1.0','transports':['http-parameters-v1'],'operations':[]}
    for record in records:
        c=record['contract'];call(provider,'POST',base,'/operation-contracts/'+c['id']+'/activate')
        capabilities['operations'].extend(call(provider,'GET',base,'/operation-contracts/'+c['id']+'/runtime-capability')['operations'])
    (directory/'contracts/installed.json').write_text(json.dumps(capabilities))
    (directory/'fixture-qualification-receipts.private.json').write_text(json.dumps(receipts,indent=2))
    print(json.dumps({'fixture_services_approved':2,'fixture_contracts_active':2,'actual_provider_contracts_changed':0,'real_model':True,'invalid_requests_rejected':True,'designer_runs_yet':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['drafts','qualify']);parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args(); directory=args.directory.resolve()
    if args.action=='drafts':drafts(directory)
    else:qualify_and_publish(directory)
