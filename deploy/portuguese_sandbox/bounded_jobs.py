"""Bounded one-shot operator for this separate profile. Never auto-retries."""
import argparse,hashlib,json,subprocess,os
from pathlib import Path
import requests

ROOT=Path(os.environ['PT_SANDBOX_RECORDS']).resolve()
C=['docker','--context','desktop-linux','compose','-f',str(ROOT/'profile/compose.private.json')]
CASES={'train':('TrainModel',{'epochs':1,'batch_size':4},{'dataset_ref':'pt-approved-synthetic-data'}),
 'generate10':('GenerateData',{'number_of_examples':10},{'model_ref':'pt-approved-test-model'}),
 'generate20':('GenerateData',{'number_of_examples':20},{'model_ref':'pt-approved-test-model'})}
def authenticated():
    s=requests.Session();s.trust_env=False
    c=json.loads((ROOT/'profile/credentials.json').read_text())
    r=s.post('http://127.0.0.1:23124/api/auth/login',json={k:c[k] for k in ('email','password')},timeout=15)
    assert r.status_code==200,r.status_code
    return s
def api(s,method,path,**kwargs):
    r=s.request(method,'http://127.0.0.1:23124/api'+path,timeout=30,**kwargs)
    if not r.ok:raise RuntimeError(str(r.status_code)+' '+r.text[:1500])
    return r.json()
def journal():
    code="import sqlite3,json; d=sqlite3.connect('/state/journal.sqlite3'); d.row_factory=sqlite3.Row; print(json.dumps([dict(r) for r in d.execute('select * from jobs')]))"
    return json.loads(subprocess.check_output(C+['exec','-T','pt-adapter','python','-c',code],text=True,timeout=15))
def payload(saved,method,runinput):
    services=[n for n in saved['nodes'] if n.get('data',{}).get('service')]
    return {'name':saved['name'],'solution_id':saved['id'],'expected_updated_at':saved['updated_at'],
        'nodes':[{'node_id':n['id'],'service_id':n['data']['service']['id'],'container_name':'pt-'+method,
            'operation_name':method,'configuration':n['data']['configuration']} for n in services],
        'edges':[],'run_input':runinput}
def snapshot(case):
    method,expected,runinput=CASES[case];s=authenticated()
    designs=json.loads((ROOT/'designs.private.json').read_text())
    saved=api(s,'GET','/solutions/'+designs['train' if case=='train' else 'generate']['id'])
    p=payload(saved,method,runinput)
    assert len(p['nodes'])==1 and p['nodes'][0]['configuration']['parameters']==expected
    prior=journal()
    assert not any(r['state'] in ('running','uncertain','failed') for r in prior), 'Stop on unresolved/failed work'
    assert len([r for r in prior if r['method']=='TrainModel'])==(0 if case=='train' else 1)
    assert len([r for r in prior if r['method']=='GenerateData'])==(1 if case=='generate20' else 0)
    if case=='generate20':
        first=json.loads((ROOT/'generate10-observed.private.json').read_text())
        assert first['workflow']['status']=='completed'
        old=api(s,'GET','/workflows/'+first['workflow']['workflow_id']+'/submitted-configuration')
        assert old==first['submission'],'First immutable submission changed'
    compiled=api(s,'POST','/workflows/compile',json=p)
    ready=api(s,'POST','/workflows/runtime-preflight',json=p)
    assert ready['status']=='ready',ready
    # Same maintained server helper used at submission; strictly read-only WP3 capability negotiation.
    code="import json,sys; from app.services.orchestrator_adapter import require_parameter_transport; print(json.dumps(require_parameter_transport(json.load(sys.stdin))))"
    checked=subprocess.run(C+['exec','-T','api','python','-c',code],input=json.dumps(compiled),text=True,stdout=subprocess.PIPE,check=True,timeout=30)
    result={'case':case,'saved':saved,'request':p,'compiled':compiled,'readiness':ready,'compatibility':json.loads(checked.stdout),
        'journal_before':prior,'resources':json.loads((ROOT/'profile/preflight.json').read_text()),
        'request_sha256':hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()}
    with (ROOT/(case+'-snapshot.private.json')).open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({'case':case,'snapshot':'recorded','settings':expected,'ready':True,'job_count_before':len(prior),'submission_sent':False}))
def submit(case):
    snapshot=json.loads((ROOT/(case+'-snapshot.private.json')).read_text())
    s=authenticated();p=snapshot['request']
    current=api(s,'GET','/solutions/'+p['solution_id'])
    assert current==snapshot['saved'],'Saved design drift; stop'
    assert journal()==snapshot['journal_before'],'Journal drift; stop'
    with (ROOT/(case+'-attempt.private.json')).open('x') as f:json.dump({'case':case,'state':'dispatching','request_sha256':snapshot['request_sha256']},f)
    # Exactly one request. Failure or uncertain response leaves the marker consumed.
    result=api(s,'POST','/workflows/submit-to-orchestrator',json=p)
    (ROOT/(case+'-response.private.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps({'case':case,'workflow_id':result['workflow_id'],'submission_id':result['submission_id'],'status':result['status']}))
def observe(case):
    response=json.loads((ROOT/(case+'-response.private.json')).read_text());wf=response['workflow_id'];s=authenticated()
    result={'workflow':api(s,'GET','/orchestrator/workflows/'+wf),'tasks':api(s,'GET','/orchestrator/workflows/'+wf+'/tasks'),
        'submission':api(s,'GET','/workflows/'+wf+'/submitted-configuration'),'journal':journal()}
    (ROOT/(case+'-observed.private.json')).write_text(json.dumps(result,indent=2))
    relevant=[r for r in result['journal'] if json.loads(r['request'])['workflow_id']==wf]
    print(json.dumps({'case':case,'workflow':result['workflow'],'tasks':result['tasks'],'adapter_states':[r['state'] for r in relevant]}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['snapshot','submit','observe']);p.add_argument('case',choices=CASES)
    a=p.parse_args();globals()[a.action](a.case)
