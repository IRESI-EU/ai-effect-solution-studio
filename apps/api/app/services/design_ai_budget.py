"""Persistent, fail-closed budget for one explicitly authorized local Luna batch.

USD accounting uses integer nano-dollars. Standard rates checked 2026-10-18:
input .10, cached .01, cache writes .125, output .50 per million tokens.
Reserve at the highest input/cache-write rate; never assume a cache discount.
No request bodies, credentials or generated text are stored here.
"""
import json
from decimal import Decimal
from pathlib import Path
import sqlite3

from fastapi import HTTPException

LIMIT = 500_000_000  # $0.50
MAX_CALLS = 11
MAX_INPUT = 32000
MAX_OUTPUT = 2000  # Includes reasoning tokens.
RESERVATION = MAX_INPUT * 125 + MAX_OUTPUT * 500  # $0.005
PRICING = "https://developers.openai.com/api/docs/models/gpt-6-luna"
PAUSED_CODE = "design_ai_allowance_paused"


def allowance_state(closed, limit, max_calls, count, held, unsettled=0, outstanding=0):
    reason = "closed" if closed else "call_limit" if count >= max_calls else "insufficient_budget" if limit-held < RESERVATION else None
    explanation = {"closed": "This session is closed.", "call_limit": "This session has used its provider-call limit.",
                   "insufficient_budget": "The remaining allowance cannot cover the next maximum request cost."}
    message = ("AI testing is paused by the local test allowance. " + explanation[reason]
               + " Ask the local operator to review the allowance; retrying will not resume it.") if reason else "Local AI test allowance is available."
    return {"can_request": reason is None, "blocked_reason": reason, "message": message,
            "limit_usd": limit/1_000_000_000, "remaining_usd": max(0, limit-held)/1_000_000_000,
            "max_calls": max_calls, "request_count": count, "remaining_calls": max(0, max_calls-count),
            "next_reservation_usd": RESERVATION/1_000_000_000,
            "unsettled_holds_usd": unsettled/1_000_000_000, "outstanding_reservations": outstanding}


def initialize(path, *, limit_usd="0.50", max_calls=MAX_CALLS):
    limit = int(Decimal(str(limit_usd)) * 1_000_000_000)
    if not 0 < limit <= LIMIT or not 1 <= max_calls <= MAX_CALLS:
        raise ValueError("Acceptance allowance exceeds the supported ceiling")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never silently reset an earlier allowance.
    with path.open("xb"):
        pass
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE batch (id INTEGER PRIMARY KEY CHECK(id=1), closed INTEGER NOT NULL,
            limit_nano INTEGER NOT NULL, max_calls INTEGER NOT NULL);
        CREATE TABLE requests (id INTEGER PRIMARY KEY, held INTEGER NOT NULL,
            reserved INTEGER NOT NULL, input_bound INTEGER NOT NULL,
            usage TEXT, status TEXT NOT NULL, response_id TEXT);
        """)
        db.execute("INSERT INTO batch VALUES (1,0,?,?)", (limit, max_calls))


def limits(db):
    # Read the original ledger without migrating or rewriting it. A new batch
    # gets its own persisted allowance; configuration cannot enlarge it.
    columns = {row[1] for row in db.execute("PRAGMA table_info(batch)")}
    if {"limit_nano", "max_calls"} <= columns:
        return tuple(db.execute("SELECT limit_nano,max_calls FROM batch WHERE id=1").fetchone())
    return LIMIT, MAX_CALLS


class Budget:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise HTTPException(503, "Acceptance budget must be explicitly initialized")

    def availability(self):
        """Read-only status; never reserve a call or alter/reopen a ledger."""
        with sqlite3.connect(self.path.resolve().as_uri()+"?mode=ro", uri=True, timeout=5) as db:
            db.execute("BEGIN")
            closed = db.execute("SELECT closed FROM batch WHERE id=1").fetchone()[0]
            limit, max_calls = limits(db)
            count, held, unsettled, outstanding = db.execute("""SELECT COUNT(*), COALESCE(SUM(held),0),
                COALESCE(SUM(CASE WHEN usage IS NULL THEN held ELSE 0 END),0),
                COALESCE(SUM(CASE WHEN status='reserved' THEN 1 ELSE 0 END),0) FROM requests""").fetchone()
        return allowance_state(closed, limit, max_calls, count, held, unsettled, outstanding)

    def reserve(self, input_bound, output_limit):
        if input_bound > MAX_INPUT or not 1 <= output_limit <= MAX_OUTPUT:
            raise HTTPException(422, "Acceptance input/output reservation limit exceeded")
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            closed = db.execute("SELECT closed FROM batch WHERE id=1").fetchone()[0]
            limit, max_calls = limits(db)
            count, held = db.execute("SELECT COUNT(*), COALESCE(SUM(held),0) FROM requests").fetchone()
            state = allowance_state(closed, limit, max_calls, count, held)
            if not state["can_request"]:
                raise HTTPException(429, {"code": PAUSED_CODE, "message": state["message"], "allowance": state})
            cursor = db.execute("INSERT INTO requests(held,reserved,input_bound,status) VALUES (?,?,?,'reserved')",
                                (RESERVATION, RESERVATION, input_bound))
            return cursor.lastrowid

    def settle(self, request_id, payload):
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            self.failed(request_id, "usage_unknown")
            return
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        if type(input_tokens) is not int or type(output_tokens) is not int or min(input_tokens, output_tokens) < 0:
            self.failed(request_id, "usage_invalid")
            return
        # Conservatively charge all input at cache-write rate, including cached
        # reads. This upper estimate also covers mixed/undisclosed cache writes.
        upper_cost = input_tokens * 125 + output_tokens * 500
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET held=?, usage=?, status=?, response_id=? WHERE id=?",
                       (max(upper_cost, RESERVATION) if input_tokens > MAX_INPUT or output_tokens > MAX_OUTPUT else upper_cost,
                        json.dumps(usage), payload.get("status", "received"), payload.get("id"), request_id))
            if input_tokens > MAX_INPUT or output_tokens > MAX_OUTPUT or upper_cost > RESERVATION:
                db.execute("UPDATE batch SET closed=1 WHERE id=1")
                raise_after = True
            else:
                raise_after = False
        if raise_after:
            raise HTTPException(503, "Provider exceeded the acceptance usage bound; batch stopped")

    def failed(self, request_id, status):
        # A timeout/cancellation may still be billed: keep its full reservation.
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET status=? WHERE id=? AND usage IS NULL AND status='reserved'", (status, request_id))

    def close(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE batch SET closed=1 WHERE id=1")

    def report(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute("SELECT * FROM requests ORDER BY id")]
            closed = bool(db.execute("SELECT closed FROM batch WHERE id=1").fetchone()[0])
            limit, max_calls = limits(db)
        for row in rows:
            row["usage"] = json.loads(row["usage"]) if row["usage"] else None
        known = [row["usage"] for row in rows if row["usage"]]
        tokens = {"input_tokens": 0, "cached_input_tokens": 0, "cache_write_tokens": 0,
                  "output_tokens": 0, "reasoning_tokens": 0}
        estimated_nano = 0
        for usage in known:
            details = usage.get("input_tokens_details") or {}
            inputs, outputs = usage["input_tokens"], usage["output_tokens"]
            cached = max(0, min(inputs, details.get("cached_tokens", 0)))
            # If cache writes are undisclosed, estimate all remaining input at
            # their higher rate; the reservation never relies on this discount.
            writes = max(0, min(inputs-cached, details.get("cache_write_tokens", inputs-cached)))
            tokens["input_tokens"] += inputs
            tokens["cached_input_tokens"] += cached
            tokens["cache_write_tokens"] += writes
            tokens["output_tokens"] += outputs
            tokens["reasoning_tokens"] += (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
            estimated_nano += (inputs-cached-writes)*100 + cached*10 + writes*125 + outputs*500
        return {"limit_usd": limit / 1_000_000_000, "max_calls": max_calls, "model": "gpt-6-luna", "reasoning_effort": "low", "service_tier": "default",
                "pricing_source": PRICING, "closed": closed, "requests": rows,
                "token_usage": tokens, "usage_unknown_requests": len(rows)-len(known),
                "estimated_usage_cost_usd": estimated_nano / 1_000_000_000,
                "accounted_upper_cost_usd": sum(row["held"] for row in rows) / 1_000_000_000}
