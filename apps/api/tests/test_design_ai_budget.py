from concurrent.futures import ThreadPoolExecutor
import sqlite3

from fastapi import HTTPException
import pytest

from app.services.design_ai_budget import Budget, initialize, LIMIT, MAX_INPUT, RESERVATION


def test_followup_has_separate_persisted_ten_cent_allowance(tmp_path):
    import hashlib
    old=tmp_path/'old.sqlite3'
    initialize(old)
    Budget(old).close()
    before=hashlib.sha256(old.read_bytes()).hexdigest()
    new=tmp_path/'new.sqlite3'
    initialize(new,limit_usd='.10',max_calls=2)
    budget=Budget(new)
    assert budget.report()['limit_usd']==.10 and budget.report()['max_calls']==2
    first=budget.reserve(16000,2000)
    with sqlite3.connect(new) as db:
        db.execute('UPDATE requests SET held=? WHERE id=?',(100_000_000-RESERVATION+1,first))
    with pytest.raises(HTTPException) as error:
        budget.reserve(16000,2000)
    assert error.value.status_code==429
    assert Budget(old).report()['closed']
    assert hashlib.sha256(old.read_bytes()).hexdigest()==before


def test_reservations_survive_restart_and_concurrent_calls(tmp_path):
    path=tmp_path/'budget.sqlite3'
    initialize(path)
    def reserve(_):
        try:
            return Budget(path).reserve(16000,2000)
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(reserve,range(15)))
    assert results.count(429)==4
    report=Budget(path).report()
    assert len(report['requests'])==11
    assert sum(row['held'] for row in report['requests'])==11*RESERVATION
    with pytest.raises(FileExistsError):
        initialize(path)


def test_insufficient_remaining_budget_and_closed_batch_stop_before_call(tmp_path):
    path=tmp_path/'budget.sqlite3'
    initialize(path)
    budget=Budget(path)
    first=budget.reserve(16000,2000)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE requests SET held=? WHERE id=?',(LIMIT-RESERVATION+1,first))
    with pytest.raises(HTTPException) as error:
        budget.reserve(16000,2000)
    assert error.value.status_code==429
    budget.close()
    assert budget.report()['closed']


def test_input_bound_unknown_usage_and_excess_usage_are_fail_closed(tmp_path):
    path=tmp_path/'budget.sqlite3'
    initialize(path)
    budget=Budget(path)
    with pytest.raises(HTTPException):
        budget.reserve(MAX_INPUT+1,2000)
    assert budget.report()['requests']==[]
    first=budget.reserve(16000,2000)
    budget.failed(first,'timeout')
    assert budget.report()['requests'][0]['held']==RESERVATION
    second=budget.reserve(16000,2000)
    with pytest.raises(HTTPException):
        budget.settle(second,{'usage':{'input_tokens':MAX_INPUT+1,'output_tokens':2000}})
    assert budget.report()['closed']


@pytest.mark.parametrize('reason',['closed','call_limit','insufficient_budget'])
def test_paused_allowance_has_machine_readable_nonretryable_reason(tmp_path,reason):
    path=tmp_path/'manual.sqlite3'
    initialize(path,limit_usd='.10',max_calls=1 if reason=='call_limit' else 10)
    budget=Budget(path)
    if reason=='closed':budget.close()
    else:
        request=budget.reserve(16000,2000)
        if reason=='insufficient_budget':
            with sqlite3.connect(path) as db:db.execute('UPDATE requests SET held=? WHERE id=?',(100_000_000-RESERVATION+1,request))
    before=len(budget.report()['requests'])
    with pytest.raises(HTTPException) as failure:budget.reserve(16000,2000)
    assert failure.value.detail['code']=='design_ai_allowance_paused'
    assert failure.value.detail['allowance']['blocked_reason']==reason
    assert 'AI testing is paused by the local test allowance' in failure.value.detail['message']
    assert len(budget.report()['requests'])==before


def test_manual_allowance_status_is_read_only_and_accounts_for_unknown_usage(tmp_path):
    import hashlib
    path=tmp_path/'manual.sqlite3'
    initialize(path,limit_usd='.10',max_calls=10)
    budget=Budget(path)
    request=budget.reserve(16000,2000)
    budget.failed(request,'timeout_usage_unknown')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    state=budget.availability()
    assert state['can_request'] and state['remaining_calls']==9
    assert state['remaining_usd']==.095 and state['next_reservation_usd']==.005
    assert state['unsettled_holds_usd']==.005 and state['outstanding_reservations']==0
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_config_reports_allowance_without_reserving_or_exposing_path(environment,provider,monkeypatch,tmp_path):
    import hashlib
    from app.core.config import settings
    path=tmp_path/'manual.sqlite3'
    initialize(path,limit_usd='.10',max_calls=10)
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(path))
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    response=environment.get('/design-ai/config')
    assert response.status_code==200
    state=response.json()['test_allowance']
    assert state['can_request'] and state['remaining_calls']==10 and state['remaining_usd']==.10
    assert str(path) not in response.text and not provider.contexts
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    Budget(path).close()
    assert environment.get('/design-ai/config').json()['test_allowance']['blocked_reason']=='closed'
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file',str(tmp_path/'missing.sqlite3'))
    assert environment.get('/design-ai/config').json()['test_allowance']['blocked_reason']=='unavailable'
    assert not (tmp_path/'missing.sqlite3').exists()
