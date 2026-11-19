"""Fresh, explicitly authorised normal-solution acceptance; never an old grant.

No initializer is called by the app. All accounting is local, durable, exclusive
and before dispatch. This module contains no API key or provider request code.
"""
from contextlib import contextmanager, closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3

from fastapi import HTTPException
from sqlalchemy.engine import make_url

MODEL = 'gpt-5.4-mini-2026-03-17'
MAX_INPUT = 64_000
MAX_OUTPUT = 3_000
MAX_REQUESTS = 6
LIMIT_NANO = 450_000_000  # USD 0.45, proposed; separate approval required.
# Standard USD .75/4.50 MTok, checked 2026-11-18. Include 10% uplift headroom,
# do not assume cache discounts. Six maximum reservations = USD .4059.
INPUT_NANO = 825
OUTPUT_NANO = 4950
RESERVATION = MAX_INPUT * INPUT_NANO + MAX_OUTPUT * OUTPUT_NANO


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()


def binding(settings, user_id, solution_id):
    url=make_url(settings.database_url)
    if url.get_backend_name()=='sqlite': database=str(Path(url.database).resolve())
    elif url.get_backend_name()=='postgresql' and url.host in {'127.0.0.1','localhost','::1'}:
        database=canonical({'host':url.host,'port':url.port or 5432,'name':url.database,'role':url.username})
    else: raise HTTPException(503,'Normal acceptance requires an explicit local development database')
    return {'database_sha256':digest(database),'user_id':user_id,'solution_id':solution_id}


def lower_limits(max_requests, limit_nano):
    return (type(max_requests) is int and 1 <= max_requests <= MAX_REQUESTS
            and type(limit_nano) is int and RESERVATION <= limit_nano <= LIMIT_NANO)


def initialize(path, *, approved_binding, authorization_ref, expires_at, max_requests=MAX_REQUESTS, limit_nano=LIMIT_NANO):
    """Operator-only AFTER separate approval; exclusive creation, no reopen/reset."""
    if not lower_limits(max_requests, limit_nano): raise ValueError('New scoped limits may only lower the existing maximums')
    if not authorization_ref.strip() or set(approved_binding)!={'database_sha256','user_id','solution_id'} or not all(approved_binding.values()):
        raise ValueError('A concrete approval reference and exact account/solution/database scope are required')
    expiry=datetime.fromisoformat(expires_at)
    now=datetime.now(timezone.utc)
    if expiry.tzinfo is None or not now<expiry<=now+timedelta(hours=24):raise ValueError('Expiry must be within 24 hours of separate approval')
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb'):pass
    policy={'version':1,'path':str(path),'file_identity':[path.stat().st_dev,path.stat().st_ino],
        'binding':approved_binding,'authorization_ref':authorization_ref,'expires_at':expires_at,
        'model':MODEL,'reasoning':'none','tier':'default','input_limit':MAX_INPUT,'output_limit':MAX_OUTPUT,
        'max_requests':max_requests,'limit_nano':limit_nano,'reservation_nano':RESERVATION}
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE acceptance_policy (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL, hash TEXT NOT NULL, closed INTEGER NOT NULL);'
            'CREATE TABLE acceptance_requests (id INTEGER PRIMARY KEY, reserved INTEGER NOT NULL, held INTEGER NOT NULL, input_bound INTEGER NOT NULL, state TEXT NOT NULL, usage TEXT, response_id TEXT);')
        db.execute('INSERT INTO acceptance_policy VALUES (1,?,?,0)',(canonical(policy),digest(policy)))


class Budget:
    def __init__(self,path):self.path=Path(path).resolve()

    @contextmanager
    def transaction(self,write=False):
        try:
            with closing(sqlite3.connect(self.path.as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True,timeout=3)) as db:
                with db:
                    db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
                    yield db
        except (sqlite3.Error,OSError,ValueError,KeyError,TypeError) as exc:
            raise HTTPException(503,'Scoped acceptance accounting unavailable or invalid; no dispatch or fallback') from exc

    def policy(self,db):
        raw,hashed,closed=db.execute('SELECT value,hash,closed FROM acceptance_policy WHERE id=1').fetchone()
        value=json.loads(raw)
        if (digest(value)!=hashed or value['path']!=str(self.path) or value['file_identity']!=[self.path.stat().st_dev,self.path.stat().st_ino]
            or value['version']!=1 or value['model']!=MODEL or value['reasoning']!='none' or value['tier']!='default'
            or not lower_limits(value['max_requests'],value['limit_nano'])
            or (value['input_limit'],value['output_limit'],value['reservation_nano'])!=(MAX_INPUT,MAX_OUTPUT,RESERVATION)):
            raise HTTPException(503,'Scoped acceptance identity or immutable controls differ')
        return value,closed

    def state(self,db):
        policy,closed=self.policy(db)
        count,reserved,held,unresolved=db.execute("SELECT COUNT(*),COALESCE(SUM(reserved),0),COALESCE(SUM(held),0),SUM(CASE WHEN usage IS NULL THEN 1 ELSE 0 END) FROM acceptance_requests").fetchone()
        reason=('closed' if closed else 'expired' if datetime.fromisoformat(policy['expires_at'])<=datetime.now(timezone.utc)
            else 'unresolved_request' if unresolved else 'request_limit' if count>=policy['max_requests']
            else 'budget_limit' if max(reserved,held)+RESERVATION>policy['limit_nano'] else None)
        return {'can_request':reason is None,'blocked_reason':reason,'request_count':count,
            'max_calls':policy['max_requests'],'remaining_calls':max(0,policy['max_requests']-count),
            'limit_usd':policy['limit_nano']/1e9,'lifetime_reserved_usd':reserved/1e9,'next_reservation_usd':RESERVATION/1e9,
            'message':'Scoped acceptance available.' if reason is None else 'Scoped acceptance paused: '+reason+'. No retry or fallback is authorised.'}

    def availability(self):
        with self.transaction() as db:return self.state(db)

    def reserve(self,input_bound,output_limit,*,request_binding):
        if type(input_bound)is not int or not 0<input_bound<=MAX_INPUT or output_limit!=MAX_OUTPUT:
            raise HTTPException(422,'Scoped acceptance input/output bound exceeded before dispatch')
        with self.transaction(True) as db:
            policy,_=self.policy(db)
            if request_binding!=policy['binding']:raise HTTPException(403,'Scoped acceptance account/solution/database binding differs')
            state=self.state(db)
            if not state['can_request']:raise HTTPException(429,state)
            return db.execute("INSERT INTO acceptance_requests(reserved,held,input_bound,state) VALUES (?,?,?,'reserved')",(RESERVATION,RESERVATION,input_bound)).lastrowid

    def settle(self,identity,payload):
        usage=payload.get('usage')
        valid=isinstance(usage,dict) and all(type(usage.get(k))is int and usage[k]>=0 for k in ('input_tokens','output_tokens'))
        if not valid:self.failed(identity,'usage_unknown');raise HTTPException(503,'Unknown usage; acceptance stopped without retry')
        counters={k:usage[k] for k in ('input_tokens','output_tokens')}
        cost=counters['input_tokens']*INPUT_NANO+counters['output_tokens']*OUTPUT_NANO
        overflow=counters['input_tokens']>MAX_INPUT or counters['output_tokens']>MAX_OUTPUT or payload.get('model')!=MODEL or payload.get('service_tier') not in (None,'default')
        with self.transaction(True) as db:
            self.policy(db)
            row=db.execute('SELECT state,input_bound FROM acceptance_requests WHERE id=?',(identity,)).fetchone()
            if not row or row[0]!='reserved':raise HTTPException(409,'Reservation already settled or stopped')
            overflow=overflow or counters['input_tokens']>row[1]
            response_id=payload.get('id')
            db.execute('UPDATE acceptance_requests SET held=?,state=?,usage=?,response_id=? WHERE id=?',
                (max(cost,RESERVATION) if overflow else cost,'usage_overrun' if overflow else 'settled',canonical(counters),str(response_id)[:200],identity))
            if overflow:db.execute('UPDATE acceptance_policy SET closed=1 WHERE id=1')
        if overflow:raise HTTPException(503,'Provider usage/model/tier exceeded acceptance controls; stopped')

    def failed(self,identity,status):
        with self.transaction(True) as db:
            self.policy(db)
            updated=db.execute('UPDATE acceptance_requests SET state=? WHERE id=? AND usage IS NULL AND state=\'reserved\'',(status,identity)).rowcount
            if updated:db.execute('UPDATE acceptance_policy SET closed=1 WHERE id=1')

    def close(self):
        with self.transaction(True) as db:
            self.policy(db);db.execute('UPDATE acceptance_policy SET closed=1 WHERE id=1')
