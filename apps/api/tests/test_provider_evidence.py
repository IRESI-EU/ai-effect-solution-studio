"""Future evidence capture only. Every SDK/HTTP response is an offline double."""
import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai_provider as provider, provider_evidence as evidence


def record(caplog):
    return json.loads(next(r.message for r in caplog.records if r.name == "design_ai.provider.audit"))


@pytest.mark.parametrize("metadata", [True, False])
def test_capture_actual_sdk_metadata_hashes_and_validated_turn(environment, monkeypatch, tmp_path, caplog, metadata):
    from app.services.design_ai_budget import initialize, Budget
    caplog.set_level(logging.DEBUG, logger="design_ai.provider.audit")
    ledger = tmp_path / "synthetic.sqlite3"
    initialize(ledger)
    for name, value in dict(openai_api_key="offline-only", design_ai_model="gpt-6-luna",
            design_ai_reasoning_effort="low", design_ai_max_output_tokens=2000,
            design_ai_acceptance_budget_file=str(ledger),
            database_url="postgresql+psycopg://local@127.0.0.1/design_ai_acceptance_test").items():
        monkeypatch.setattr(settings, name, value)
    turn = AssistantTurn(message="Offline result", template_key=None, expected_revision=2, edits=[])
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        payload = dict(object="response", created_at=0, status="completed", output=[dict(type="message",
            id="msg_fixture", role="assistant", status="completed", content=[dict(type="output_text", text=turn.model_dump_json(), annotations=[])])],
            usage=dict(input_tokens=100, output_tokens=4, total_tokens=104,
                input_tokens_details=dict(cached_tokens=20, cache_write_tokens=10, unexpected="private"),
                output_tokens_details=dict(reasoning_tokens=1)))
        if metadata:
            payload.update(id="resp_fixture", model="returned-model-revision", service_tier="flex")
        return httpx.Response(200, json=payload, headers={"x-request-id": "req_fixture", "authorization": "Bearer never-retain"} if metadata else {})
    monkeypatch.setattr(provider, "AsyncOpenAI", lambda **kwargs: AsyncOpenAI(**kwargs,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    context = {"request": "Explain", "history": []}
    with evidence.correlation(conversation_id="conversation-fixture", draft_id="draft-fixture", revision=2):
        assert asyncio.run(provider.OpenAIProvider().respond(context)) == turn
    audit = record(caplog)
    assert len(calls) == 1 and "conversation_id" not in calls[0]["input"][1]["content"]
    assert audit["requested_model"] == "gpt-6-luna" and audit["requested_service_tier"] == "default"
    assert audit["returned_model"] == ("returned-model-revision" if metadata else None)
    assert audit["returned_service_tier"] == ("flex" if metadata else None)
    assert audit["request_id"] == ("req_fixture" if metadata else None)
    assert audit["response_id"] == ("resp_fixture" if metadata else None)
    if not metadata:
        assert {"returned_model", "returned_service_tier", "request_id", "response_id"} <= set(audit["unavailable_fields"])
    assert audit["validated_response"] == turn.model_dump(mode="json")
    assert audit["validated_response_sha256"] == evidence.digest(turn.model_dump(mode="json"))
    assert len(audit["request_sha256"]) == len(audit["configuration_sha256"]) == 64
    config = dict(model="gpt-6-luna", store=False, service_tier="default", max_output_tokens=2000, reasoning={"effort": "low"})
    config["transport"] = dict(endpoint="responses", max_retries=0, timeout_seconds=40)
    assert audit["requested_configuration"] == config
    assert audit["request_sha256"] == evidence.digest(dict(configuration=config, input=calls[0]["input"], schema=AssistantTurn.model_json_schema()))
    assert audit["configuration_sha256"] == evidence.digest(dict(configuration=config, schema=AssistantTurn.model_json_schema()))
    assert audit["request_sha256"] != audit["configuration_sha256"]
    assert audit["usage"]["input_tokens_details"] == {"cached_tokens": 20, "cache_write_tokens": 10}
    assert audit["usage"]["output_tokens_details"] == {"reasoning_tokens": 1}
    assert audit["correlation"] == dict(conversation_id="conversation-fixture", draft_id="draft-fixture", revision=2, accounting_permit="1")
    assert Budget(ledger).report()["requests"][0]["usage"]["total_tokens"] == 104
    assert "never-retain" not in json.dumps(audit) and "conversation_input" not in audit


def test_evidence_redaction_preserves_response_and_only_numeric_usage(caplog):
    caplog.set_level(logging.DEBUG, logger="design_ai.provider.audit")
    turn = AssistantTurn(message=r"Do not follow: C:\private\data.csv /private/data.csv sk-fake-secret Bearer fake-secret", template_key=None,
        expected_revision=0, edits=[dict(kind="set_run_input", node_id=None,
            value=json.dumps(dict(dataset_bytes="row-secret", private_path="/private/file", authorization="Bearer secret", seed=43)))])
    original = turn.model_dump_json()
    evidence.finish({}, payload={"model": "safe", "usage": {"input_tokens": True, "output_tokens": 1}}, response=None,
        request_id=None, validated=turn)
    audit = record(caplog)
    serialized = json.dumps(audit)
    for forbidden in ("row-secret", "fake-secret", "data.csv", "private_path", "authorization"):
        assert forbidden not in serialized
    assert json.loads(audit["validated_response"]["edits"][0]["value"]) == {"seed": 43}
    assert audit["usage"] is None and "usage" in audit["unavailable_fields"]
    assert turn.model_dump_json() == original
    assert evidence.sanitize("a,b\n1,2\n3,4") == "[dataset content omitted]"
    assert evidence.sanitize("CSV follows:\na,b\n1,2") == "[dataset content omitted]"
    assert evidence.sanitize(r"Read C:\private directory\sensitive file.csv now") == "[private path omitted]"


def test_disabled_capture_does_no_serialization(monkeypatch):
    monkeypatch.setattr(logging.getLogger("design_ai.provider.audit"), "isEnabledFor", lambda level: False)
    assert evidence.begin({}, None, None, 40) is None


def test_capture_failure_does_not_change_provider_result(environment, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "offline-only")
    monkeypatch.setattr(settings, "design_ai_model", "offline-model")
    logger = logging.getLogger("design_ai.provider.audit")
    monkeypatch.setattr(logger, "isEnabledFor", lambda level: True)
    monkeypatch.setattr(logger, "debug", lambda *args: (_ for _ in ()).throw(OSError("private filename")))
    turn = AssistantTurn(message="Offline fixture", template_key=None, expected_revision=None, edits=[])
    class SDK:
        responses = SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=turn)))
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
    monkeypatch.setattr(provider, "AsyncOpenAI", lambda **kwargs: SDK())
    assert asyncio.run(provider.OpenAIProvider().respond({"request": "Explain"})) == turn


def test_correlation_isolated_across_tasks_and_exception():
    async def run():
        async def one(identifier):
            with evidence.correlation(conversation_id=identifier, draft_id=None, revision=None):
                await asyncio.sleep(0)
                assert evidence._correlation.get()["conversation_id"] == identifier
        await asyncio.gather(one("first"), one("second"))
        with pytest.raises(ValueError):
            with evidence.correlation(conversation_id="failed", draft_id=None, revision=None):
                raise ValueError()
        assert evidence._correlation.get() is None
    asyncio.run(run())


def test_normal_chat_correlates_server_revision_without_changing_model_context(environment, provider, monkeypatch):
    draft = environment.post("/design-ai/drafts", json={"template_key": "denmark"}).json()
    seen = []
    original = provider.respond
    async def respond(context):
        seen.append(evidence._correlation.get())
        assert "conversation_id" not in context
        return await original(context)
    monkeypatch.setattr(provider, "respond", respond)
    conversation = "12345678-1234-4234-8234-123456789abc"
    body = dict(message="Rename", draft_id=draft["id"], revision=0, conversation_id=conversation)
    result = environment.post("/design-ai/chat", json=body)
    assert result.status_code == 200, result.text
    assert seen == [dict(conversation_id=conversation, draft_id=draft["id"], revision=0)]
    assert evidence._correlation.get() is None
    assert environment.post("/design-ai/chat", json={**body, "revision": 9}).status_code == 409
    assert len(seen) == 1
    assert environment.post("/design-ai/chat", json={**body, "conversation_id": "/private/path"}).status_code == 422
