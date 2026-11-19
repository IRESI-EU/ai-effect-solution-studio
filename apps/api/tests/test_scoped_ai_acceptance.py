"""Synthetic ledgers and mocked SDK only: no live approval, key or paid request."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json
import shutil
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.solution_assistant import SavedSolutionResponse
from app.services import scoped_ai_acceptance as module


SCOPE={'database_sha256':'a'*64,'user_id':'fixture-designer','solution_id':'fixture-solution'}


def new(tmp_path):
    path=tmp_path/'new-scoped-fixture.sqlite'
    module.initialize(path,approved_binding=SCOPE,authorization_ref='OFFLINE TEST APPROVAL DOUBLE',
        expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
    return module.Budget(path)


def settled(budget,identity):
    budget.settle(identity,{'model':module.MODEL,'service_tier':'default','id':'resp_fixture',
        'usage':{'input_tokens':100,'output_tokens':20,'unexpected':'NEVER PERSIST THIS'}})


def test_six_requests_lifetime_reservations_and_no_reset(tmp_path):
    budget=new(tmp_path)
    for _ in range(6):
        identity=budget.reserve(1000,3000,request_binding=SCOPE);settled(budget,identity)
    assert budget.availability()['lifetime_reserved_usd']==0.4059
    assert not budget.availability()['can_request']
    with pytest.raises(HTTPException):budget.reserve(1000,3000,request_binding=SCOPE)
    with pytest.raises(FileExistsError):new(tmp_path)
    assert b'NEVER PERSIST THIS' not in budget.path.read_bytes()


def test_identity_scope_limits_uncertainty_close_and_copy_are_fail_closed(tmp_path):
    budget=new(tmp_path)
    for bound,output,scope in [(64001,3000,SCOPE),(100,3001,SCOPE),(100,3000,{**SCOPE,'solution_id':'another'})]:
        with pytest.raises(HTTPException):budget.reserve(bound,output,request_binding=scope)
    assert budget.availability()['request_count']==0
    identity=budget.reserve(1000,3000,request_binding=SCOPE)
    with pytest.raises(HTTPException):budget.reserve(1000,3000,request_binding=SCOPE)
    budget.failed(identity,'timeout_usage_unknown')
    assert not module.Budget(budget.path).availability()['can_request']
    copy=tmp_path/'copy.sqlite';shutil.copy2(budget.path,copy)
    with pytest.raises(HTTPException):module.Budget(copy).availability()


def test_concurrent_reservations_never_dispatch_twice_with_unknown_usage(tmp_path):
    budget=new(tmp_path)
    def reserve(_):
        try:return budget.reserve(1000,3000,request_binding=SCOPE)
        except HTTPException:return None
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(reserve,range(4)))
    assert sum(value is not None for value in results)==1


@pytest.mark.parametrize('mutation',['model','tier','input','output','unknown'])
def test_usage_and_model_mismatch_stops_the_scope(tmp_path,mutation):
    budget=new(tmp_path);identity=budget.reserve(1000,3000,request_binding=SCOPE)
    payload={'model':module.MODEL,'service_tier':'default','usage':{'input_tokens':100,'output_tokens':20}}
    if mutation=='model':payload['model']='other'
    if mutation=='tier':payload['service_tier']='priority'
    if mutation=='input':payload['usage']['input_tokens']=1001
    if mutation=='output':payload['usage']['output_tokens']=3001
    if mutation=='unknown':payload['usage']=None
    with pytest.raises(HTTPException):budget.settle(identity,payload)
    assert not budget.availability()['can_request']


def test_sdk_dispatch_is_pinned_reserved_and_excludes_private_scope(environment,tmp_path,monkeypatch):
    from app.services import design_ai_provider as provider
    budget=new(tmp_path)
    monkeypatch.setattr(settings,'design_ai_scoped_acceptance_file',str(budget.path))
    monkeypatch.setattr(settings,'design_ai_model',module.MODEL)
    monkeypatch.setattr(settings,'design_ai_reasoning_effort','none')
    monkeypatch.setattr(settings,'design_ai_max_output_tokens',3000)
    monkeypatch.setattr(settings,'openai_api_key','EXPLICIT SDK DOUBLE KEY, NEVER TRANSMITTED')
    turn=SavedSolutionResponse(outcome='answer',message='EXPLICIT SDK RESPONSE DOUBLE',clarification=None,solution_edits=[],assumptions=[])
    requests=[]
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        def __init__(self,**kwargs):
            assert kwargs['max_retries']==0 and kwargs['base_url']=='https://api.openai.com/v1'
            self.responses=SimpleNamespace(with_raw_response=SimpleNamespace(parse=self.parse))
        async def parse(self,**kwargs):
            assert budget.availability()['request_count']==1
            requests.append(kwargs)
            payload={'model':module.MODEL,'service_tier':'default','id':'resp_fixture','usage':{'input_tokens':100,'output_tokens':20}}
            return SimpleNamespace(http_response=SimpleNamespace(json=lambda:payload),parse=lambda:SimpleNamespace(output_parsed=turn))
    monkeypatch.setattr(provider,'AsyncOpenAI',Client)
    result=asyncio.run(provider.OpenAIProvider().respond({'mode':'saved_solution','request':'Explain','_acceptance_binding':SCOPE}))
    assert result==turn and 'fixture-designer' not in json.dumps(requests[0]['input'])
    assert requests[0]['max_output_tokens']==3000 and requests[0]['reasoning']=={'effort':'none'}
    assert requests[0]['service_tier']=='default' and not requests[0].get('tools')


@pytest.mark.parametrize('failure,expected_stage',[('request','provider_request'),('parse','sdk_parse'),('schema','schema_validation'),('refusal','provider_refusal_or_incomplete')])
def test_scoped_failures_are_distinguishable_secret_free_and_stop_after_one(environment,tmp_path,monkeypatch,failure,expected_stage):
    from app.services import design_ai_provider as provider
    from openai import APIError
    import httpx
    budget=new(tmp_path)
    for key,value in {'design_ai_scoped_acceptance_file':str(budget.path),'design_ai_model':module.MODEL,
        'design_ai_reasoning_effort':'none','design_ai_max_output_tokens':3000,'openai_api_key':'OFFLINE SDK DOUBLE ONLY'}.items():monkeypatch.setattr(settings,key,value)
    calls=[]
    class Client:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        def __init__(self,**kwargs):self.responses=SimpleNamespace(with_raw_response=SimpleNamespace(parse=self.request))
        async def request(self,**kwargs):
            calls.append(kwargs)
            if failure=='request':raise APIError('PRIVATE UPSTREAM DETAIL',httpx.Request('POST','https://api.openai.com/v1/responses'),body=None)
            def parse():
                if failure=='parse':raise ValueError('PRIVATE PARSER DETAIL')
                return SimpleNamespace(output_parsed=None if failure=='refusal' else {'invented':'PRIVATE SCHEMA DETAIL'})
            return SimpleNamespace(http_response=SimpleNamespace(json=lambda:{'model':module.MODEL,'service_tier':'default','usage':{'input_tokens':100,'output_tokens':20}}),parse=parse)
    monkeypatch.setattr(provider,'AsyncOpenAI',Client)
    with pytest.raises(HTTPException) as error:asyncio.run(provider.OpenAIProvider().respond({'mode':'saved_solution','request':'Explain','_acceptance_binding':SCOPE}))
    assert error.value.detail['stage']==expected_stage and 'PRIVATE' not in json.dumps(error.value.detail)
    assert len(calls)==1 and budget.availability()['request_count']==1 and not budget.availability()['can_request']


def test_new_lower_recovery_caps_are_exclusive_and_do_not_change_closed_scope(tmp_path):
    old=new(tmp_path);old.close();before=old.path.read_bytes()
    path=tmp_path/'lower-recovery-fixture.sqlite'
    module.initialize(path,approved_binding=SCOPE,authorization_ref='OFFLINE LOWER-CAP APPROVAL DOUBLE',
        expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),max_requests=3,limit_nano=210_000_000)
    budget=module.Budget(path)
    for _ in range(3):settled(budget,budget.reserve(1000,3000,request_binding=SCOPE))
    assert budget.availability()['max_calls']==3 and budget.availability()['limit_usd']==0.21
    assert budget.availability()['lifetime_reserved_usd']==0.20295
    with pytest.raises(HTTPException):budget.reserve(1000,3000,request_binding=SCOPE)
    assert old.path.read_bytes()==before and not old.availability()['can_request']
    for calls,limit in [(7,210_000_000),(3,450_000_001),(0,210_000_000),(3,True)]:
        with pytest.raises(ValueError):module.initialize(tmp_path/'invalid.sqlite',approved_binding=SCOPE,authorization_ref='OFFLINE INVALID',
            expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),max_requests=calls,limit_nano=limit)
