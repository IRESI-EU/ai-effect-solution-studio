"""One real Danish explanation against final code; never resets an allowance.

Domain input testing is deliberately blocked unless separately verified by an
operator against current deployed wrapper evidence. This check executes nothing.
"""
import argparse
import hashlib
import json
from pathlib import Path

from dotenv import dotenv_values
import requests
from sqlalchemy.engine import make_url

from app.services.design_ai_budget import Budget


def run(env_file, manifest_file, output):
    if output.exists():
        raise ValueError('Choose a new report path; never repeat a paid request implicitly')
    values=dotenv_values(env_file)
    url=make_url(values['DATABASE_URL'])
    assert url.host=='127.0.0.1' and url.database.startswith('design_ai_acceptance_')
    assert values['DESIGN_AI_MODEL']=='gpt-6-luna' and values['DESIGN_AI_REASONING_EFFORT']=='low'
    manifest=json.loads(manifest_file.read_text())
    old=Path(manifest['previous_ledger'])
    assert hashlib.sha256(old.read_bytes()).hexdigest()==manifest['previous_sha256']
    assert Budget(old).report()['closed']
    budget=Budget(values['DESIGN_AI_ACCEPTANCE_BUDGET_FILE'])
    assert budget.path.resolve()!=old.resolve()
    assert budget.report()['limit_usd']==.10 and not budget.report()['requests'] and not budget.report()['closed']
    report={'model':'gpt-6-luna','reasoning_effort':'low','processing':'standard','endpoint':'Responses',
            'metadata':'historical Danish export','execution_invoked':False,
            'domain_input_test':'blocked: no current deployed-wrapper source/digest and verified input policy', 'correct':False}
    session=requests.Session()
    session.trust_env=False
    def request(method,path,body=None):
        response=session.request(method,'http://127.0.0.1:18081'+path,json=body,timeout=100,allow_redirects=False)
        if response.status_code!=200:
            raise RuntimeError(f'Local acceptance request failed (HTTP {response.status_code}); no retry')
        return response.json()
    try:
        request('POST','/auth/login',{'email':values['BOOTSTRAP_ADMIN_EMAIL'],'password':values['BOOTSTRAP_ADMIN_PASSWORD']})
        config=request('GET','/design-ai/config')
        assert config['model']=='gpt-6-luna' and config['provider_mode']=='real' and config['provider_configured']
        draft=request('POST','/design-ai/drafts',{'template_key':'denmark'})
        before=request('GET','/design-ai/drafts/'+draft['id'])
        source=request('GET','/solutions/'+draft['source']['solution_id'])
        prompt='Explain the retrieved operations and their connections. Name each operation. Identify unknown semantic compatibility; do not edit or claim execution.'
        report['prompt']=prompt
        result=request('POST','/design-ai/chat',{'message':prompt,'draft_id':draft['id'],'revision':draft['revision'],'history':[]})
        report.update(message=result['message'],activity=result['activity'],context_revision=result['context_revision'],current_revision=result['current_revision'])
        assert all(name.lower() in result['message'].lower() for name in ('BuildRunConfig','GenerateTopology','RenderTopologies'))
        assert result['draft'] is None and result['context_revision']==result['current_revision']==draft['revision']
        assert not any(event['tool'] in {'validate_draft','save_draft'} for event in result['activity'])
        assert request('GET','/design-ai/drafts/'+draft['id'])==before
        assert request('GET','/solutions/'+draft['source']['solution_id'])==source
        assert len(budget.report()['requests'])==1 and budget.report()['usage_unknown_requests']==0
        report.update(correct=True,draft_unchanged=True,source_unchanged=True)
    except (AssertionError,RuntimeError,requests.RequestException) as error:
        report['failure']=str(error) if not isinstance(error,requests.RequestException) else 'Local request failed; no retry'
    finally:
        budget.close()
        report['budget']=budget.report()
        report['previous_ledger_unchanged']=hashlib.sha256(old.read_bytes()).hexdigest()==manifest['previous_sha256'] and Budget(old).report()['closed']
        with output.open('x',encoding='utf-8') as target:
            json.dump(report,target,indent=2,ensure_ascii=False)
        session.close()
    print(json.dumps(report,indent=2,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.env_file,args.manifest,args.output)
