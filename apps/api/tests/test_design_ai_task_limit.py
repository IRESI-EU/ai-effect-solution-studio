"""Task ceiling tests use only disposable offline ledgers, never the active ledger."""
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from app.services.design_ai_budget import Budget, initialize, RESERVATION


def checkpoint(path, config, *, cost=10_000_000):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute("SELECT id,held,reserved,input_bound,usage,status,response_id FROM requests ORDER BY id")]
    config.write_text(json.dumps({"ledger":path.name,"baseline_count":len(rows),"baseline_sha256":hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),"max_calls":2,"max_reserved_nano":cost}))


def test_task_limit_atomic_persistent_and_preserves_prior_consumption(tmp_path):
    path, config = tmp_path/'existing.sqlite3', tmp_path/'checkpoint.json'
    initialize(path,limit_usd='.10',max_calls=10)
    prior = Budget(path).reserve(16000,2000)
    Budget(path).settle(prior,{"status":"completed","usage":{"input_tokens":1000,"output_tokens":100}})
    checkpoint(path,config)
    before = path.read_bytes()
    assert Budget(path,task_limit_file=config).availability()['task_allowance']['remaining_calls'] == 2
    assert path.read_bytes() == before
    def reserve(_):
        try: return Budget(path,task_limit_file=config).reserve(16000,2000)
        except HTTPException as error: return error.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(reserve,range(8)))
    assert rows.count(429) == 6
    report = Budget(path).report()
    assert report['max_calls'] == 10 and report['limit_usd'] == .10
    assert len(report['requests']) == 3 and report['requests'][0]['held'] == 175000
    for row in report['requests'][1:]: Budget(path).settle(row['id'],{"status":"completed","usage":{"input_tokens":1,"output_tokens":1}})
    state = Budget(path,task_limit_file=config).availability()
    assert state['task_allowance']['reserved_usd'] == .01 and not state['can_request']
    with pytest.raises(HTTPException) as blocked: Budget(path,task_limit_file=config).reserve(16000,2000)
    assert blocked.value.status_code == 429


def test_cost_ceiling_failure_holds_and_invalid_checkpoint_fail_closed(tmp_path):
    path, config = tmp_path/'existing.sqlite3', tmp_path/'checkpoint.json'
    initialize(path)
    checkpoint(path,config,cost=RESERVATION)
    budget = Budget(path,task_limit_file=config)
    first = budget.reserve(16000,2000)
    budget.failed(first,'timeout_usage_unknown')
    with pytest.raises(HTTPException): budget.reserve(16000,2000)
    assert Budget(path).availability()['unsettled_holds_usd'] == .005
    saved = config.read_text()
    for value in ('{}', 'invalid', saved.replace('"max_calls": 2','"max_calls": 4'), saved.replace('"baseline_count": 0','"baseline_count": 99')):
        config.write_text(value)
        with pytest.raises(HTTPException) as blocked: budget.reserve(16000,2000)
        assert blocked.value.status_code == 503
    config.unlink()
    with pytest.raises(HTTPException): budget.reserve(16000,2000)
    assert len(Budget(path).report()['requests']) == 1


def test_provider_task_cap_rejects_third_before_sdk(environment, monkeypatch, tmp_path):
    import asyncio
    from app.core.config import settings
    from app.services import design_ai_provider as provider
    path, config = tmp_path/'existing.sqlite3', tmp_path/'checkpoint.json'
    initialize(path)
    checkpoint(path,config)
    for _ in range(2): Budget(path,task_limit_file=config).reserve(16000,2000)
    monkeypatch.setattr(settings,'openai_api_key','offline-test-never-sent')
    monkeypatch.setattr(settings,'design_ai_model','gpt-6-luna')
    monkeypatch.setattr(settings,'design_ai_reasoning_effort','low')
    monkeypatch.setattr(settings,'design_ai_max_output_tokens',2000)
    monkeypatch.setattr(settings,'database_url','postgresql+psycopg://local@127.0.0.1/design_ai_acceptance_test')
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(path))
    monkeypatch.setattr(settings,'design_ai_acceptance_task_limit_file',str(config))
    def forbidden(**kwargs): raise AssertionError('No SDK construction allowed after task cap')
    monkeypatch.setattr(provider,'AsyncOpenAI',forbidden)
    with pytest.raises(HTTPException) as blocked: asyncio.run(provider.OpenAIProvider().respond({'request':'offline'}))
    assert blocked.value.status_code == 429


def test_manual_three_call_checkpoint_reserves_lifetime_cost_and_blocks_fourth(tmp_path):
    path, config = tmp_path/'shared.sqlite3', tmp_path/'manual.json'
    initialize(path, limit_usd='.10', max_calls=10)
    for _ in range(6):
        row = Budget(path).reserve(16000,2000)
        Budget(path).settle(row, {'status':'completed','usage':{'input_tokens':1,'output_tokens':1}})
    checkpoint(path,config,cost=15_000_000)
    policy=json.loads(config.read_text());policy['max_calls']=3;config.write_text(json.dumps(policy))
    budget=Budget(path,task_limit_file=config)
    before=path.read_bytes()
    assert budget.availability()['task_allowance']['remaining_calls']==3
    assert path.read_bytes()==before
    for _ in range(3):
        row=budget.reserve(16000,2000)
        budget.settle(row,{'status':'completed','usage':{'input_tokens':1,'output_tokens':1}})
    assert budget.availability()['task_allowance']['reserved_usd']==.015
    assert budget.availability()['task_allowance']['remaining_calls']==0
    assert Budget(path).availability()['remaining_calls']==1  # Shared budget alone would allow a fourth.
    with pytest.raises(HTTPException) as blocked: budget.reserve(16000,2000)
    assert blocked.value.status_code==429
    assert Budget(path).report()['max_calls']==10
