"""Dated review-budget tests use synthetic ledgers and HTTP doubles only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sqlite3
import sys
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app.accounting_authority import create_app
from app.core.config import settings
from app.services import shared_allowance as shared
from app.services.allowance_client import Client
from app.services.shared_allowance import Authority, CONTROLS, REVIEW_SCOPE
from test_shared_allowance import ledger, fingerprint, usage, TOKEN, claims  # noqa: F401
from test_portuguese_acceptance_allocation import exhausted_beta, proposed, CLAIMS, BINDING

REVIEW_TOKEN="synthetic-project-review-token-not-a-secret-0003"
REVIEW_BINDING={**BINDING,"consumer_id":"pt-project-review-demo",
                "token_sha256":hashlib.sha256(REVIEW_TOKEN.encode()).hexdigest()}
REVIEW_CLAIMS={k:v for k,v in REVIEW_BINDING.items() if k!="token_sha256"} | {"scope":REVIEW_SCOPE}


@pytest.fixture
def closed_checkpoint(ledger,monkeypatch):
    monkeypatch.setattr(shared,"utc_now",lambda:datetime.fromisoformat("2026-11-17T12:00:00+00:00"))
    close_portuguese_checkpoint(ledger)
    return ledger


def close_portuguese_checkpoint(ledger):
    exhausted_beta(ledger);proposed(ledger)
    authority=Authority(ledger)
    for _ in range(3):
        key=str(uuid4());authority.reserve(TOKEN,CLAIMS,key,32000,2000,CONTROLS)
        result=authority.settle(TOKEN,CLAIMS,key,usage(key))
        authority.acknowledge(TOKEN,CLAIMS,key,result["usage_sha256"])
    authority.stop(scope_id=CLAIMS["scope"],expected_sha256=fingerprint(ledger),
                   operator="synthetic",authorization_ref="synthetic checkpoint closure")


def request(path,**changes):
    return {"authority_id":"synthetic-authority-01","bindings":[deepcopy(REVIEW_BINDING)],
            "expected_sha256":fingerprint(path),"expected_ledger_path":str(path.resolve()),
            "expected_file_identity":[path.stat().st_dev,path.stat().st_ino],
            "operator":"synthetic-operator","authorization_ref":"synthetic new review approval only",
            "proposal_sha256":"c"*64,**changes}


def reserve(path,key=None):
    return Authority(path).reserve(REVIEW_TOKEN,REVIEW_CLAIMS,key or str(uuid4()),32000,2000,CONTROLS)


def settle(path,key,payload=None):
    authority=Authority(path)
    receipt=authority.settle(REVIEW_TOKEN,REVIEW_CLAIMS,key,usage(key) if payload is None else payload)
    return authority.acknowledge(REVIEW_TOKEN,REVIEW_CLAIMS,key,receipt["usage_sha256"])


def test_dry_run_then_ten_calls_preserve_closed_batch_history_scopes_and_audits(closed_checkpoint):
    path=closed_checkpoint;authority=Authority(path);before=path.read_bytes()
    with authority.transaction() as db:
        old=authority.projection(db);events=db.execute("SELECT * FROM authority_events").fetchall()
    dry=authority.activate_review_demo(**request(path))
    assert not dry["applied"] and path.read_bytes()==before
    assert dry["proposal"]["historical_batch"]==[1,100_000_000,28]
    assert dry["proposal"]["max_calls"]==10 and dry["proposal"]["max_reserved_nano"]==50_000_000
    authority.activate_review_demo(**request(path),apply=True)
    assert authority.availability(TOKEN,CLAIMS)["blocked_reason"]=="closed"
    assert authority.availability(TOKEN,claims())["blocked_reason"]=="closed"
    for index in range(10):
        receipt=reserve(path);settle(path,receipt["request_key"])
        assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["scope_count"]==index+1
    state=authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)
    assert state["blocked_reason"]=="call_limit" and state["outstanding_reservations"]==0
    assert state["scope_reserved_nano"]==50_000_000 and state["remaining_usd"]==0
    assert state["request_count"]==state["max_calls"]==10 and state["historical_request_count"]==28
    assert state["historical_batch_closed"] and state["limit_usd"]==0.05
    assert state["aggregate_limit_usd"]==0.10
    with pytest.raises(HTTPException):reserve(path)
    with authority.transaction() as db:
        after=authority.projection(db)
        assert after["batch"]==old["batch"] and after["requests"][:28]==old["requests"]
        assert after["historical_audits"]==old["historical_audits"]
        for scope,value in old["policy"]["scopes"].items():assert after["policy"]["scopes"][scope]==value
        assert db.execute("SELECT * FROM authority_events ORDER BY seq LIMIT ?",(len(events),)).fetchall()==events
    before=path.read_bytes()
    with pytest.raises(HTTPException):authority.activate_review_demo(**request(path),apply=True)
    with pytest.raises(HTTPException):proposed(path)
    assert path.read_bytes()==before


@pytest.mark.parametrize("change",[
    {"authority_id":"another-authority"},{"operator":""},{"authorization_ref":""},
    {"proposal_sha256":"not-a-hash"},{"expected_sha256":"0"*64},
    {"expected_file_identity":[0,0]},{"expected_ledger_path":"/not-the-original-ledger"},
    {"bindings":[BINDING]}, {"bindings":[REVIEW_BINDING,REVIEW_BINDING]},
    {"bindings":[{**REVIEW_BINDING,"environment":"production"}]},
    {"bindings":[{**REVIEW_BINDING,"database_scope":"0"*64}]},
    {"bindings":[{**REVIEW_BINDING,"token_sha256":BINDING["token_sha256"]}]},
])
def test_wrong_activation_request_never_writes(closed_checkpoint,change):
    path=closed_checkpoint;before=path.read_bytes()
    with pytest.raises((HTTPException,ValueError)):Authority(path).activate_review_demo(**request(path,**change),apply=True)
    assert path.read_bytes()==before


def test_missing_file_copy_and_incomplete_checkpoint_cannot_activate(ledger,closed_checkpoint,tmp_path):
    source=closed_checkpoint;copied=tmp_path/"copy.sqlite3";shutil.copyfile(source,copied)
    before=copied.read_bytes()
    with pytest.raises(HTTPException):Authority(copied).activate_review_demo(**request(copied),apply=True)
    assert copied.read_bytes()==before
    missing=tmp_path/"missing.sqlite3"
    with pytest.raises(HTTPException):Authority(missing).activate_review_demo(**request(source),apply=True)
    assert not missing.exists()
    # A pristine thirteen-call ledger is not the required closed checkpoint.
    from test_shared_allowance import initialize_synthetic
    early=tmp_path/"early.sqlite3";initialize_synthetic(early);before=early.read_bytes()
    with pytest.raises(HTTPException):Authority(early).activate_review_demo(**request(early),apply=True)
    assert early.read_bytes()==before


@pytest.mark.parametrize("token,changes",[(TOKEN,{}),(REVIEW_TOKEN,{"environment":"production"}),
    (REVIEW_TOKEN,{"database_scope":"0"*64}),(REVIEW_TOKEN,{"consumer_id":"review-a"}),
    (REVIEW_TOKEN,{"scope":CLAIMS["scope"]})])
def test_no_historical_token_other_database_or_consumer_can_use_review_budget(closed_checkpoint,token,changes):
    path=closed_checkpoint;Authority(path).activate_review_demo(**request(path),apply=True)
    before=path.read_bytes()
    with pytest.raises(HTTPException):Authority(path).reserve(token,{**REVIEW_CLAIMS,**changes},str(uuid4()),32000,2000,CONTROLS)
    assert path.read_bytes()==before


def test_one_dispatch_replay_and_unacknowledged_receipt_block_competing_calls(closed_checkpoint):
    path=closed_checkpoint;authority=Authority(path);authority.activate_review_demo(**request(path),apply=True)
    def contender(_):
        try:return reserve(path)
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(contender,range(6)))
    receipts=[r for r in results if isinstance(r,dict)];assert len(receipts)==1
    key=receipts[0]["request_key"]
    assert not reserve(path,key)["dispatch_allowed"]
    receipt=authority.settle(REVIEW_TOKEN,REVIEW_CLAIMS,key,usage(key))
    assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["blocked_reason"]=="outstanding_usage"
    with pytest.raises(HTTPException):reserve(path)
    authority.acknowledge(REVIEW_TOKEN,REVIEW_CLAIMS,key,receipt["usage_sha256"])
    assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["can_request"]


@pytest.mark.parametrize("payload",[None,{"id":"synthetic-overrun","service_tier":"default",
    "usage":{"input_tokens":32001,"output_tokens":2000}}])
def test_uncertain_usage_and_overrun_latch_review_closed_without_touching_old_batch(closed_checkpoint,payload):
    path=closed_checkpoint;authority=Authority(path);authority.activate_review_demo(**request(path),apply=True)
    key=reserve(path)["request_key"]
    with pytest.raises(HTTPException):authority.settle(REVIEW_TOKEN,REVIEW_CLAIMS,key,payload)
    state=authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)
    assert state["blocked_reason"]=="closed" and state["scope_reserved_nano"]==5_000_000
    with sqlite3.connect(path) as db:assert db.execute("SELECT closed,limit_nano,max_calls FROM batch").fetchone()==(1,100_000_000,28)
    if payload is None:
        settle(path,key)  # Genuine receipt reconciliation cannot reopen this dated session.
        assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["blocked_reason"]=="closed"
    with pytest.raises(HTTPException):reserve(path)


def test_expiry_blocks_new_dispatch_but_allows_accounting_then_stop_without_reopening(closed_checkpoint,monkeypatch):
    path=closed_checkpoint;authority=Authority(path);values=request(path)
    authority.activate_review_demo(**values,apply=True);key=reserve(path)["request_key"]
    monkeypatch.setattr(shared,"utc_now",lambda:datetime.fromisoformat(shared.REVIEW_EXPIRES))
    assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["blocked_reason"]=="expired"
    with pytest.raises(HTTPException):reserve(path)
    settle(path,key)
    authority.stop(scope_id=REVIEW_SCOPE,expected_sha256=fingerprint(path),operator="synthetic",authorization_ref="synthetic review complete")
    assert authority.availability(REVIEW_TOKEN,REVIEW_CLAIMS)["blocked_reason"]=="closed"
    with pytest.raises(HTTPException):authority.activate_review_demo(**request(path),apply=True)


def test_already_expired_proposal_never_writes(closed_checkpoint,monkeypatch):
    path=closed_checkpoint;before=path.read_bytes()
    monkeypatch.setattr(shared,"utc_now",lambda:datetime.fromisoformat(shared.REVIEW_EXPIRES))
    with pytest.raises(HTTPException):Authority(path).activate_review_demo(**request(path),apply=True)
    assert path.read_bytes()==before


def test_new_review_cap_cannot_increase_original_aggregate_money_ceiling(ledger,monkeypatch):
    monkeypatch.setattr(shared,"utc_now",lambda:datetime.fromisoformat("2026-11-17T12:00:00+00:00"))
    # Seed higher genuine-history charges before installing the synthetic authority.
    with sqlite3.connect(ledger) as db:db.execute("UPDATE requests SET held=3840000")
    close_portuguese_checkpoint(ledger);before=ledger.read_bytes()
    with pytest.raises(HTTPException,match="USD0.10"):
        Authority(ledger).activate_review_demo(**request(ledger),apply=True)
    assert ledger.read_bytes()==before


def test_existing_api_client_can_use_new_budget_without_protocol_or_api_changes(closed_checkpoint,monkeypatch):
    path=closed_checkpoint;Authority(path).activate_review_demo(**request(path),apply=True)
    values={"database_url":"postgresql://review_role:unused@postgres:5432/production_name",
        "design_ai_restricted_beta":True,"design_ai_reviewer_ids":"named-existing-reviewer-id",
        "design_ai_budget_authority_url":"http://127.0.0.1:1","design_ai_budget_authority_socket":"",
        "design_ai_budget_authority_ca_file":"","design_ai_budget_authority_token":REVIEW_TOKEN,
        "design_ai_budget_authority_id":"synthetic-authority-01","design_ai_budget_scope":REVIEW_SCOPE,
        "design_ai_budget_consumer":"pt-project-review-demo","design_ai_budget_environment":"portuguese-sandbox-local",
        "design_ai_acceptance_budget_file":"","design_ai_acceptance_task_limit_file":""}
    for k,v in values.items():monkeypatch.setattr(settings,k,v)
    with TestClient(create_app(path)) as server:
        def handle(req):
            response=server.post(req.url.path,json=json.loads(req.content),headers={"Authorization":req.headers["Authorization"]})
            return httpx.Response(response.status_code,json=response.json())
        client=Client(settings,transport=httpx.MockTransport(handle))
        assert client.availability()["can_request"]
        key=client.reserve(100,2000);client.settle(key,usage(key))
        state=client.availability();assert state["scope_count"]==1 and state["outstanding_reservations"]==0
        assert state["historical_batch_closed"] and state["can_request"]
        assert server.post("/v1/activate-review",json={}).status_code==404


def test_cli_review_request_defaults_to_byte_identical_dry_run(closed_checkpoint,tmp_path,monkeypatch,capsys):
    path=closed_checkpoint;before=path.read_bytes();source=Path(__file__).resolve().parents[3]
    request_file=tmp_path/"synthetic-review.json";request_file.write_text(json.dumps(request(path)))
    script=source/"deploy/restricted-beta/amend_shared_allowance.py"
    monkeypatch.setattr(sys,"argv",[str(script),"--ledger",str(path),"--review-request",str(request_file)])
    runpy.run_path(str(script),run_name="__main__")
    assert json.loads(capsys.readouterr().out)["applied"] is False and path.read_bytes()==before
