"""Disposable ledgers only. Never reads or mutates the live allowance."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3

from fastapi import HTTPException
import pytest

from app.services.design_ai_budget import Budget, initialize
from app.services.design_ai_allowance_operator import amend_calls, SCHEMA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("SELECT id,held,reserved,input_bound,usage,status,response_id FROM requests ORDER BY id")]


@pytest.fixture
def prepared(tmp_path):
    path, task = tmp_path / "shared.sqlite3", tmp_path / "task.json"
    initialize(path, limit_usd=".10", max_calls=10)
    for _ in range(10):
        request = Budget(path).reserve(16000, 2000)
        Budget(path).settle(request, {"status": "completed", "usage": {"input_tokens": 100, "output_tokens": 100}})
    task.write_text(json.dumps({"ledger": path.name, "baseline_count": 10,
        "baseline_sha256": hashlib.sha256(json.dumps(rows(path), sort_keys=True).encode()).hexdigest(),
        "max_calls": 2, "max_reserved_nano": 10_000_000}))
    args = dict(path=path, expected_ledger_sha256=sha(path), expected_limit=10, new_limit=12,
        amendment_id="authorized-two", operator="unit operator", reason="two unit cases",
        authorization_ref="unit-only-authorization", task_limit_file=task)
    return path, task, args


def test_preview_atomic_extension_and_replay_preserve_accounting(prepared):
    path, task, args = prepared
    original, task_bytes, before_rows = path.read_bytes(), task.read_bytes(), rows(path)
    preview = amend_calls(**args)
    assert not preview["applied"] and preview["audit"]["before"]["max_calls"] == 10
    assert path.read_bytes() == original
    applied = amend_calls(**args, dry_run=False)
    assert applied["applied"] and applied["audit"]["after"] == {"max_calls": 12, "limit_nano": 100_000_000, "closed": 0}
    assert rows(path) == before_rows and task.read_bytes() == task_bytes
    with sqlite3.connect(path) as db:
        audit = json.loads(db.execute("SELECT audit_json FROM allowance_amendments").fetchone()[0])
    assert audit == applied["audit"]
    state = Budget(path, task_limit_file=task).availability()
    assert state["can_request"] and state["request_count"] == 10 and state["remaining_calls"] == 2
    after = path.read_bytes()
    assert amend_calls(**args, dry_run=False)["replayed"]
    assert path.read_bytes() == after


@pytest.mark.parametrize("change", ["hash", "expected", "wrong_ledger", "empty_operator", "larger", "closed", "outstanding"])
def test_rejected_target_or_precondition_leaves_policy_unchanged(prepared, tmp_path, change):
    path, task, args = prepared
    if change == "hash": args["expected_ledger_sha256"] = "0" * 64
    elif change == "expected": args["expected_limit"] = 9
    elif change == "larger": args["new_limit"] = 13
    elif change == "empty_operator": args["operator"] = ""
    elif change == "wrong_ledger":
        other = tmp_path / "other.sqlite3"
        initialize(other, limit_usd=".10", max_calls=10)
        args["path"] = other
    elif change == "closed":
        Budget(path).close(); args["expected_ledger_sha256"] = sha(path)
    else:
        with sqlite3.connect(path) as db: db.execute("UPDATE requests SET usage=NULL,status='reserved' WHERE id=10")
        args["expected_ledger_sha256"] = sha(path)
    before = args["path"].read_bytes()
    with pytest.raises((ValueError, HTTPException)): amend_calls(**args, dry_run=False)
    assert args["path"].read_bytes() == before


def test_conflicting_and_concurrent_amendments_cannot_overwrite(prepared):
    path, task, args = prepared
    def apply(identifier):
        try: return amend_calls(**{**args, "amendment_id": identifier}, dry_run=False)["applied"]
        except ValueError: return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(apply, ["one", "two"])).count(True) == 1
    with sqlite3.connect(path) as db:
        identifier = db.execute("SELECT amendment_id FROM allowance_amendments").fetchone()[0]
        assert db.execute("SELECT max_calls FROM batch").fetchone()[0] == 12
        assert db.execute("SELECT COUNT(*) FROM allowance_amendments").fetchone()[0] == 1
    with pytest.raises(ValueError): amend_calls(**{**args, "amendment_id": identifier, "reason": "conflicting reason"}, dry_run=False)


def test_audit_persistence_failure_rolls_back_policy(prepared):
    path, task, args = prepared
    with sqlite3.connect(path) as db:
        db.execute(SCHEMA)
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON allowance_amendments BEGIN SELECT RAISE(ABORT,'simulated audit failure'); END")
    args["expected_ledger_sha256"] = sha(path)
    before = rows(path)
    with pytest.raises(sqlite3.IntegrityError): amend_calls(**args, dry_run=False)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT max_calls FROM batch").fetchone()[0] == 10
        assert db.execute("SELECT COUNT(*) FROM allowance_amendments").fetchone()[0] == 0
    assert rows(path) == before


def test_only_scoped_task_uses_slots_then_shared_and_task_pause(prepared, tmp_path):
    path, task, args = prepared
    amend_calls(**args, dry_run=False)
    assert Budget(path).availability()["blocked_reason"] == "amendment_scope"
    other = tmp_path / "other-task.json"; other.write_bytes(task.read_bytes())
    assert Budget(path, task_limit_file=other).availability()["blocked_reason"] == "amendment_scope"
    with pytest.raises(HTTPException): Budget(path).reserve(16000, 2000)
    budget = Budget(path, task_limit_file=task)
    for _ in range(2):
        request = budget.reserve(16000, 2000)
        budget.settle(request, {"status": "completed", "usage": {"input_tokens": 1, "output_tokens": 1}})
    assert budget.availability()["blocked_reason"] == "task_limit"
    assert Budget(path).availability()["blocked_reason"] == "call_limit"
    with pytest.raises(HTTPException): budget.reserve(16000, 2000)
    assert len(rows(path)) == 12


def test_monetary_and_checkpoint_integrity_guards_survive(prepared):
    path, task, args = prepared
    amend_calls(**args, dry_run=False)
    with sqlite3.connect(path) as db: db.execute("UPDATE batch SET limit_nano=(SELECT SUM(held) FROM requests)")
    assert Budget(path, task_limit_file=task).availability()["blocked_reason"] == "insufficient_budget"
    with pytest.raises(HTTPException): Budget(path, task_limit_file=task).reserve(16000, 2000)
    with sqlite3.connect(path) as db: db.execute("UPDATE batch SET limit_nano=100000000")
    # Immutable checkpoint tampering fails closed, even if it looks like a fresh task.
    policy = json.loads(task.read_text()); policy["max_calls"] = 3; task.write_text(json.dumps(policy))
    assert not Budget(path, task_limit_file=task).availability()["can_request"]
