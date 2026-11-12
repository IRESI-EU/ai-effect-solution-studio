"""Private authority protocol and provider adapter; every provider is a double."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app.accounting_authority import create_app
from app.core.config import settings
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai_provider as provider
from app.services.allowance_client import Client
from app.services.shared_allowance import Authority
from test_shared_allowance import TOKEN, activate, claims, ledger, SCOPE  # noqa: F401


@pytest.fixture
def setup(ledger,monkeypatch):
    activate(ledger)
    values={"database_url":"postgresql://review_role:unused@postgres:5432/production_name",
        "design_ai_restricted_beta":True,"design_ai_reviewer_ids":"named-existing-reviewer-id",
        "design_ai_budget_authority_url":"http://127.0.0.1:1","design_ai_budget_authority_socket":"",
        "design_ai_budget_authority_token":TOKEN,"design_ai_budget_authority_id":"synthetic-authority-01",
        "design_ai_budget_scope":"acceptance-20261111","design_ai_budget_consumer":"review-a",
        "design_ai_budget_environment":"preproduction","design_ai_acceptance_budget_file":"",
        "design_ai_acceptance_task_limit_file":"","design_ai_model":"gpt-6-luna",
        "design_ai_reasoning_effort":"low","design_ai_max_output_tokens":2000,
        "openai_api_key":"test-only-not-transmitted"}
    for k,v in values.items():monkeypatch.setattr(settings,k,v)
    calls=[]
    with TestClient(create_app(ledger)) as server:
        def handle(request):
            body=json.loads(request.content);calls.append((request.url.path,deepcopy(body)))
            response=server.post(request.url.path,json=body,headers={"Authorization":request.headers.get("Authorization","")})
            return httpx.Response(response.status_code,json=response.json())
        transport=httpx.MockTransport(handle)
        yield ledger,transport,calls,server


def test_protocol_auth_scope_identity_and_no_policy_endpoint(setup):
    path,transport,calls,server=setup
    client=Client(settings,transport=transport)
    assert client.availability()["can_request"]
    body=claims()
    assert server.post('/v1/status',json=body).status_code==401
    assert server.post('/v1/status',json=body,headers={'Authorization':'Bearer '+'invalid'*8}).status_code==403
    assert server.post('/v1/activate',json={}).status_code==404
    assert server.get('/openapi.json').status_code==404


@pytest.mark.parametrize("failure",["timeout","server_error","redirect","bad_identity","malformed"])
def test_accounting_failure_is_one_attempt_and_never_dispatches_or_falls_back(setup,monkeypatch,failure):
    path,_,calls,server=setup;attempts=[]
    def handle(request):
        attempts.append(request)
        if failure=='timeout':raise httpx.ReadTimeout('Synthetic uncertainty',request=request)
        if failure=='server_error':return httpx.Response(503,json={})
        if failure=='redirect':return httpx.Response(307,headers={'Location':'https://other.example/'})
        if failure=='malformed':return httpx.Response(200,json=[])
        return httpx.Response(200,json={'authority_id':'wrong','scope':settings.design_ai_budget_scope})
    client=Client(settings,transport=httpx.MockTransport(handle))
    with pytest.raises(HTTPException):client.reserve(100,2000)
    assert len(attempts)==1
    assert Authority(path).availability(TOKEN,claims())['request_count']==13


def test_lost_reservation_ack_is_durable_and_never_permits_replay(setup):
    path,transport,calls,server=setup
    def lose_ack(request):
        transport.handle_request(request)
        raise httpx.ReadTimeout('Response lost after commit',request=request)
    client=Client(settings,transport=httpx.MockTransport(lose_ack))
    with pytest.raises(HTTPException):client.reserve(100,2000)
    assert Authority(path).availability(TOKEN,claims())['outstanding_reservations']==1
    receipt=Authority(path).lookup(TOKEN,claims(),client.key)
    assert not receipt['dispatch_allowed']
    with pytest.raises(HTTPException):Client(settings,transport=transport).reserve(100,2000)


def test_lost_settlement_receipt_keeps_all_environments_paused_without_automatic_retry(setup):
    path,transport,calls,server=setup
    client=Client(settings,transport=transport);key=client.reserve(100,2000)
    def lose_settlement(request):
        response=transport.handle_request(request)
        if request.url.path=='/v1/settle':raise httpx.ReadTimeout('Settlement reply lost',request=request)
        return response
    client.transport=httpx.MockTransport(lose_settlement)
    with pytest.raises(HTTPException):client.settle(key,{'id':'test-reply','service_tier':'default','usage':{'input_tokens':10,'output_tokens':1}})
    client.failed(key,'failure')  # No second transport attempt in exception/finally.
    assert [r[0] for r in calls]==['/v1/reserve','/v1/settle']
    assert Authority(path).availability(TOKEN,claims())['blocked_reason']=='outstanding_usage'


def test_scope_never_falls_back_to_legacy_budget_or_impersonates_local_profile(setup,monkeypatch):
    path,transport,calls,server=setup
    monkeypatch.setattr(settings,'database_url','postgresql://review_role:unused@postgres:5432/design_aie37_qualification')
    with pytest.raises(HTTPException):Client(settings,transport=transport).reserve(100,2000)
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(path))
    with pytest.raises(HTTPException):Client(settings,transport=transport)


@pytest.mark.parametrize("url",['http://external.example','http://user:password@127.0.0.1','https://example.test/path','https://example.test/?token=x'])
def test_unreviewed_transport_or_embedded_credentials_are_denied(setup,monkeypatch,url):
    monkeypatch.setattr(settings,'design_ai_budget_authority_url',url)
    with pytest.raises(HTTPException):Client(settings)


@pytest.mark.parametrize('mode',['valid','malformed'])
def test_provider_uses_normal_sdk_only_after_fresh_reservation_and_settles_before_parse(setup,monkeypatch,mode):
    path,transport,calls,server=setup
    from app.services import allowance_client
    original=allowance_client.Client
    monkeypatch.setattr(allowance_client,'Client',lambda config:original(config,transport=transport))
    sdk=[]
    turn=AssistantTurn(message='Synthetic adapter test, not genuine acceptance',template_key=None,expected_revision=None,edits=[])
    class Raw:
        http_response=SimpleNamespace(json=lambda:{'id':'synthetic-provider-response','service_tier':'default','usage':{'input_tokens':100,'output_tokens':2}})
        def parse(self):
            assert Authority(path).availability(TOKEN,claims())['outstanding_reservations']==0
            if mode=='malformed':raise ValueError('Synthetic malformed response')
            return SimpleNamespace(output_parsed=turn)
    async def parse(**kwargs):sdk.append(kwargs);return Raw()
    class SDK:
        responses=SimpleNamespace(with_raw_response=SimpleNamespace(parse=parse))
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
    def constructor(**kwargs):
        assert calls[-1][0]=='/v1/reserve' and Authority(path).availability(TOKEN,claims())['outstanding_reservations']==1
        assert kwargs['max_retries']==0
        return SDK()
    monkeypatch.setattr(provider,'AsyncOpenAI',constructor)
    if mode=='valid':assert asyncio.run(provider.OpenAIProvider().respond({'request':'Synthetic test'}))==turn
    else:
        with pytest.raises(HTTPException):asyncio.run(provider.OpenAIProvider().respond({'request':'Synthetic test'}))
    assert len(sdk)==1 and sdk[0]['service_tier']=='default' and sdk[0]['max_output_tokens']==2000
    assert sdk[0]['reasoning']=={'effort':'low'} and sdk[0]['prompt_cache_options']=={'ttl':'30m'}
    assert [c[0] for c in calls]==['/v1/reserve','/v1/settle','/v1/acknowledge']
    settled=calls[-2][1]['payload'];assert set(settled)=={'id','usage','service_tier'}
    assert 'Synthetic test' not in json.dumps(settled)


def test_provider_never_constructs_sdk_when_authority_is_unavailable(setup,monkeypatch):
    from app.services import allowance_client
    original=allowance_client.Client
    def fail(request):raise httpx.ConnectError('Authority offline',request=request)
    monkeypatch.setattr(allowance_client,'Client',lambda config:original(config,transport=httpx.MockTransport(fail)))
    monkeypatch.setattr(provider,'AsyncOpenAI',lambda **kwargs:pytest.fail('No provider without accounting'))
    with pytest.raises(HTTPException):asyncio.run(provider.OpenAIProvider().respond({'request':'Never send'}))


def test_legacy_database_guard_is_unchanged_for_production_identity(setup,monkeypatch):
    path,_,_,_=setup
    for name in ('authority_url','authority_socket','authority_token','authority_id','scope','consumer','environment'):
        monkeypatch.setattr(settings,'design_ai_budget_'+name,'')
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(path))
    monkeypatch.setattr(settings,'design_ai_acceptance_task_limit_file','unused-checkpoint')
    monkeypatch.setattr(provider,'AsyncOpenAI',lambda **kwargs:pytest.fail('Legacy guard must prevent provider construction'))
    with pytest.raises(HTTPException,match='isolated local database'):
        asyncio.run(provider.OpenAIProvider().respond({'request':'Never send'}))


def test_normal_config_reads_authority_without_exposing_credentials(environment,setup,monkeypatch):
    from app.services import allowance_client
    _,transport,calls,_=setup
    original=allowance_client.Client
    monkeypatch.setattr(allowance_client,'Client',lambda config:original(config,transport=transport))
    monkeypatch.setattr(settings,'design_ai_reviewer_ids','designer')
    response=environment.get('/design-ai/config')
    assert response.status_code==200
    value=response.json()
    assert value['test_allowance']['authority_id']=='synthetic-authority-01'
    assert TOKEN not in response.text and settings.openai_api_key not in response.text
    assert [row[0] for row in calls]==['/v1/status']
