"""Offline SDK adapter tests, never a live API key or live provider response."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from openai import APIError, APITimeoutError
from openai import AsyncOpenAI as RealOpenAIClient

from app.core.config import settings
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai_provider as module


class FakeOpenAIClient:
    def __init__(self, parse):
        self.responses = SimpleNamespace(parse=parse)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.parametrize("mode,expected", [("valid", 200), ("refusal", 502), ("malformed", 502), ("timeout", 504), ("failure", 502)])
def test_real_provider_adapter_with_mocked_sdk(environment, monkeypatch, mode, expected):
    monkeypatch.setattr(settings, "openai_api_key", "test-key-never-transmitted")
    monkeypatch.setattr(settings, "design_ai_model", "configured-test-model")
    turn = AssistantTurn(message="A grounded explanation", template_key=None, expected_revision=None, edits=[])
    result = turn if mode == "valid" else ({"invented": True} if mode == "malformed" else None)
    parse = AsyncMock(return_value=SimpleNamespace(output_parsed=result))
    if mode == "timeout":
        parse.side_effect = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    elif mode == "failure":
        parse.side_effect = APIError("Secret upstream detail must not be shown", httpx.Request("POST", "https://api.openai.com/v1/responses"), body=None)
    options = {}
    def constructor(**kwargs):
        options.update(kwargs)
        return FakeOpenAIClient(parse)
    monkeypatch.setattr(module, "AsyncOpenAI", constructor)
    async def run():
        if expected == 200:
            assert await module.OpenAIProvider().respond({"request": "Explain"}) == turn
        else:
            with pytest.raises(HTTPException) as exc:
                await module.OpenAIProvider().respond({"request": "Explain"})
            assert exc.value.status_code == expected
            assert "Secret upstream" not in exc.value.detail
    asyncio.run(run())
    assert options["max_retries"] == 0 and options["timeout"] == 40
    kwargs = parse.call_args.kwargs
    assert kwargs["store"] is False and kwargs["text_format"] is AssistantTurn
    assert "tools" not in kwargs and kwargs["model"] == "configured-test-model"


def test_context_is_bounded_before_network_call(environment, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-only")
    monkeypatch.setattr(settings, "design_ai_model", "test-model")
    monkeypatch.setattr(settings, "design_ai_context_chars", 4000)
    constructor = AsyncMock()
    monkeypatch.setattr(module, "AsyncOpenAI", constructor)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(module.OpenAIProvider().respond({"request": "x" * 5000}))
    assert exc.value.status_code == 422
    constructor.assert_not_called()


def test_provider_mode_is_explicit_without_exposing_credentials(environment, provider):
    from app.main import app
    from app.services.design_ai_provider import get_provider
    fixture=environment.get('/design-ai/config').json()
    assert fixture['provider_mode']=='test' and fixture['provider_name']=='Test provider'
    app.dependency_overrides.pop(get_provider)
    actual=environment.get('/design-ai/config').json()
    assert actual['provider_mode']=='real' and actual['provider_name']=='OpenAI'
    assert not actual['provider_configured'] and actual['model'] is None
    assert 'api_key' not in str(actual).lower()


def test_actual_openai_sdk_serialization_and_parsing_with_offline_http(environment, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key-never-transmitted")
    monkeypatch.setattr(settings, "design_ai_model", "configured-test-model")
    expected = AssistantTurn(message="Offline HTTP fixture", template_key="dutch", expected_revision=None, edits=[])
    calls = []
    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert request.url.path == "/v1/responses"
        assert body["store"] is False
        assert body["service_tier"] == "default"
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        assert body["text"]["format"]["schema"]["additionalProperties"] is False
        return httpx.Response(200, json={"id": "resp_offline_test", "object": "response", "created_at": 0,
            "status": "completed", "model": "configured-test-model", "output": [{"type": "message", "id": "msg_offline_test",
            "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": expected.model_dump_json(), "annotations": []}]}]})
    def constructor(**kwargs):
        return RealOpenAIClient(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(module, "AsyncOpenAI", constructor)
    assert asyncio.run(module.OpenAIProvider().respond({"request": "Find a Dutch template"})) == expected
    assert len(calls) == 1


def test_budgeted_sdk_records_usage_before_parsing(environment, monkeypatch, tmp_path):
    from app.services.design_ai_budget import Budget, initialize
    ledger=tmp_path/'batch.sqlite3'
    initialize(ledger)
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(ledger))
    monkeypatch.setattr(settings,'database_url','postgresql+psycopg://local@127.0.0.1/design_ai_acceptance_test')
    monkeypatch.setattr(settings,'openai_api_key','offline-only')
    monkeypatch.setattr(settings,'design_ai_model','gpt-6-luna')
    monkeypatch.setattr(settings,'design_ai_reasoning_effort','low')
    monkeypatch.setattr(settings,'design_ai_max_output_tokens',2000)
    calls=[]
    def handler(request):
        body=json.loads(request.content)
        calls.append(body)
        assert body['model']=='gpt-6-luna' and body['reasoning']=={'effort':'low'}
        assert body['service_tier']=='default' and body['max_output_tokens']==2000
        assert len(Budget(ledger).report()['requests'])==1  # Reservation preceded HTTP.
        return httpx.Response(200,json={'id':'resp_budget_test','object':'response','created_at':0,
            'status':'completed','model':'gpt-6-luna','output':[{'type':'message','id':'message_test','role':'assistant',
            'status':'completed','content':[{'type':'output_text','text':'invalid structured JSON','annotations':[]}]}],
            'usage':{'input_tokens':1000,'output_tokens':100,'total_tokens':1100,
            'input_tokens_details':{'cached_tokens':100,'cache_write_tokens':400},'output_tokens_details':{'reasoning_tokens':10}}})
    monkeypatch.setattr(module,'AsyncOpenAI',lambda **kwargs: RealOpenAIClient(**kwargs,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    with pytest.raises(HTTPException) as error:
        asyncio.run(module.OpenAIProvider().respond({'request':'Explain'}))
    assert error.value.status_code==502 and len(calls)==1
    row=Budget(ledger).report()['requests'][0]
    assert row['usage']['total_tokens']==1100 and row['held']==175000
    report=Budget(ledger).report()
    assert report['estimated_usage_cost_usd']==.000151
    assert report['token_usage']['reasoning_tokens']==10  # Included in output, not added twice.
