"""Read-only owned snapshots after normal browser actions; never edits or calls AI."""
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'deploy/normal_designer_workspace')]
from fixtures import session,login,call

def capture(d,identifier,label):
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    profile=load(d/'profile.private.json');assert profile['offline'] is True
    client=session();login(client,profile['api_url'],load(d/'credentials.private.json')['designer'])
    get=lambda path:call(client,'GET',profile['api_url'],path)
    value=dict(solution=get('/solutions/'+identifier),conversation=get('/design-ai/solutions/'+identifier),provider=get('/design-ai/config'))
    with sqlite3.connect((d/'portal.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        nodes,edges,metadata=db.execute('SELECT nodes,edges,design_metadata FROM solutions WHERE id=?',(identifier,)).fetchone()
        value['stored']=dict(nodes=json.loads(nodes),edges=json.loads(edges),design_metadata=json.loads(metadata) if metadata else None)
        value['submissions']=db.execute('SELECT COUNT(*) FROM execution_submissions').fetchone()[0]
    assert value['provider']['provider_mode']=='test' and value['submissions']==0 and not (d/'acceptance.private.sqlite').exists()
    with (d/(label+'.private.json')).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)
    pending=value['conversation']['pending']
    print(json.dumps(dict(label=label,solution=identifier,pending=bool(pending),saved_nodes=len(value['stored']['nodes']),offline=True,submissions=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--solution',required=True);p.add_argument('--label',required=True);a=p.parse_args();capture(a.directory.resolve(),a.solution,a.label)
