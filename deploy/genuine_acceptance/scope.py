"""Unpaid preflight, exclusive activation and close of the one authorised scope.

No chat, provider connectivity probe, workflow submit or replacement ledger exists
in this tool. Genuine messages and explicit Runs happen only in the normal UI.
"""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'apps/api'),str(ROOT/'deploy/normal_designer_workspace')]
from fixtures import call,session,login
from app.services.scoped_ai_acceptance import Budget,MODEL,MAX_INPUT,MAX_OUTPUT,MAX_REQUESTS,LIMIT_NANO,RESERVATION,binding,initialize


def load(directory):
    p=json.loads((directory/'profile.private.json').read_text())
    if p['kind']!='genuine-saved-solution-v1' or p['directory']!=str(directory):raise RuntimeError('Wrong workspace')
    accounts=json.loads((directory/'credentials.private.json').read_text());client=session();user=login(client,p['api_url'],accounts['designer'])
    return p,client,user


def get(client,p,path):return call(client,'GET',p['api_url'],path)


def preflight(directory,solution_id):
    p,client,_=load(directory)
    config=get(client,p,'/design-ai/config')
    assert config['provider_mode']=='real' and config['provider_name']=='OpenAI' and config['model']==MODEL and not config['provider_configured']
    assert not (directory/'acceptance.private.sqlite').exists(),'Never preflight as a fresh exercise after activation'
    solution=get(client,p,'/solutions/'+solution_id)
    assert not solution['nodes'] and not solution['edges'],'Start from the one fresh goal solution; do not seed a graph'
    records=json.loads((directory/'fixtures.private.json').read_text());catalogue=get(client,p,'/services')
    assert len(catalogue)==3 and all(s['status']=='approved' and s['name'].startswith('DEVELOPMENT SOFTWARE FIXTURE') for s in catalogue)
    nodes=[];pins=[]
    for index,record in enumerate(records):
        service=next(s for s in catalogue if s['id']==record['service']['id'])
        resolution=get(client,p,'/services/'+service['id']+'/operation-contract-resolution');contract=resolution['contract']
        assert contract['status']=='active' and contract['definition']['binding_transport']=='whole-output-v1'
        node={'node_id':'preflight-'+str(index),'service_id':service['id'],'container_name':'resolved-by-registry','operation_name':service['operation_name'],
            'operation_contract':{'contract_id':contract['id'],'contract_version':contract['contract_version']}}
        if index==0:node['configuration']={'contract_id':contract['id'],'contract_version':contract['contract_version'],'parameters':{'how_many':2}}
        nodes.append(node);pins.append({'service_id':service['id'],'name':service['name'],'contract_id':contract['id'],'contract_version':contract['contract_version']})
    # Compiler/readiness only: no saved-graph mutation and no workflow dispatch.
    payload={'name':'Genuine acceptance unpaid runtime preflight','nodes':nodes,
        'edges':[{'source':'preflight-0','target':'preflight-'+str(index),'binding':{'source_slot':'networks','target_slot':'networks'}} for index in (1,2)],
        'run_input':json.loads((directory/'fixture-input.json').read_text())}
    compiled=call(client,'POST',p['api_url'],'/workflows/compile',json=payload)
    readiness=call(client,'POST',p['api_url'],'/workflows/runtime-preflight',json=payload)
    assert readiness['status']=='ready' and readiness['connection_compatibility']['status']=='ready' and readiness['parameter_compatibility']['status']=='ready'
    document={'passed':True,'solution_id':solution_id,'solution_updated_at':solution['updated_at'],'catalogue':pins,'provider':config,
        'compiler_sha256':hashlib.sha256(json.dumps(compiled,sort_keys=True).encode()).hexdigest(),'readiness':readiness,
        'fixture_input_sha256':hashlib.sha256((directory/'fixture-input.json').read_bytes()).hexdigest(),'paid_requests':0,'workflow_submissions':0}
    with (directory/'preflight.private.json').open('x') as stream:json.dump(document,stream,indent=2)
    print(json.dumps({'unpaid_preflight_passed':True,'actual_active_services':3,'real_provider':True,'compiler_runtime_contracts_match':True,'paid_requests':0,'workflow_submissions':0}))


def activate(directory,solution_id):
    p,client,_=load(directory);checkpoint=json.loads((directory/'preflight.private.json').read_text())
    assert checkpoint['passed'] and checkpoint['solution_id']==solution_id
    solution=get(client,p,'/solutions/'+solution_id)
    assert solution['updated_at']==checkpoint['solution_updated_at'] and not solution['nodes']
    # The normal owned solution records its actual designer identity, not a seed.
    owner=solution['created_by_user_id']
    scope=binding(SimpleNamespace(database_url='sqlite:///'+(directory/'portal.sqlite').as_posix()),owner,solution_id)
    expiry=(datetime.now(timezone.utc)+timedelta(hours=23,minutes=59)).isoformat()
    initialize(directory/'acceptance.private.sqlite',approved_binding=scope,authorization_ref=p['authorization_ref'],expires_at=expiry)
    with (directory/'activation.private.json').open('x') as stream:json.dump({'binding':scope,'expires_at':expiry,'authorization_ref':p['authorization_ref']},stream,indent=2)
    print(json.dumps({'activated_once':True,'model':MODEL,'max_requests':MAX_REQUESTS,'max_input':MAX_INPUT,'max_output':MAX_OUTPUT,
        'hard_limit_usd':LIMIT_NANO/1e9,'reservation_per_request_usd':RESERVATION/1e9,'expires_at':expiry,'calls_made':0}))


def close(directory):
    profile=json.loads((directory/'profile.private.json').read_text());assert profile['kind']=='genuine-saved-solution-v1'
    budget=Budget(directory/'acceptance.private.sqlite');budget.close()
    with sqlite3.connect(budget.path) as db:rows=db.execute('SELECT reserved,held,usage,state FROM acceptance_requests ORDER BY id').fetchall()
    usages=[json.loads(row[2]) for row in rows if row[2] is not None]
    summary={'closed':True,'requests':len(rows),'known_input_tokens':sum(u['input_tokens'] for u in usages),
        'known_output_tokens':sum(u['output_tokens'] for u in usages),'usage_complete':len(usages)==len(rows),
        'accounted_usd':sum(row[1] for row in rows)/1e9,'lifetime_reserved_usd':sum(row[0] for row in rows)/1e9,
        'accounting_basis':'conservative rates including 10% headroom; unknown usage retains maximum reservation; invoice not independently reconciled'}
    (directory/'closed-summary.private.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


def capture(directory,solution_id):
    p,client,_=load(directory)
    solution=get(client,p,'/solutions/'+solution_id);conversation=get(client,p,'/design-ai/solutions/'+solution_id)
    audits=[json.loads(line) for line in (directory/'provider-audit.private.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(audits)==1 and conversation['conversation_revision']==1
    # The audit's conservative CSV redactor can omit comma-rich prose. Recover
    # only the actually stored owned response, then verify the original SDK hash.
    from app.services.provider_evidence import digest
    turn=dict(audits[0]['validated_response'])
    turn['message']=conversation['messages'][-1]['content']
    assert digest(turn)==audits[0]['validated_response_sha256']
    assert turn['discovery'] is None and not turn['solution_edits'] and not turn['edits']
    assert not solution['nodes'] and not solution['edges'] and conversation['pending'] is None
    assert not Budget(directory/'acceptance.private.sqlite').availability()['can_request']
    accounts=json.loads((directory/'credentials.private.json').read_text());other=session();login(other,p['api_url'],accounts['other_designer'])
    denied=[other.get(p['api_url']+path,timeout=10).status_code for path in ('/solutions/'+solution_id,'/design-ai/solutions/'+solution_id)]
    assert denied==[403,403]
    closed=json.loads((directory/'closed-summary.private.json').read_text())
    checkpoint={'solution':solution,'conversation':conversation,'actual_validated_turn':turn,'audit_response_hash_verified':True,'closed':closed}
    with (directory/'failed-turn-1.private.json').open('x',encoding='utf-8') as stream:json.dump(checkpoint,stream,indent=2,ensure_ascii=False)
    public={'date':'2026-11-19','result':'FAIL','failed_step':1,'failure_stage':'acceptance_semantics',
        'reason':'The real response discovered services and compatible connections but asked no structured count clarification; remaining turns and Runs were not attempted.',
        'model':audits[0]['returned_model'],'provider_stage':audits[0]['provider_stage'],'sdk_schema_validated':True,
        'actual_response':turn,'actual_response_sha256':digest(turn),'request_sha256':audits[0]['request_sha256'],
        'solution_id':solution_id,'solution_updated_at':solution['updated_at'],'conversation_revision':conversation['conversation_revision'],
        'saved_nodes':0,'saved_edges':0,'pending_proposal':None,'run_input_selected':False,'workflow_submissions':0,
        'first_run':{'attempted':False},'second_run':{'attempted':False},
        'turns':[{'turn':1,'result':'FAIL','observed':'Actual catalogue discovery, settings/defaults and compatible connections; no count question',
            'user_message':conversation['messages'][0]['content']}]+[{'turn':n,'result':'NOT_ATTEMPTED','reason':'Stopped after first failed live step; scope closed'} for n in range(2,7)],
        'accounting':closed,'usage':audits[0]['usage'],'other_designer_denied':True,
        'catalogue':json.loads((directory/'preflight.private.json').read_text())['catalogue'],
        'scope_policy':{'max_requests':6,'max_input_tokens':64000,'max_output_tokens':3000,'hard_limit_usd':0.45,'automatic_retries':0,'fallback_models':False},
        'portal_serving_commit':json.loads((directory/'serving.private.json').read_text())['portal_base'],
        'wp3_serving_commit':'39405313f9b685d91b8263b9b87a3fc42577331d','historical_workflows_rerun':False,
        'limitations':['No independent renderer consumption was established','No partner scientific approval','No joins or broad interchangeability established','No production deployment','No general reliability claim']}
    destination=ROOT/'docs/verification/genuine-conversation-acceptance-20261119.json'
    with destination.open('x',encoding='utf-8') as stream:json.dump(public,stream,indent=2,ensure_ascii=False);stream.write('\n')
    fixture=ROOT/'apps/api/tests/fixtures/genuine-clarification-miss-20261119.json';fixture.parent.mkdir(exist_ok=True)
    with fixture.open('x',encoding='utf-8') as stream:json.dump(turn,stream,indent=2,ensure_ascii=False);stream.write('\n')
    print(json.dumps({'result':'FAIL','requests':closed['requests'],'actual_response_hash_verified':True,'scope_closed':True,'new_workflow_submissions':0,'provider_identifiers_published':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['preflight','activate','close','capture']);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--solution')
    args=parser.parse_args();directory=args.directory.resolve()
    if args.action=='preflight':preflight(directory,args.solution)
    elif args.action=='activate':activate(directory,args.solution)
    elif args.action=='close':close(directory)
    else:capture(directory,args.solution)
