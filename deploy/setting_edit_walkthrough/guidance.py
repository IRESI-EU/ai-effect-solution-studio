"""Two-response OFFLINE D-guidance walkthrough; no interpreter/evaluator or key.

Reuse the existing isolated copy, authentication and source-review starter.
Production never imports this fixture. Both supplied responses are labelled.
"""
import argparse
from copy import deepcopy
import json, os
from pathlib import Path
from target_choice import ROOT, prepare as copy_fixture, environment, sqlite_types, start

FOLLOWUP='Use the published maximum candidate layouts of 2. Keep all other settings, input and connections.'


def captured():
    report=json.loads((ROOT/'docs/verification/setting-choice-executed-20261121.json').read_text(encoding='utf-8'))
    return next(c for c in report['cases'] if c['id']=='D-invalid')


def prepare(directory, case, offline):
    copy_fixture(directory,case,offline,title='OFFLINE guidance — earlier pending title')
    p=directory/'profile.private.json';profile=json.loads(p.read_text(encoding='utf-8'))
    profile.update(api_url='http://127.0.0.1:28273',web_url='http://127.0.0.1:23139',
        environment_label='OFFLINE SETTING GUIDANCE — SCRIPTED RESPONSES / NO MODEL / NO RUN')
    p.write_text(json.dumps(profile,indent=2),encoding='utf-8')


class OfflineGuidance:
    name='OFFLINE captured D + scripted valid follow-up'; mode='test'
    def __init__(self,directory):self.directory=directory
    async def respond(self,c):
        from app.schemas.solution_assistant import SavedSolutionResponse
        path=self.directory/'responses.private.jsonl'
        records=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
        n=len(records);case=captured()
        if n==0 and c['request']==case['request']:
            response=deepcopy(case['provider_audit']['validated_response'])
        elif n==1 and c['request']==FOLLOWUP:
            projection=c['pending_candidate'] or c['saved_design'];eligible=[]
            for step in projection['steps']:
                props=(step['contract'] or {}).get('definition',{}).get('execution_parameters',{}).get('properties',{})
                for name,spec in props.items():
                    if spec['type']=='integer' and spec.get('minimum',4)<=2 and spec.get('maximum',0)>=4:
                        eligible.append((step,name))
            if len(eligible)!=1:raise ValueError('This supplied-response fixture requires exactly one eligible integer target')
            step,name=eligible[0]
            response=dict(outcome='setting_edit',message=None,clarification=None,solution_edits=[],assumptions=[],
                edit_base=c['edit_bases']['pending' if c['pending_candidate'] else 'saved'],
                parameter_action=dict(operation='set_parameters',target_ref=step['target_ref'],requested_values=[dict(name=name,value=2)]))
        else:raise ValueError('Only the two documented OFFLINE responses are supplied; no model is connected')
        with path.open('a',encoding='utf-8') as log:
            log.write(json.dumps(dict(offline=True,request=c['request'],response=response),ensure_ascii=False)+'\n')
        return SavedSolutionResponse.model_validate(response)


def serve(directory):
    sqlite_types()
    from app.main import app
    from app.services.design_ai_provider import get_provider
    from fastapi.responses import JSONResponse
    provider=OfflineGuidance(directory);app.dependency_overrides[get_provider]=lambda:provider
    @app.middleware('http')
    async def no_execution(request,call_next):
        if request.method not in {'GET','HEAD'} and (request.url.path.startswith(('/deployments','/workflows/submit')) or request.url.path.endswith('/runtime/verify')):
            return JSONResponse(status_code=409,content={'detail':'OFFLINE setting guidance walkthrough: execution disabled.'})
        return await call_next(request)
    from urllib.parse import urlsplit
    import uvicorn
    profile=json.loads((directory/'profile.private.json').read_text(encoding='utf-8'))
    uvicorn.run(app,host='127.0.0.1',port=urlsplit(profile['api_url']).port,log_level='warning',access_log=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','start','_serve'])
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--case',type=Path);p.add_argument('--offline',type=Path)
    a=p.parse_args();d=a.directory.resolve()
    if a.action=='prepare':prepare(d,a.case.resolve(),a.offline.resolve())
    elif a.action=='start':start(d,script=__file__,build_parent='sgui')
    else:os.environ.update(environment(d));serve(d)
