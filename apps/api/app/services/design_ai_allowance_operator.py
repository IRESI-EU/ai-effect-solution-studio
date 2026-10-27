"""Local, audited two-slot extension. No monetary amendments or reopening operation."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone

SCHEMA = """CREATE TABLE IF NOT EXISTS allowance_amendments (
    amendment_id TEXT PRIMARY KEY, request_json TEXT NOT NULL, audit_json TEXT NOT NULL,
    scope_path TEXT NOT NULL, scope_sha256 TEXT NOT NULL, ledger_path TEXT NOT NULL)"""


def identity(path):
    return os.path.normcase(str(Path(path).resolve()))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def has_amendments(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='allowance_amendments'").fetchone())


def scope_allowed(db, ledger, task):
    """The additional slots belong only to the immutable checkpoint in the audit."""
    if not has_amendments(db):
        return True
    row = db.execute("SELECT scope_path,scope_sha256,ledger_path FROM allowance_amendments ORDER BY rowid DESC LIMIT 1").fetchone()
    if row is None:
        return True
    try:
        return (row[2] == identity(ledger) and bool(task) and row[0] == identity(task)
                and row[1] == digest(Path(task).read_bytes()))
    except OSError:
        return False


def amend_calls(path, *, expected_ledger_sha256, expected_limit, new_limit, amendment_id,
                operator, reason, authorization_ref, task_limit_file, dry_run=True):
    from app.services.design_ai_budget import Budget, RESERVATION
    path, task = Path(path).resolve(), Path(task_limit_file).resolve()
    if not path.is_file() or not task.is_file() or path == task:
        raise ValueError("Exact existing ledger and checkpoint files are required")
    if (type(expected_limit), type(new_limit)) != (int, int) or (expected_limit, new_limit) != (10, 12):
        raise ValueError("This narrow operator operation supports only 10 to 12 calls")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", amendment_id):
        raise ValueError("A unique amendment identifier is required")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_ledger_sha256):
        raise ValueError("The expected ledger fingerprint is required")
    for value in (operator, reason, authorization_ref):
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError("Operator, reason and authorization reference are required")
    task_bytes = task.read_bytes()
    request = dict(ledger=identity(path), expected_ledger_sha256=expected_ledger_sha256,
        expected_limit=expected_limit, new_limit=new_limit, amendment_id=amendment_id,
        operator=operator, reason=reason, authorization_ref=authorization_ref,
        task_checkpoint=identity(task), task_sha256=digest(task_bytes))
    request_json = json.dumps(request, sort_keys=True)
    mode = "ro" if dry_run else "rw"  # Never creates a replacement ledger.
    with sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=10) as db:
        db.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
        if has_amendments(db):
            prior = db.execute("SELECT request_json,audit_json FROM allowance_amendments WHERE amendment_id=?", (amendment_id,)).fetchone()
            if prior:
                if prior[0] != request_json:
                    raise ValueError("Amendment identifier conflicts with its recorded request")
                return {"applied": False, "replayed": True, "audit": json.loads(prior[1])}
            if db.execute("SELECT 1 FROM allowance_amendments LIMIT 1").fetchone():
                raise ValueError("This ledger already has its one-time amendment")
        if digest(path.read_bytes()) != expected_ledger_sha256:
            raise ValueError("Ledger fingerprint mismatch; inspect the exact target and current state")
        columns = {row[1] for row in db.execute("PRAGMA table_info(batch)")}
        if not {"limit_nano", "max_calls", "closed"} <= columns:
            raise ValueError("Legacy implicit policy cannot be amended")
        closed, money, calls = db.execute("SELECT closed,limit_nano,max_calls FROM batch WHERE id=1").fetchone()
        rows = [dict(zip(("id", "held", "reserved", "input_bound", "usage", "status", "response_id"), row))
                for row in db.execute("SELECT id,held,reserved,input_bound,usage,status,response_id FROM requests ORDER BY id")]
        if closed or calls != expected_limit or len(rows) != expected_limit or money != 100_000_000:
            raise ValueError("Expected an open, call-exhausted 10-call / USD0.10 policy")
        if any(row["usage"] is None or row["status"] == "reserved" for row in rows):
            raise ValueError("Outstanding or unknown-usage reservations prevent amendment")
        if money - sum(row["held"] for row in rows) < 2 * RESERVATION:
            raise ValueError("Shared monetary allowance cannot cover both cases")
        policy = json.loads(task_bytes)
        state = Budget(path, task_limit_file=task).task_availability(db)
        if (policy["baseline_count"] != len(rows) or policy["max_calls"] != 2
                or policy["max_reserved_nano"] != 2 * RESERVATION or not state["can_request"]
                or state["request_count"] != 0):
            raise ValueError("The unchanged, unused two-request / USD0.01 checkpoint is required")
        before = {"closed": closed, "limit_nano": money, "max_calls": calls}
        after = {**before, "max_calls": new_limit}
        audit = {"request": request, "before": before, "after": after,
            "used_calls": len(rows), "held_nano": sum(row["held"] for row in rows),
            "usage_records_sha256": digest(json.dumps(rows, sort_keys=True).encode()),
            "applied_at": None if dry_run else datetime.now(timezone.utc).isoformat()}
        if not dry_run:
            if task.read_bytes() != task_bytes:
                raise ValueError("Task checkpoint changed during amendment")
            db.execute(SCHEMA)
            db.execute("UPDATE batch SET max_calls=? WHERE id=1 AND max_calls=? AND closed=0", (new_limit, expected_limit))
            db.execute("INSERT INTO allowance_amendments VALUES (?,?,?,?,?,?)", (amendment_id, request_json,
                json.dumps(audit, sort_keys=True), identity(task), digest(task_bytes), identity(path)))
        return {"applied": not dry_run, "replayed": False, "audit": audit}
