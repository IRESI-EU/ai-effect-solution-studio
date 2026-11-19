"""Read-only evidence AFTER browser-created Runs. Never dispatch or seed tasks."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from onboard import call,session,login


def sha(raw):return hashlib.sha256(raw).hexdigest()


def capture(directory,workflow,label):
    p=json.loads((directory/'profile.private.json').read_text())
    if p['kind'] not in {'offline-assistant-danish-v1','genuine-saved-solution-v1'}:raise RuntimeError('Wrong isolated workspace')
    accounts=json.loads((directory/'credentials.private.json').read_text())
    client=session();login(client,p['api_url'],accounts['designer'])
    def get(path):return call(client,'GET',p['api_url'],path)
    snapshot=get('/workflows/'+workflow+'/submitted-configuration')
    evidence=get('/workflows/'+workflow+'/instance-evidence')
    assert evidence['state']=='available'
    tasks=get('/orchestrator/workflows/'+workflow+'/tasks')['tasks']
    records=[];root=(directory/'outputs'/workflow).resolve()
    for task in tasks:
        assert task['status']=='completed' and len(task['output_refs'])==1
        ref=task['output_refs'][0];path=Path(ref['uri']).resolve()
        assert path.is_relative_to(root) and path.suffix=='.json'
        raw=path.read_bytes();output=json.loads(raw)
        preview=call(client,'POST',p['api_url'],'/data-references/preview',json={**ref,'workflow_id':workflow,'task_id':task['task_id']})
        assert preview['available']
        artifacts=[]
        for item in output.get('artifact_manifest',{}).get('files',[]):
            svg=Path(item['uri']).resolve();assert svg.is_relative_to(root)
            content=svg.read_bytes();assert sha(content)==item['sha256'] and len(content)==item['bytes']
            result=call(client,'POST',p['api_url'],'/data-references/preview',json={**{k:item[k] for k in ('protocol','uri','format')},'workflow_id':workflow,'task_id':task['task_id']})
            assert result['available'] and base64.b64decode(result['image_data_url'].split(',',1)[1])==content
            artifacts.append({'name':svg.name,'sha256':sha(content),'bytes':len(content)})
        inputs=[]
        for item in task['input_refs']:
            content=base64.b64decode(item['uri']) if item['protocol']=='inline' else Path(item['uri']).read_bytes()
            inputs.append({'sha256':sha(content),'bytes':len(content)})
        records.append({'task':task,'input_hashes':inputs,'output_sha256':sha(raw),'output_bytes':len(raw),
            'topology_count':output.get('topology_count'),'drawing_count':output.get('drawing_count'),
            'execution':output.get('execution'),'artifacts':artifacts})
    solution_id=snapshot['submitted']['request']['solution_id'];other=session();login(other,p['api_url'],accounts['other_designer'])
    denied={}
    for path in ('/solutions/'+solution_id,'/design-ai/solutions/'+solution_id,
                 '/workflows/'+workflow+'/submitted-configuration','/workflows/'+workflow+'/instance-evidence',
                 '/orchestrator/workflows/'+workflow+'/tasks'):
        response=other.get(p['api_url']+path,timeout=10);assert response.status_code==403;denied[path]=403
    last=tasks[-1]
    assert other.post(p['api_url']+'/data-references/preview',json={**last['output_refs'][0],'workflow_id':workflow,'task_id':last['task_id']},timeout=10).status_code==403
    document={'workflow_id':workflow,'solution_id':solution_id,'snapshot':snapshot,'evidence':evidence,'records':records,'other_designer_denied':denied}
    target=directory/(label+'.private.json')
    if target.exists():
        old=json.loads(target.read_text());assert old['snapshot']==snapshot and old['records']==records
        print(json.dumps({'workflow':workflow,'original_snapshot_outputs_and_drawings_unchanged':True}))
    else:
        with target.open('x') as stream:json.dump(document,stream,indent=2)
        print(json.dumps({'workflow':workflow,'same_saved_solution':solution_id,'tasks':len(records),
            'topology_counts':[r['topology_count'] for r in records],'drawing_counts':[r['drawing_count'] for r in records],
            'owned_svg_previews':sum(len(r['artifacts']) for r in records),'other_designer_denied':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--workflow',required=True);parser.add_argument('--label',required=True)
    args=parser.parse_args();capture(args.directory.resolve(),args.workflow,args.label)
