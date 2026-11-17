"""Read recorded artifacts only. No algorithm endpoint is invoked."""
import argparse,base64,csv,hashlib,io,json,subprocess
from pathlib import Path
from bounded_jobs import ROOT,C,authenticated,api
def collect(case,phase):
    record=json.loads((ROOT/(case+'-observed.private.json')).read_text())
    assert record['workflow']['status']=='completed'
    wf=record['workflow']['workflow_id']
    tasks=record['tasks']['tasks'];assert len(tasks)==1 and tasks[0]['status']=='completed'
    rows=[r for r in record['journal'] if json.loads(r['request'])['workflow_id']==wf]
    assert len(rows)==1 and rows[0]['state']=='complete'
    row=rows[0];req=json.loads(row['request']);proof=json.loads(row['result'])
    assert proof['workflow_id']==wf and proof['task_id']==tasks[0]['task_id']==req['task_id']
    assert proof['instance_id']==req['configuration']['instance_id']=='pt-step'
    code="""import sys,json,base64,requests
from app.core.config import settings
url=sys.stdin.read().strip()
assert url.startswith('http://pt-adapter:8080/control/data/')
public=requests.get(url,timeout=10);assert public.status_code==401
r=requests.get(url,headers={'Authorization':'Bearer '+settings.orchestrator_services_api_key},timeout=10)
assert r.status_code==200
print(base64.b64encode(r.content).decode())
"""
    result=subprocess.run(C+['exec','-T','api','python','-c',code],input=proof['output']['uri'],text=True,stdout=subprocess.PIPE,check=True,timeout=20)
    data=base64.b64decode(result.stdout.strip(),validate=True)
    assert hashlib.sha256(data).hexdigest()==proof['sha256']
    counts={}
    for r in csv.DictReader(io.StringIO(data.decode())):
        counts[r['example']]=counts.get(r['example'],0)+1
    expected=10 if case=='generate10' else 20
    assert set(counts)=={str(i) for i in range(1,expected+1)} and set(counts.values())=={100}
    assert proof['requested_effective']=={'number_of_examples':expected}
    s=authenticated()
    assert api(s,'GET','/workflows/'+wf+'/submitted-configuration')==record['submission']
    output={'workflow_id':wf,'task_id':req['task_id'],'instance_id':proof['instance_id'],'sha256':proof['sha256'],
        'bytes':len(data),'actual_examples':len(counts),'csv_rows':sum(counts.values()),'rows_per_example':100,
        'requested_effective':proof['requested_effective'],'upstream_arguments':proof['upstream_arguments'],
        'unauthenticated_download_denied':True,'immutable_submission_unchanged':True}
    filename=ROOT/(case+'-'+phase+'-artifact.private.json')
    filename.write_text(json.dumps(output,indent=2))
    if phase=='after20':
        before=json.loads((ROOT/(case+'-before20-artifact.private.json')).read_text())
        assert output==before,'Historical output or association changed'
    (ROOT/(case+'.csv')).write_bytes(data)
    print(json.dumps(output))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case',choices=['generate10','generate20']);p.add_argument('phase',choices=['before20','after20','final'])
    a=p.parse_args();collect(a.case,a.phase)
