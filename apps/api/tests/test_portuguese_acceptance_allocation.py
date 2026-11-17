"""Only suite-created synthetic ledgers; no real policy activation or provider."""
from copy import deepcopy
import sqlite3

import pytest
from fastapi import HTTPException

from app.services.shared_allowance import Authority, rows
from test_shared_allowance import ledger, activate, complete_acceptance, reserve, settle, fingerprint, binding, claims, TOKEN  # noqa: F401

SCOPE='pt-provider-acceptance-20261116'
BINDING={**binding(),'consumer_id':'pt-registered-design-review','environment':'portuguese-sandbox-local'}
CLAIMS={**claims(scope=SCOPE),'consumer_id':BINDING['consumer_id'],'environment':BINDING['environment']}


def exhausted_beta(path):
    complete_acceptance(path);activate(path,phase='beta')
    for _ in range(10):settle(path,reserve(path,scope='beta-20261111'),scope='beta-20261111')


def proposed(path,**changes):
    return activate(path,phase='portuguese_acceptance',scope_id=SCOPE,bindings=[deepcopy(BINDING)],acceptance_evidence='a'*64,**changes)


def test_new_three_case_allocation_is_separate_bounded_audited_and_dry_run_default(ledger):
    exhausted_beta(ledger);before=ledger.read_bytes()
    with sqlite3.connect(ledger) as db:history=rows(db);audits=db.execute('select * from authority_events').fetchall()
    assert proposed(ledger,apply=False)['proposal']['after_calls']==28 and ledger.read_bytes()==before
    proposed(ledger)
    assert Authority(ledger).availability(TOKEN,claims(scope='beta-20261111'))['blocked_reason']=='inactive_scope'
    for _ in range(3):
        from uuid import uuid4
        from app.services.shared_allowance import CONTROLS
        receipt=Authority(ledger).reserve(TOKEN,CLAIMS,str(uuid4()),32000,2000,CONTROLS)
        from test_shared_allowance import usage
        result=Authority(ledger).settle(TOKEN,CLAIMS,receipt['request_key'],usage(receipt['request_key']))
        Authority(ledger).acknowledge(TOKEN,CLAIMS,receipt['request_key'],result['usage_sha256'])
    state=Authority(ledger).availability(TOKEN,CLAIMS)
    assert state['request_count']==state['max_calls']==28 and state['scope_count']==state['scope_max_calls']==3
    assert state['scope_reserved_nano']==state['scope_limit_nano']==15000000 and state['limit_usd']==0.1
    assert state['blocked_reason']=='call_limit' and state['outstanding_reservations']==0
    with sqlite3.connect(ledger) as db:
        assert rows(db)[:25]==history
        assert db.execute('select * from authority_events order by seq limit ?', (len(audits),)).fetchall()==audits
    with pytest.raises(HTTPException):Authority(ledger).reserve(TOKEN,CLAIMS,str(uuid4()),1,1,CONTROLS)
    with pytest.raises(HTTPException):proposed(ledger)


@pytest.mark.parametrize('change',[{'scope_id':'beta-20261111'},{'bindings':[binding()]},{'bindings':[BINDING,BINDING]},{'acceptance_evidence':''},{'acceptance_evidence':'not-a-frozen-hash'}])
def test_no_other_scope_or_environment_can_use_new_transition(ledger,change):
    exhausted_beta(ledger);before=fingerprint(ledger)
    values={'phase':'portuguese_acceptance','scope_id':SCOPE,'bindings':[BINDING],'acceptance_evidence':'a'*64,**change}
    with pytest.raises((ValueError,HTTPException)):activate(ledger,**values)
    assert fingerprint(ledger)==before


def test_incomplete_beta_and_closed_global_policy_cannot_be_reopened(ledger):
    complete_acceptance(ledger);activate(ledger,phase='beta')
    with pytest.raises(HTTPException):proposed(ledger)
    for _ in range(10):settle(ledger,reserve(ledger,scope='beta-20261111'),scope='beta-20261111')
    Authority(ledger).stop(scope_id='beta-20261111',expected_sha256=fingerprint(ledger),operator='synthetic',authorization_ref='test closure')
    before=fingerprint(ledger)
    with pytest.raises(HTTPException):proposed(ledger)
    assert fingerprint(ledger)==before
