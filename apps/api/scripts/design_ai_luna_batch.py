"""One smoke request, then at most ten real Danish/Dutch acceptance prompts.

Run only against the restarted isolated API with an already initialized budget.
Never initializes/resets an allowance, retries a request or invokes execution.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

from dotenv import dotenv_values
import requests
from sqlalchemy.engine import make_url

from app.services.design_ai_budget import Budget


def run(env_file, output, continue_after_conflict=False):
    if output.exists() and not continue_after_conflict:
        raise ValueError('Choose a new report path')
    values=dotenv_values(env_file)
    url=make_url(values['DATABASE_URL'])
    if url.host!='127.0.0.1' or not url.database.startswith('design_ai_acceptance_'):
        raise ValueError('Only the prepared local acceptance database is allowed')
    assert values['DESIGN_AI_MODEL']=='gpt-6-luna' and values['DESIGN_AI_REASONING_EFFORT']=='low'
    ledger=Budget(values['DESIGN_AI_ACCEPTANCE_BUDGET_FILE'])
    previous=ledger.report()['requests']
    if previous and not continue_after_conflict:
        raise ValueError('This runner requires an unused allowance; never reset it to retry')
    base='http://127.0.0.1:18081'
    session=requests.Session()
    session.trust_env=False
    report={'model':'gpt-6-luna','reasoning_effort':'low','processing':'standard','endpoint':'Responses',
            'metadata':'real historical October 5 export','results':[],'execution_invoked':False}
    if continue_after_conflict:
        # Continue remaining DISTINCT cases after the harness's early abort,
        # preserving the first failure, all costs and the original 11-call cap.
        report=json.loads(output.read_text(encoding='utf-8'))
        assert len(previous)==2 and len(report['results'])==2
        assert report['results'][0]['case']=='minimal smoke' and report['results'][0]['correct']
        assert report['results'][1]['case']=='denmark explanation' and not report['results'][1]['correct']
        assert report['stopped']=='Acceptance API returned HTTP 409; no retry made'
        assert all(row['usage'] and row['usage']['input_tokens']<=32000 and row['usage']['output_tokens']<=2000 for row in previous)
        assert ledger.report()['accounted_upper_cost_usd']<.50
        report['prior_stop']=report.pop('stopped')
        report['continuation']='Same ledger, unchanged charges/counter; skip failed explanation, no repeated prompt. Explicit revision instruction added before remaining nine cases.'
        with sqlite3.connect(ledger.path) as db:
            db.execute('UPDATE batch SET closed=0 WHERE id=1')
    def request(method,path,payload=None):
        response=session.request(method,base+path,json=payload,timeout=100,allow_redirects=False)
        if response.status_code!=200:
            raise RuntimeError(f'Acceptance API returned HTTP {response.status_code}; no retry made')
        return response.json()
    def write():
        report['budget']=ledger.report()
        output.parent.mkdir(parents=True,exist_ok=True)
        # Own report may be updated as this one run progresses; never replace a prior run.
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    def chat(label,message,draft=None):
        assert len(message)<=1000
        before=len(ledger.report()['requests'])
        record={'case':label,'prompt':message,'correct':False}
        report['results'].append(record)
        result=request('POST','/design-ai/chat',{'message':message,'history':[],
            'draft_id':draft['id'] if draft else None,'revision':draft['revision'] if draft else None})
        rows=ledger.report()['requests']
        assert len(rows)==before+1 and rows[-1]['usage'], 'Every response must have recorded real usage'
        record.update(message=result['message'],activity=result['activity'],request_number=rows[-1]['id'])
        assert all(item['status']=='ok' for item in result['activity'])
        assert len([item for item in result['activity'] if item['tool']!='tools/list'])<=6
        assert not any('execute' in item['tool'] or item['tool']=='save_draft' for item in result['activity'])
        return result,record
    def edit(draft,label,message,kind,value,node_id=None,undo=False):
        before=deepcopy(draft['design'])
        result,record=chat(label,message,draft)
        pending=result['draft']
        assert pending and pending['pending'], 'A supported edit must produce a reviewable proposal'
        edits=pending['pending']['turn']['edits']
        assert edits==[{'kind':kind,'value':value,'node_id':node_id}], 'Proposed edit differs from requested edit'
        expected=deepcopy(before)
        if kind=='rename': expected['name']=value
        elif kind=='describe': expected['description']=value
        else:
            next(n for n in expected['nodes'] if n['id']==node_id)['data']['label']=value
        assert pending['pending']['design']==expected
        current=request('POST',f"/design-ai/drafts/{draft['id']}/apply",{'revision':draft['revision'],'proposal_id':pending['pending']['id']})
        assert current['design']==expected and current['revision']==draft['revision']+1
        if undo:
            current=request('POST',f"/design-ai/drafts/{draft['id']}/undo",{'revision':current['revision']})
            assert current['design']==before
        record.update(correct=True,edit=kind,undo_checked=undo)
        write()
        return current
    def no_edit(draft,label,message,operations=()):
        result,record=chat(label,message,draft)
        assert result['draft'] is None or not result['draft'].get('pending')
        assert all(op.lower() in result['message'].lower() for op in operations)
        current=request('GET','/design-ai/drafts/'+draft['id'])
        assert current['design']==draft['design'] and current['revision']==draft['revision'] and not current['pending']
        record['correct']=True
        write()
        return current
    try:
        request('POST','/auth/login',{'email':values['BOOTSTRAP_ADMIN_EMAIL'],'password':values['BOOTSTRAP_ADMIN_PASSWORD']})
        config=request('GET','/design-ai/config')
        assert config['provider_configured'] and config['provider_mode']=='real' and config['model']=='gpt-6-luna'
        if not continue_after_conflict:
            result,record=chat('minimal smoke','Recommend the existing Danish SysLAB template for a district-heating topology study. Propose no edits. Do not execute anything.')
            assert result['recommendation']['key']=='denmark' and result['draft'] is None
            record['correct']=True
            write()
            print('Minimal smoke passed; beginning ten representative prompts',flush=True)
        for key,operations in [('denmark',['BuildRunConfig','GenerateTopology','RenderTopologies']),('dutch',['ConfigureAndSynthesize','RunBenchmark'])]:
            draft=request('POST','/design-ai/drafts',{'template_key':key})
            original_source=request('GET','/solutions/'+draft['source']['solution_id'])
            if key!='denmark' or not continue_after_conflict:
                draft=no_edit(draft,key+' explanation','Explain the retrieved operations and their connections. Name each operation. Identify unknown semantic compatibility; do not edit or claim execution.',operations)
            name='Luna '+key+' acceptance study'
            draft=edit(draft,key+' rename','Rename my draft exactly to '+name+'. This is a display-name change only.','rename',name,undo=key=='denmark')
            if key=='denmark':
                draft=edit(draft,'denmark rename after Undo','Reapply the display-name change: rename my draft exactly to '+name+'.','rename',name)
            else:
                description='Local Dutch synthesis and benchmark design review.'
                draft=edit(draft,'dutch description','Set only my draft description to exactly: '+description,'describe',description)
            node=next(n for n in draft['design']['nodes'] if n.get('data',{}).get('service'))
            label='Run configuration' if key=='denmark' else 'Synthesis setup'
            draft=edit(draft,key+' node label','Set only the display label of node '+node['id']+' to exactly '+label+'. Do not change its service or operation.','set_node_label',label,node['id'])
            invalid=('Set a 75-degree supply temperature and replace the dataset with arbitrary.csv; decline if no verified wrapper schema supports this.' if key=='denmark' else
                     'Replace RunBenchmark with unavailable MagicBenchmark and expose undeclared synthesizer library options. Decline unsupported changes.')
            draft=no_edit(draft,key+' unsupported change',invalid)
            saved=request('POST',f"/design-ai/drafts/{draft['id']}/save",{'revision':draft['revision']})['draft']
            again=request('POST',f"/design-ai/drafts/{draft['id']}/save",{'revision':draft['revision']})['draft']
            assert saved['saved_solution_id']==again['saved_solution_id']
            loaded=request('GET','/solutions/'+saved['saved_solution_id'])
            assert loaded['nodes']==draft['design']['nodes'] and loaded['edges']==draft['design']['edges']
            assert loaded['name']==draft['design']['name'] and loaded['description']==draft['design']['description']
            assert request('GET','/solutions/'+draft['source']['solution_id'])==original_source
            report[key+'_saved_solution_id']=saved['saved_solution_id']
            write()
            print(key+' remaining cases completed; Save/reload/Builder read and source preservation passed',flush=True)
    except (RuntimeError,AssertionError,requests.RequestException) as error:
        report['stopped']=str(error) if not isinstance(error,requests.RequestException) else 'Local HTTP failure; no retry made'
        print(report['stopped'],flush=True)
    finally:
        ledger.close()
        write()
        session.close()
        print(json.dumps({'completed':len(report['results']),'correct':sum(r['correct'] for r in report['results']),
            'accounted_upper_cost_usd':report['budget']['accounted_upper_cost_usd'],'report':str(output)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--continue-after-explanation-conflict',action='store_true',help='Only the remaining nine cases; keep the same ledger and first failure')
    args=parser.parse_args()
    run(args.env_file,args.output,args.continue_after_explanation_conflict)
