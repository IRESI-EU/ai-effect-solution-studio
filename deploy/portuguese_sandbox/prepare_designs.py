"""Read-only runtime inspection plus two fresh designs through authorized API.
No execution endpoint is called here.
"""
import hashlib,io,json,subprocess,tarfile,os
from pathlib import Path
import requests
ROOT=Path(os.environ['PT_SANDBOX_RECORDS']).resolve()
cfg=ROOT/'profile/compose.private.json'
D=['docker','--context','desktop-linux']
C=D+['compose','-f',str(cfg)]
def command(args): return subprocess.check_output(args,timeout=30,text=True)
actual=json.loads(command(D+['run','--rm','--network','none','--read-only','--entrypoint','python',
 'sha256:c0a0b19a07619401f74ff944146b4d3fd33f3b4bc86fd71a7dfadcc1ceb85589','-c',
 "from pathlib import Path; import json,hashlib; print(json.dumps({str(p.relative_to('/app/')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/src').rglob('*.py')}))"]))
wp3=Path(os.environ['PT_SANDBOX_WP3_CHECKOUT']).resolve()
archive=subprocess.check_output(['git','-c','core.longpaths=true','archive','0221b7ecd4a2d5f072de640350ebc599df22131a','orchestrator/src'],cwd=wp3,timeout=20)
with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
    for member in tf.getmembers():
        if member.isfile() and member.name.endswith('.py'):
            name=member.name.removeprefix('orchestrator/')
            assert hashlib.sha256(tf.extractfile(member).read()).hexdigest()==actual[name], 'Packaged WP3 source drift: '+name
policy=json.loads((ROOT/'profile/policy.json').read_text())
owner_namespace='sandbox_'+hashlib.sha256(policy['owner_id'].encode()).hexdigest()[:20]
code="""import json,os,requests,sqlite3
from pathlib import Path
from app.core.config import settings
assert not settings.openai_api_key and not settings.design_ai_enabled and not settings.design_ai_demo_execution_grant_file
assert not settings.design_ai_acceptance_budget_file and not settings.aie37_qualification and not settings.design_ai_dutch_demo
token=settings.orchestrator_services_api_key
caps=requests.get('http://pt-adapter:8080/control/capabilities',headers={'Authorization':'Bearer '+token},timeout=5)
assert caps.status_code==200
api=requests.get('http://ml:600/openapi.json',timeout=5).json()
assert {p['name'] for p in api['paths']['/train']['post']['parameters']} >= {'user_id','model_name','epochs','batch_size','sequence_len','overwrite','index_col'}
assert {p['name'] for p in api['paths']['/generate']['get']['parameters']} >= {'user_id','model_name','number_of_examples','return_csv'}
models=requests.get('http://ml:600/models',params={'user_id':OWNER_NAMESPACE},timeout=5).json()
assert not models
print(json.dumps({'caps':caps.json(),'train_schema':api['paths']['/train']['post'],'generate_schema':api['paths']['/generate']['get'],
'isolated_default_models':models,'provider_disconnected':True,'ledger_attached':False,'grant_disabled':True}))
"""
runtime=json.loads(command(C+['exec','-T','api','python','-c',code.replace('OWNER_NAMESPACE',repr(owner_namespace))]))
assert command(C+['exec','-T','redis','redis-cli','DBSIZE']).strip()=='0'
credential=json.loads((ROOT/'profile/credentials.json').read_text())
s=requests.Session();s.trust_env=False
base='http://127.0.0.1:23124/api'
response=s.post(base+'/auth/login',json={k:credential[k] for k in ('email','password')},timeout=15)
assert response.status_code==200,response.status_code
assert response.json()['id']==credential['owner_id']
assert requests.get('http://127.0.0.1:23124/login',timeout=10).status_code==200
def create(method,parameters):
    node={'id':'pt-step','type':'default','position':{'x':400,'y':200},'data':{'label':'EXPERIMENTAL Portuguese '+method,
        'node_kind':'service','service':{'id':'pt-experimental-'+method},'configuration':{
        'contract_id':'pt-sandbox-generate-v1' if method=='GenerateData' else 'pt-sandbox-train-v1','contract_version':'0.1.0','parameters':parameters}}}
    data={'name':'EXPERIMENTAL Portuguese '+method+' parameter proof','description':'Platform-controlled isolated synthetic test. Not partner-approved or scientifically qualified.',
        'nodes':[{'id':'input','type':'input','position':{'x':100,'y':200},'data':{'label':'Workflow Input','node_kind':'workflow_input'}},node,
            {'id':'output','type':'output','position':{'x':700,'y':200},'data':{'label':'Workflow Output','node_kind':'workflow_output'}}],
        'edges':[{'id':'input-pt','source':'input','target':'pt-step'},{'id':'pt-output','source':'pt-step','target':'output'}]}
    response=s.post(base+'/solutions',json=data,timeout=15)
    assert response.status_code==200,response.text
    return response.json()
if (ROOT/'designs.private.json').exists(): raise RuntimeError('Prepared designs already exist; do not duplicate')
designs={'generate':create('GenerateData',{'number_of_examples':10}),'train':create('TrainModel',{'epochs':1,'batch_size':4})}
(ROOT/'designs.private.json').write_text(json.dumps(designs,indent=2))
(ROOT/'preflight-runtime.private.json').write_text(json.dumps({'runtime':runtime,'wp3_source_parity':'All manifest source files match maintained PR3 base bytes','worker_started':False},indent=2))
print(json.dumps({'login_proxy':'pass','wp3_source_parity':'pass','empty_new_redis':True,'empty_test_models':True,
 'generate_builder':'http://127.0.0.1:23124/builder?solutionId='+designs['generate']['id'],
 'training_builder':'http://127.0.0.1:23124/builder?solutionId='+designs['train']['id'],'jobs_submitted':0}))
