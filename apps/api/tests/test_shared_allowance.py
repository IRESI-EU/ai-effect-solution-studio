"""Synthetic ledgers only. Never open/copy the real 13-call allowance."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.services.shared_allowance import Authority, CONTROLS, RESERVATION, database_scope, rows
from app.services.design_ai_budget import Budget

TOKEN="synthetic-authority-token-not-a-secret-0001"
SECOND="synthetic-authority-token-not-a-secret-0002"
SCOPE=database_scope("postgresql://review_role:unused@postgres:5432/production_name")


def fingerprint(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(consumer="review-a", token=TOKEN):
    return {"consumer_id":consumer,"environment":"preproduction","database_scope":SCOPE,
            "token_sha256":hashlib.sha256(token.encode()).hexdigest()}


def claims(consumer="review-a", scope="acceptance-20261111"):
    return {"consumer_id":consumer,"environment":"preproduction","database_scope":SCOPE,"scope":scope}


def initialize_synthetic(path):
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE batch(id INTEGER PRIMARY KEY,closed INTEGER,limit_nano INTEGER,max_calls INTEGER);"
                        "CREATE TABLE requests(id INTEGER PRIMARY KEY,held INTEGER,reserved INTEGER,input_bound INTEGER,usage TEXT,status TEXT,response_id TEXT);"
                        "CREATE TABLE allowance_amendments(id TEXT,audit_json TEXT);")
        db.execute("INSERT INTO batch VALUES(1,0,100000000,13)")
        db.execute("INSERT INTO allowance_amendments VALUES('synthetic-history','preserve exact audit bytes')")
        for index in range(1,14):
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,?)",(index,1500,RESERVATION,10000,json.dumps({"input_tokens":8,"output_tokens":1}),"completed","synthetic-prior-"+str(index)))


@pytest.fixture
def ledger(tmp_path):
    path=tmp_path/"synthetic.sqlite3";initialize_synthetic(path)
    return path


def activate(path, phase="acceptance", apply=True, **changes):
    values={"phase":phase,"scope_id":phase+"-20261111","authority_id":"synthetic-authority-01",
            "bindings":[binding(),binding("review-b",SECOND)],"expected_sha256":fingerprint(path),
            "expected_ledger_path":str(path.resolve()),"expected_file_identity":[path.stat().st_dev,path.stat().st_ino],
            "operator":"synthetic-operator","authorization_ref":"synthetic test only","apply":apply}
    if phase=="beta":values["acceptance_evidence"]="Synthetic acceptance passed; not a real owner observation"
    values.update(changes)
    return Authority(path).activate(**values)


def reserve(path, consumer="review-a", token=TOKEN, scope="acceptance-20261111", **changes):
    values={"key":str(uuid4()),"input_bound":32000,"output_limit":2000,"controls":CONTROLS}
    values.update(changes)
    return Authority(path).reserve(token,claims(consumer,scope),**values)


def usage(key, **changes):
    value={"id":"synthetic-response-"+key,"service_tier":"default","usage":{"input_tokens":100,"output_tokens":2}}
    value.update(changes);return value


def settle(path, receipt, scope="acceptance-20261111", payload=None):
    result=Authority(path).settle(TOKEN,claims(scope=scope),receipt["request_key"],usage(receipt["request_key"]) if payload is None else payload)
    return Authority(path).acknowledge(TOKEN,claims(scope=scope),receipt["request_key"],result["usage_sha256"])


def complete_acceptance(path):
    activate(path)
    for _ in range(2):settle(path,reserve(path))


def test_dry_run_and_exact_amendment_preserve_all_history_and_audits(ledger):
    before=ledger.read_bytes()
    with sqlite3.connect(ledger) as db:prior=rows(db)
    proposal=activate(ledger,apply=False)
    assert not proposal["applied"] and ledger.read_bytes()==before
    assert proposal["proposal"]["before_calls"]==13 and proposal["proposal"]["after_calls"]==15
    activate(ledger)
    with sqlite3.connect(ledger) as db:
        assert rows(db)==prior
        assert db.execute("SELECT * FROM allowance_amendments").fetchall()==[("synthetic-history","preserve exact audit bytes")]
        assert db.execute("SELECT limit_nano,max_calls FROM batch").fetchone()==(100_000_000,15)
        assert db.execute("SELECT count(*) FROM authority_events").fetchone()[0]==1
    with pytest.raises(HTTPException):activate(ledger)


def test_missing_ledger_never_creates_a_replacement(tmp_path):
    path=tmp_path/"missing.sqlite3"
    with pytest.raises(HTTPException):Authority(path).availability(TOKEN,claims())
    assert not path.exists()


def test_two_then_ten_requests_are_separate_lifetime_reservation_caps(ledger):
    complete_acceptance(ledger)
    state=Authority(ledger).availability(TOKEN,claims())
    assert not state["can_request"] and state["scope_count"]==2 and state["scope_reserved_nano"]==10_000_000
    with pytest.raises(HTTPException):reserve(ledger)
    activate(ledger,phase="beta")
    old=Authority(ledger).availability(TOKEN,claims())
    assert old["blocked_reason"]=="inactive_scope"
    for _ in range(10):
        receipt=reserve(ledger,scope="beta-20261111")
        settle(ledger,receipt,scope="beta-20261111")
    state=Authority(ledger).availability(TOKEN,claims(scope="beta-20261111"))
    assert state["request_count"]==25 and state["max_calls"]==25 and state["scope_count"]==10
    assert state["scope_reserved_nano"]==50_000_000 and state["limit_usd"]==0.1
    assert state["outstanding_reservations"]==0 and not state["can_request"]
    with pytest.raises(HTTPException):reserve(ledger,scope="beta-20261111")
    with pytest.raises(HTTPException):activate(ledger,phase="beta")


def test_concurrent_environment_reservation_has_one_dispatch_and_no_oversubscription(ledger):
    activate(ledger)
    def contender(index):
        try:return reserve(ledger,"review-b" if index%2 else "review-a",SECOND if index%2 else TOKEN)
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(contender,range(8)))
    assert len([r for r in results if isinstance(r,dict)])==1
    assert all(isinstance(r,dict) or r==429 for r in results)
    state=Authority(ledger).availability(TOKEN,claims())
    assert state["request_count"]==14 and state["outstanding_reservations"]==1


def test_replayed_nonce_is_observation_never_a_second_dispatch(ledger):
    activate(ledger);key=str(uuid4());first=reserve(ledger,key=key)
    again=reserve(ledger,key=key)
    assert first["dispatch_allowed"] and not again["dispatch_allowed"] and first["request_id"]==again["request_id"]
    assert not Authority(ledger).lookup(TOKEN,claims(),key)["dispatch_allowed"]
    with pytest.raises(HTTPException):reserve(ledger,key=key,input_bound=5)
    with pytest.raises(HTTPException):Authority(ledger).lookup(SECOND,claims("review-b"),key)


def test_subprocess_death_keeps_durable_hold_after_restart(ledger):
    activate(ledger);key=str(uuid4())
    code="from app.services.shared_allowance import Authority,CONTROLS; import json,sys,os; Authority(sys.argv[1]).reserve(sys.argv[2],json.loads(sys.argv[3]),sys.argv[4],32000,2000,CONTROLS); os._exit(7)"
    result=subprocess.run([sys.executable,"-c",code,str(ledger),TOKEN,json.dumps(claims()),key],timeout=20)
    assert result.returncode==7
    restarted=Authority(ledger)
    state=restarted.availability(SECOND,claims("review-b"))
    assert state["blocked_reason"]=="outstanding_usage" and state["outstanding_reservations"]==1
    assert restarted.lookup(TOKEN,claims(),key)["held_nano"]==RESERVATION
    with pytest.raises(HTTPException):reserve(ledger)


def test_process_death_during_transaction_recovers_without_partial_permit(ledger):
    activate(ledger);key=str(uuid4())
    code="""from app.services.shared_allowance import Authority,CONTROLS
import json,sys,os
a=Authority(sys.argv[1])
def crash(db,*args):
 db.execute('PRAGMA cache_size=1')
 os._exit(9)
a.audit=crash
a.reserve(sys.argv[2],json.loads(sys.argv[3]),sys.argv[4],32000,2000,CONTROLS)
"""
    result=subprocess.run([sys.executable,"-c",code,str(ledger),TOKEN,json.dumps(claims()),key],timeout=20)
    assert result.returncode==9
    from app.accounting_authority import create_app
    create_app(ledger)  # Normal owner startup lets SQLite recover its journal.
    state=Authority(ledger).availability(TOKEN,claims())
    assert state["request_count"]==13 and state["can_request"]
    assert Authority(ledger).inspect()["unresolved"]==[]


@pytest.mark.parametrize("payload", [{}, {"id":"invalid","service_tier":"default","usage":{"input_tokens":True,"output_tokens":1}},
    {"id":"invalid","service_tier":"priority","usage":{"input_tokens":10,"output_tokens":1}},
    {"id":"invalid","service_tier":"default","usage":{"input_tokens":10,"output_tokens":1,"input_tokens_details":{"cache_write_tokens_details":{"ttl_12h_tokens":1}}}}])
def test_uncertain_usage_keeps_full_hold_and_blocks_every_environment(ledger,payload):
    activate(ledger);receipt=reserve(ledger)
    with pytest.raises(HTTPException):settle(ledger,receipt,payload=payload)
    state=Authority(ledger).availability(SECOND,claims("review-b"))
    assert state["blocked_reason"]=="outstanding_usage"
    assert Authority(ledger).lookup(TOKEN,claims(),receipt["request_key"])["held_nano"]==RESERVATION


def test_overrun_is_recorded_before_shared_close_and_cannot_be_rewritten(ledger):
    activate(ledger);r=reserve(ledger)
    payload=usage(r["request_key"],usage={"input_tokens":32001,"output_tokens":2000})
    with pytest.raises(HTTPException):settle(ledger,r,payload=payload)
    state=Authority(ledger).availability(TOKEN,claims())
    assert state["blocked_reason"]=="closed"
    assert Authority(ledger).lookup(TOKEN,claims(),r["request_key"])["held_nano"]>RESERVATION
    with pytest.raises(HTTPException):settle(ledger,r)


def test_confirmed_settlement_is_idempotent_and_cannot_refund_a_call(ledger):
    activate(ledger);r=reserve(ledger)
    first=settle(ledger,r);again=settle(ledger,r)
    assert first==again and first["held_nano"]==13500
    assert Authority(ledger).availability(TOKEN,claims())["request_count"]==14
    with pytest.raises(HTTPException):settle(ledger,r,payload=usage(r["request_key"],usage={"input_tokens":0,"output_tokens":0}))


@pytest.mark.parametrize("field,value",[("environment","wrong"),("database_scope","0"*64),("consumer_id","wrong"),("scope","old-exhausted")])
def test_exact_environment_and_checkpoint_bindings(ledger,field,value):
    activate(ledger);c=claims();c[field]=value
    with pytest.raises(HTTPException) as exc:Authority(ledger).availability(TOKEN,c)
    assert exc.value.status_code==403


def test_copied_synthetic_ledger_cannot_become_another_authority(ledger,tmp_path):
    activate(ledger);fork=tmp_path/"copy-for-negative-test.sqlite3";shutil.copyfile(ledger,fork)
    with pytest.raises(HTTPException,match="copies and forks"):Authority(fork).availability(TOKEN,claims())


def test_wrong_canonical_file_is_rejected_even_before_installation(ledger,tmp_path):
    fork=tmp_path/"unactivated-negative-test.sqlite3";shutil.copyfile(ledger,fork)
    with pytest.raises(HTTPException,match="Canonical ledger"):
        activate(fork,expected_ledger_path=str(ledger),expected_file_identity=[ledger.stat().st_dev,ledger.stat().st_ino])


def test_audit_tampering_and_legacy_writes_fail_closed(ledger):
    activate(ledger)
    for write in (lambda:Budget(ledger).reserve(100,10),lambda:Budget(ledger).settle(1,{}),lambda:Budget(ledger).failed(1,"failure"),lambda:Budget(ledger).close()):
        with pytest.raises(HTTPException):write()
    with sqlite3.connect(ledger) as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE requests SET held=0 WHERE id=1")
        with pytest.raises(sqlite3.IntegrityError):db.execute("DELETE FROM authority_events")
        db.execute("UPDATE batch SET max_calls=100 WHERE id=1")
    with pytest.raises(HTTPException):Authority(ledger).availability(TOKEN,claims())


def test_insufficient_original_money_and_incomplete_acceptance_deny_activation(ledger):
    before=fingerprint(ledger)
    with pytest.raises(HTTPException):activate(ledger,expected_sha256="0"*64)
    assert fingerprint(ledger)==before
    activate(ledger)
    with pytest.raises(HTTPException):activate(ledger,phase="beta")


def test_beta_cannot_add_money_when_remaining_shared_ceiling_is_insufficient(ledger):
    with sqlite3.connect(ledger) as db:
        db.execute("UPDATE requests SET held=5000000,input_bound=32000,usage=?",(json.dumps({"input_tokens":32000,"output_tokens":2000}),))
    complete_acceptance(ledger)
    with pytest.raises(HTTPException,match="Remaining original money"):
        activate(ledger,phase="beta")
    assert Authority(ledger).availability(TOKEN,claims())["max_calls"]==15


def test_missing_acceptance_attestation_and_in_flight_work_deny_beta(ledger):
    complete_acceptance(ledger)
    before=fingerprint(ledger)
    with pytest.raises(HTTPException):activate(ledger,phase="beta",acceptance_evidence="")
    assert fingerprint(ledger)==before


def test_database_lock_failure_has_no_new_reservation(ledger):
    activate(ledger)
    with sqlite3.connect(ledger) as held:
        held.execute("BEGIN IMMEDIATE")
        with pytest.raises(HTTPException) as exc:reserve(ledger)
        assert exc.value.status_code==503
    assert Authority(ledger).availability(TOKEN,claims())["request_count"]==13


@pytest.mark.parametrize("change",[{"input_bound":32001},{"input_bound":-1},{"input_bound":True},{"output_limit":2001},{"controls":{**CONTROLS,"service_tier":"priority"}}])
def test_per_request_controls_are_not_expandable(ledger,change):
    activate(ledger)
    with pytest.raises(HTTPException):reserve(ledger,**change)
    assert Authority(ledger).availability(TOKEN,claims())["request_count"]==13


def test_database_fingerprint_pins_role_host_port_and_database_but_not_password():
    assert SCOPE==database_scope("postgresql+psycopg://review_role:rotated@postgres:5432/production_name")
    assert SCOPE!=database_scope("postgresql://review_role:unused@postgres:5432/design_aie37_qualification")
    with pytest.raises(ValueError):database_scope("sqlite://")


def test_unacknowledged_settlement_pauses_other_environment_until_explicit_receipt_recovery(ledger):
    activate(ledger);r=reserve(ledger)
    receipt=Authority(ledger).settle(TOKEN,claims(),r["request_key"],usage(r["request_key"]))
    assert receipt["status"]=="settled_unacknowledged"
    assert Authority(ledger).availability(SECOND,claims("review-b"))["blocked_reason"]=="outstanding_usage"
    inspected=Authority(ledger).inspect()
    assert inspected["unresolved"][0]["request_key"]==r["request_key"]
    with pytest.raises(HTTPException):Authority(ledger).acknowledge(TOKEN,claims(),r["request_key"],"0"*64)
    Authority(ledger).acknowledge(TOKEN,claims(),r["request_key"],receipt["usage_sha256"])
    assert Authority(ledger).availability(SECOND,claims("review-b"))["can_request"]


def test_operator_stop_is_audited_and_late_usage_cannot_reopen(ledger):
    activate(ledger);r=reserve(ledger)
    Authority(ledger).stop(scope_id=claims()["scope"],expected_sha256=fingerprint(ledger),operator="synthetic operator",authorization_ref="Synthetic failure")
    settle(ledger,r)
    assert Authority(ledger).availability(TOKEN,claims())["blocked_reason"]=="closed"
    with pytest.raises(HTTPException):activate(ledger,phase="beta")


def test_read_only_unactivated_inspection_does_not_install_any_policy(ledger):
    before=ledger.read_bytes();state=Authority(ledger).inspect()
    assert not state["active"] and state["request_count"]==13 and ledger.read_bytes()==before


def test_unreviewed_wal_mode_is_denied_without_changing_it(ledger):
    with sqlite3.connect(ledger) as db:db.execute("PRAGMA journal_mode=WAL")
    with pytest.raises(HTTPException,match="no automatic mode change"):activate(ledger)
    with sqlite3.connect(ledger) as db:assert db.execute("PRAGMA journal_mode").fetchone()[0]=="wal"


def test_unexpected_provider_content_is_not_written_to_ledger(ledger):
    activate(ledger);r=reserve(ledger)
    data=usage(r["request_key"])
    data["usage"]["unexpected_prompt"]="PRIVATE synthetic content must not be persisted"
    data["output"]="PRIVATE synthetic model output"
    settle(ledger,r,payload=data)
    with sqlite3.connect(ledger) as db:
        assert "PRIVATE" not in str(db.execute("SELECT usage FROM requests WHERE id=?",(r["request_id"],)).fetchone()[0])


def test_supported_operator_cli_defaults_to_read_only(ledger,tmp_path):
    request=tmp_path/"operator-request.json"
    values={"phase":"acceptance","scope_id":"acceptance-20261111","authority_id":"synthetic-authority-01",
        "bindings":[binding()],"expected_sha256":fingerprint(ledger),"expected_ledger_path":str(ledger.resolve()),
        "expected_file_identity":[ledger.stat().st_dev,ledger.stat().st_ino],"operator":"synthetic operator","authorization_ref":"synthetic unit test"}
    request.write_text(json.dumps(values))
    script=Path(__file__).resolve().parents[3]/"deploy/restricted-beta/amend_shared_allowance.py"
    before=ledger.read_bytes()
    result=subprocess.run([sys.executable,str(script),"--ledger",str(ledger),"--request",str(request)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)["applied"] is False and ledger.read_bytes()==before
