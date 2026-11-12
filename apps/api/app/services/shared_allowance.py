"""Single-writer authority over the EXISTING ledger; no import/copy/reset path.

Policy transitions are operator-only, exact 13->15->25, within the original
USD0.10. Clients never receive the ledger. One unresolved reservation blocks
further dispatch across environments; no timeout/expiry refunds a call or money.
"""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
import re
import secrets
import sqlite3

from fastapi import HTTPException
from sqlalchemy.engine import make_url

RESERVATION = 5_000_000
TOTAL = 100_000_000
CONTROLS = {"model":"gpt-6-luna","reasoning":"low","service_tier":"default","cache_ttl":"30m"}
FIELDS = ("id", "held", "reserved", "input_bound", "usage", "status", "response_id")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def safe_usage(value):
    """Allowlist numeric usage only; never persist unexpected provider content."""
    if not isinstance(value,dict):return None
    result={k:value[k] for k in ("input_tokens","output_tokens","total_tokens") if k in value}
    if not {"input_tokens","output_tokens"}<=result.keys() or any(type(v)is not int or v<0 for v in result.values()):return None
    for key, fields in (("input_tokens_details",("cached_tokens","cache_write_tokens")),("output_tokens_details",("reasoning_tokens",))):
        if key not in value:continue
        data=value[key]
        if not isinstance(data,dict):return None
        result[key]={k:data[k] for k in fields if k in data}
        if any(type(v)is not int or v<0 for v in result[key].values()):return None
        if key=="input_tokens_details" and "cache_write_tokens_details" in data:
            details=data["cache_write_tokens_details"]
            if not isinstance(details,dict):return None
            counters={k:details[k] for k in ("ttl_30m_tokens","ttl_12h_tokens") if k in details}
            if any(type(v)is not int or v<0 for v in counters.values()):return None
            result[key]["cache_write_tokens_details"]=counters
    return result


def database_scope(url):
    """Explicit new scope, not an exception to the legacy local DB guard."""
    u = make_url(url)
    if u.get_backend_name() != "postgresql" or not u.host or not u.database or not u.username:
        raise ValueError("Shared accounting requires a pinned PostgreSQL identity")
    return digest({"backend":"postgresql","host":u.host.lower(),"port":u.port or 5432,
                   "database":u.database,"role":u.username})


def rows(db):
    return [dict(zip(FIELDS, row)) for row in db.execute("SELECT " + ",".join(FIELDS) + " FROM requests ORDER BY id")]


def installed(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='authority_state'").fetchone())


def legacy_write_guard(db):
    if installed(db):
        raise HTTPException(503, "This ledger is managed exclusively by its shared accounting authority")


class Authority:
    def __init__(self, path):
        self.path = Path(path).resolve()

    @contextmanager
    def transaction(self, write=False):
        try:
            # mode=rw NEVER creates a missing/replacement ledger.
            with closing(sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=3)) as db:
                with db:
                    if db.execute("PRAGMA journal_mode").fetchone()[0]!="delete":
                        raise HTTPException(503,"Authority requires the original single-file rollback-journal ledger; no automatic mode change")
                    db.execute("PRAGMA synchronous=FULL")
                    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                    yield db
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, "Shared accounting unavailable or integrity invalid; no provider dispatch permitted") from exc

    def projection(self, db):
        other = {}
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            if table not in {"requests", "batch"} and not table.startswith("authority_"):
                quoted = '"' + table.replace('"', '""') + '"'
                other[table] = sorted([list(r) for r in db.execute("SELECT * FROM " + quoted)], key=canonical)
        return {"batch":list(db.execute("SELECT * FROM batch WHERE id=1").fetchone()),"requests":rows(db),
                "policy":json.loads(db.execute("SELECT value FROM authority_state WHERE id=1").fetchone()[0]),
                "mapping":[list(r) for r in db.execute("SELECT * FROM authority_requests ORDER BY request_key")],
                "historical_audits":other}

    def audit(self, db, action, actor, reference, detail):
        previous = db.execute("SELECT hash FROM authority_events ORDER BY seq DESC LIMIT 1").fetchone()
        event = {"at":datetime.now(timezone.utc).isoformat(),"action":action,"actor":actor,
                 "authorization_ref":reference,"detail":detail,"state_sha256":digest(self.projection(db))}
        parent = previous[0] if previous else "0" * 64
        value = canonical(event)
        db.execute("INSERT INTO authority_events(event,parent,hash) VALUES (?,?,?)",(value,parent,digest([parent,value])))

    def verify(self, db):
        if not installed(db):
            raise HTTPException(503, "Shared accounting policy has not been activated")
        previous, last = "0" * 64, None
        for event, parent, hashed in db.execute("SELECT event,parent,hash FROM authority_events ORDER BY seq"):
            if parent != previous or digest([parent,event]) != hashed:
                raise HTTPException(503, "Shared accounting audit integrity failed")
            previous, last = hashed, json.loads(event)
        if not last or last["state_sha256"] != digest(self.projection(db)):
            raise HTTPException(503, "Shared accounting state differs from its audit")
        policy=json.loads(db.execute("SELECT value FROM authority_state WHERE id=1").fetchone()[0])
        if (policy["ledger_path"]!=os.path.normcase(str(self.path))
                or policy["file_identity"]!=[self.path.stat().st_dev,self.path.stat().st_ino]):
            raise HTTPException(503,"This is not the authoritative ledger file; copies and forks are denied")
        if policy["protocol_version"]!=1 or policy["controls"]!=CONTROLS:
            raise HTTPException(503,"Accounting protocol/model controls differ from the audited policy")
        return policy

    def activate(self, *, phase, scope_id, authority_id, bindings, expected_sha256, expected_ledger_path, expected_file_identity, operator, authorization_ref,
                 acceptance_evidence="", apply=False):
        """Reviewed operator transition only. Dry-run is the default; no real calls.

        Beta activation additionally attests completed acceptance; failed/partial
        acceptance cannot automatically grant beta capacity or reopen a checkpoint.
        """
        for value in (scope_id, authority_id, operator, authorization_ref):
            if not isinstance(value,str) or not value.strip() or len(value)>500:
                raise ValueError("Exact scope, authority, operator and authorization required")
        if phase not in {"acceptance","beta"} or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}",scope_id):
            raise ValueError("Unsupported phase or scope identifier")
        if not isinstance(bindings,list) or not bindings:
            raise ValueError("Explicit environment bindings required")
        ids, hashes = set(), set()
        for b in bindings:
            if (set(b)!={"consumer_id","environment","database_scope","token_sha256"}
                    or not all(isinstance(v,str) and v.strip() for v in b.values())
                    or not all(re.fullmatch(r"[a-f0-9]{64}",b[k]) for k in ("database_scope","token_sha256"))
                    or b["consumer_id"] in ids or b["token_sha256"] in hashes):
                raise ValueError("Invalid or duplicate exact consumer/database/token binding")
            ids.add(b["consumer_id"]); hashes.add(b["token_sha256"])
        with self.transaction(write=apply) as db:
            if (os.path.normcase(str(self.path))!=os.path.normcase(str(Path(expected_ledger_path).resolve()))
                    or expected_file_identity!=[self.path.stat().st_dev,self.path.stat().st_ino]):
                raise HTTPException(409,"Canonical ledger path/file identity differs from the reviewed operator request")
            if not re.fullmatch(r"[a-f0-9]{64}",expected_sha256) or hashlib.sha256(self.path.read_bytes()).hexdigest()!=expected_sha256:
                raise HTTPException(409,"Ledger fingerprint changed; inspect without retrying the amendment")
            historical = rows(db)
            closed, money, maximum = db.execute("SELECT closed,limit_nano,max_calls FROM batch WHERE id=1").fetchone()
            old, new, calls, cap = (13,15,2,10_000_000) if phase=="acceptance" else (15,25,10,50_000_000)
            if closed or money != TOTAL or maximum!=old or len(historical)!=old or any(not r["usage"] or r["status"] in {"reserved","settled_unacknowledged"} for r in historical):
                raise HTTPException(409,"Expected exact exhausted, settled prior policy at unchanged USD0.10")
            if TOTAL-sum(r["held"] for r in historical)<cap:
                raise HTTPException(409,"Remaining original money cannot cover this phase")
            if phase=="acceptance":
                if installed(db): raise HTTPException(409,"Authority is already installed; no reopening")
                policy={"authority_id":authority_id,"phase":phase,"scopes":{},"original_history_sha256":digest(historical),
                        "ledger_path":os.path.normcase(str(self.path)),"file_identity":[self.path.stat().st_dev,self.path.stat().st_ino],
                        "protocol_version":1,"controls":CONTROLS}
            else:
                policy=self.verify(db)
                previous=policy["scopes"][policy["active_scope"]]
                if (policy["authority_id"]!=authority_id or policy["phase"]!="acceptance"
                        or previous["kind"]!="acceptance" or not acceptance_evidence.strip()):
                    raise HTTPException(409,"Completed acceptance and attributable pass evidence required")
                mapped=db.execute("SELECT count(*) FROM authority_requests WHERE scope=?",(policy["active_scope"],)).fetchone()[0]
                if mapped!=2: raise HTTPException(409,"Both acceptance slots must be accounted before beta activation")
                if scope_id in policy["scopes"]:raise HTTPException(409,"A historical scope cannot be reopened")
            proposal={"before_calls":old,"after_calls":new,"limit_nano":TOTAL,"scope":scope_id,
                      "max_calls":calls,"max_reserved_nano":cap,"per_request_nano":RESERVATION,"bindings":bindings}
            if not apply:return {"applied":False,"proposal":proposal}
            if phase=="acceptance":
                db.execute("CREATE TABLE authority_state(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL)")
                db.execute("CREATE TABLE authority_requests(request_key TEXT PRIMARY KEY,request_id INTEGER UNIQUE NOT NULL,scope TEXT NOT NULL,consumer TEXT NOT NULL,input_bound INTEGER NOT NULL,output_limit INTEGER NOT NULL)")
                db.execute("CREATE TABLE authority_events(seq INTEGER PRIMARY KEY,event TEXT NOT NULL,parent TEXT NOT NULL,hash TEXT NOT NULL)")
                for action in ("UPDATE","DELETE"):
                    db.execute(f"CREATE TRIGGER authority_audit_no_{action.lower()} BEFORE {action} ON authority_events BEGIN SELECT RAISE(ABORT,'immutable authority audit'); END")
                    db.execute(f"CREATE TRIGGER authority_history_no_{action.lower()} BEFORE {action} ON requests WHEN OLD.id IN (SELECT id FROM requests ORDER BY id LIMIT 13) BEGIN SELECT RAISE(ABORT,'immutable prior usage'); END")
            policy.update(phase=phase,active_scope=scope_id)
            policy["scopes"][scope_id]={"kind":phase,"baseline_count":old,"history_sha256":digest(historical),
                "max_calls":calls,"max_reserved_nano":cap,"bindings":bindings}
            db.execute("INSERT INTO authority_state(id,value) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value",(canonical(policy),))
            db.execute("UPDATE batch SET max_calls=? WHERE id=1",(new,))
            self.audit(db,"activate_"+phase,operator,authorization_ref,{**proposal,"original_ledger_sha256":expected_sha256,"acceptance_evidence":acceptance_evidence})
            return {"applied":True,"proposal":proposal}

    def binding(self, policy, token, claims):
        hashed=hashlib.sha256(token.encode()).hexdigest()
        scope=policy["scopes"].get(claims.get("scope"))
        if scope:
            for b in scope["bindings"]:
                if (secrets.compare_digest(b["token_sha256"],hashed) and all(claims.get(k)==b[k] for k in ("consumer_id","environment","database_scope"))):
                    return scope
        raise HTTPException(403,"Accounting consumer/environment/database scope denied")

    def state(self, db, policy, claims):
        scope=policy["scopes"][claims["scope"]]
        closed, money, maximum=db.execute("SELECT closed,limit_nano,max_calls FROM batch WHERE id=1").fetchone()
        history=rows(db)
        if digest(history[:scope["baseline_count"]])!=scope["history_sha256"]:
            raise HTTPException(503,"Historical checkpoint integrity failed")
        count, reserved=db.execute("SELECT count(*),coalesce(sum(r.reserved),0) FROM requests r JOIN authority_requests a ON r.id=a.request_id WHERE a.scope=?",(claims["scope"],)).fetchone()
        outstanding=sum(not r["usage"] or r["status"]=="settled_unacknowledged" for r in history)
        reason=("closed" if closed else "inactive_scope" if policy["active_scope"]!=claims["scope"]
                else "outstanding_usage" if outstanding else "call_limit" if len(history)>=maximum or count>=scope["max_calls"]
                else "scope_money_limit" if reserved+RESERVATION>scope["max_reserved_nano"]
                else "shared_money_limit" if sum(r["held"] for r in history)+RESERVATION>money else None)
        return {"protocol_version":1,"authority_id":policy["authority_id"],"scope":claims["scope"],"can_request":reason is None,
                "blocked_reason":reason,"message":"Shared allowance available" if reason is None else "AI messages paused: "+reason,
                "max_calls":maximum,"request_count":len(history),"remaining_calls":max(0,maximum-len(history)),
                "limit_usd":money/1e9,"remaining_usd":max(0,money-sum(r["held"] for r in history))/1e9,
                "outstanding_reservations":outstanding,"scope_count":count,"scope_max_calls":scope["max_calls"],
                "scope_reserved_nano":reserved,"scope_limit_nano":scope["max_reserved_nano"]}

    def availability(self, token, claims):
        with self.transaction() as db:
            policy=self.verify(db);self.binding(policy,token,claims)
            return self.state(db,policy,claims)

    def receipt(self, db, policy, claims, key, dispatch=False):
        mapped=db.execute("SELECT request_id,scope,consumer FROM authority_requests WHERE request_key=?",(key,)).fetchone()
        if not mapped or mapped[1:]!=(claims["scope"],claims["consumer_id"]):raise HTTPException(404,"Reservation not found for consumer")
        r=next(row for row in rows(db) if row["id"]==mapped[0])
        return {"protocol_version":1,"authority_id":policy["authority_id"],"scope":claims["scope"],"request_key":key,
                "request_id":r["id"],"dispatch_allowed":dispatch,"status":r["status"],"held_nano":r["held"],
                "response_id":r["response_id"],"usage_sha256":digest(json.loads(r["usage"])) if r["usage"] else None}

    def reserve(self, token, claims, key, input_bound, output_limit, controls):
        try:valid_key=str(UUID(key))==key and UUID(key).version==4
        except (ValueError,TypeError,AttributeError):valid_key=False
        if (not valid_key or type(input_bound)is not int or not 1<=input_bound<=32000
                or type(output_limit)is not int or not 1<=output_limit<=2000 or controls!=CONTROLS):
            raise HTTPException(422,"Pinned model/context/output/Standard controls required")
        with self.transaction(True) as db:
            policy=self.verify(db);self.binding(policy,token,claims)
            existing=db.execute("SELECT input_bound,output_limit FROM authority_requests WHERE request_key=?",(key,)).fetchone()
            if existing:
                if existing!=(input_bound,output_limit):raise HTTPException(409,"Reservation key conflicts with its original request")
                return self.receipt(db,policy,claims,key)  # NEVER authorize a second dispatch.
            state=self.state(db,policy,claims)
            if not state["can_request"]:raise HTTPException(429,{"code":"design_ai_allowance_paused","message":state["message"],"allowance":state})
            request=db.execute("INSERT INTO requests(held,reserved,input_bound,status) VALUES(?,?,?,'reserved')",(RESERVATION,RESERVATION,input_bound)).lastrowid
            db.execute("INSERT INTO authority_requests VALUES(?,?,?,?,?,?)",(key,request,claims["scope"],claims["consumer_id"],input_bound,output_limit))
            self.audit(db,"reserve",claims["consumer_id"],claims["scope"],{"request_key":key,"request_id":request})
            return self.receipt(db,policy,claims,key,True)

    def lookup(self, token, claims, key):
        with self.transaction() as db:
            policy=self.verify(db);self.binding(policy,token,claims)
            return self.receipt(db,policy,claims,key)

    def settle(self, token, claims, key, payload=None):
        error=False
        with self.transaction(True) as db:
            policy=self.verify(db);self.binding(policy,token,claims)
            receipt=self.receipt(db,policy,claims,key)
            usage=safe_usage(payload.get("usage")) if isinstance(payload,dict) else None
            r=next(row for row in rows(db) if row["id"]==receipt["request_id"])
            if r["usage"]:
                if not isinstance(payload,dict) or canonical(json.loads(r["usage"]))!=canonical(usage) or r["response_id"]!=payload.get("id"):
                    raise HTTPException(409,"Settled usage is immutable")
                return receipt
            bound, output=db.execute("SELECT input_bound,output_limit FROM authority_requests WHERE request_key=?",(key,)).fetchone()
            good=(isinstance(usage,dict) and all(type(usage.get(k))is int and usage[k]>=0 for k in ("input_tokens","output_tokens"))
                  and isinstance(payload.get("id"),str) and 0<len(payload["id"])<=200 and payload.get("service_tier")=="default")
            if good:
                details=usage.get("input_tokens_details") or {}
                writes=details.get("cache_write_tokens_details") or {} if isinstance(details,dict) else None
                good=isinstance(details,dict) and isinstance(writes,dict) and writes.get("ttl_12h_tokens",0)==0
            if not good:
                db.execute("UPDATE requests SET status='usage_unknown' WHERE id=?",(r["id"],))
                error=True
            else:
                cost=usage["input_tokens"]*125+usage["output_tokens"]*500
                over=usage["input_tokens"]>bound or usage["output_tokens"]>output or cost>RESERVATION
                db.execute("UPDATE requests SET held=?,usage=?,status=?,response_id=? WHERE id=?",(max(cost,RESERVATION) if over else cost,canonical(usage),"overrun" if over else "settled_unacknowledged",payload["id"],r["id"]))
                if over:db.execute("UPDATE batch SET closed=1 WHERE id=1")
                error=over
            self.audit(db,"usage_uncertain" if not good else "settle",claims["consumer_id"],claims["scope"],{"request_key":key,"request_id":r["id"],"stopped":error})
            result=self.receipt(db,policy,claims,key)
        # Commit the hold/overrun BEFORE returning the stop error.
        if error:raise HTTPException(503,"Usage uncertain or exceeded its reservation; accounting stopped without retry")
        return result

    def acknowledge(self, token, claims, key, usage_sha256):
        """A lost settlement response must keep ALL environments paused.

        Only receipt confirmation, never elapsed time, unlocks the next request.
        A lost acknowledgement response cannot lose accounting: the caller had
        already received/verified the durable usage receipt before sending it.
        """
        with self.transaction(True) as db:
            policy=self.verify(db);self.binding(policy,token,claims)
            receipt=self.receipt(db,policy,claims,key)
            if receipt["usage_sha256"]!=usage_sha256 or receipt["status"] not in {"settled_unacknowledged","settled"}:
                raise HTTPException(409,"Confirmed durable usage receipt required")
            if receipt["status"]!="settled":
                db.execute("UPDATE requests SET status='settled' WHERE id=?",(receipt["request_id"],))
                self.audit(db,"acknowledge_usage",claims["consumer_id"],claims["scope"],{"request_key":key,"usage_sha256":usage_sha256})
            return self.receipt(db,policy,claims,key)

    def inspect(self):
        with self.transaction() as db:
            if not installed(db):
                prior=rows(db)
                return {"active":False,"ledger_path":str(self.path),"file_identity":[self.path.stat().st_dev,self.path.stat().st_ino],
                        "ledger_sha256":hashlib.sha256(self.path.read_bytes()).hexdigest(),"history_sha256":digest(prior),
                        "batch":dict(zip(("closed","limit_nano","max_calls"),db.execute("SELECT closed,limit_nano,max_calls FROM batch WHERE id=1").fetchone())),
                        "request_count":len(prior),"held_nano":sum(r["held"] for r in prior),
                        "outstanding_reservations":sum(not r["usage"] for r in prior)}
            policy=self.verify(db)
            return {"authority_id":policy["authority_id"],"phase":policy["phase"],"active_scope":policy["active_scope"],
                    "history_count":13,"history_sha256":policy["original_history_sha256"],
                    "audit_head":db.execute("SELECT hash FROM authority_events ORDER BY seq DESC LIMIT 1").fetchone()[0],
                    "unresolved":[{"request_key":key,**self.receipt(db,policy,{"scope":scope,"consumer_id":consumer},key)}
                        for key,scope,consumer in db.execute("SELECT a.request_key,a.scope,a.consumer FROM authority_requests a JOIN requests r ON a.request_id=r.id WHERE r.usage IS NULL OR r.status='settled_unacknowledged'")]}

    def stop(self, *, scope_id, expected_sha256, operator, authorization_ref):
        if not operator.strip() or not authorization_ref.strip():raise ValueError("Attributable stop reason required")
        with self.transaction(True) as db:
            policy=self.verify(db)
            if scope_id!=policy["active_scope"] or hashlib.sha256(self.path.read_bytes()).hexdigest()!=expected_sha256:
                raise HTTPException(409,"Exact active scope/fingerprint required to stop")
            db.execute("UPDATE batch SET closed=1 WHERE id=1")
            self.audit(db,"stop",operator,authorization_ref,{"scope":scope_id})
            return {"closed":True,"scope":scope_id,"reopen_supported":False}
