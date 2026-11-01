"""Preview/apply one attributable 12→13 amendment. Never called by the app.

Earlier policies, usage and checkpoints stay intact. A Docker path mapping is
accepted only after inspecting the actual existing profile's bind mounts.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from app.services.design_ai_allowance_operator import identity, digest, has_amendments


def mount_identity(source):
    # Docker Desktop reports a Windows host bind as this WSL path. Translate
    # only that exact representation; comparison still requires the full,
    # resolved original host directory (never merely a matching basename).
    if os.name == 'nt':
        match = re.fullmatch(r'/run/desktop/mnt/host/([A-Za-z])/(.+)', source)
        if match:
            if '..' in match[2].split('/'):
                raise ValueError('Invalid host mount path')
            source = match[1]+':/'+match[2]
    return identity(source)


def runtime_scope(container, ledger, task):
    if not container:
        return None
    if container != 'ai-effect-aie37-api-1':
        raise ValueError('Only the existing isolated AIE-37 API container may be mapped')
    value = json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
    labels = value['Config'].get('Labels') or {}
    if (labels.get('com.docker.compose.project') != 'ai-effect-aie37'
        or labels.get('com.docker.compose.service') != 'api'
        or value['Config']['Image'] != 'ai-effect-aie37-api:goal-results-v1'):
        raise ValueError('Wrong integration runtime identity')
    mappings = {}
    for directory, filename, target in [(ledger.parent,ledger.name,'/acceptance'),(task.parent,task.name,'/task-limits')]:
        mount = next((item for item in value['Mounts'] if item['Destination']==target and item['Type']=='bind'),None)
        if not mount or mount_identity(mount['Source']) != identity(directory):
            raise ValueError('The runtime must bind the exact existing ledger and checkpoint directories')
        mappings['ledger_path' if target=='/acceptance' else 'task_path'] = target+'/'+filename
    return {**mappings,'container_id':value['Id'],'image_id':value['Image']}


def amend_demo_call(path, *, expected_ledger_sha256, expected_limit, new_limit, amendment_id,
                    operator, reason, authorization_ref, task_limit_file, runtime_container=None, dry_run=True):
    from app.services.design_ai_budget import Budget, RESERVATION
    path,task = Path(path).resolve(),Path(task_limit_file).resolve()
    if not path.is_file() or not task.is_file() or path==task:
        raise ValueError('Exact existing ledger and immutable checkpoint required')
    if type(expected_limit) is not int or type(new_limit) is not int or (expected_limit,new_limit)!=(12,13):
        raise ValueError('This operation supports only one 12 to 13 call amendment')
    if not re.fullmatch(r'[a-f0-9]{64}',expected_ledger_sha256) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',amendment_id):
        raise ValueError('Exact ledger fingerprint and attributable amendment ID required')
    if any(not isinstance(v,str) or not v.strip() or len(v)>2000 for v in (operator,reason,authorization_ref)):
        raise ValueError('Operator, reason and authorization reference required')
    task_bytes=task.read_bytes()
    scope=runtime_scope(runtime_container,path,task)
    request={'ledger':identity(path),'expected_ledger_sha256':expected_ledger_sha256,'expected_limit':expected_limit,
        'new_limit':new_limit,'amendment_id':amendment_id,'operator':operator,'reason':reason,'authorization_ref':authorization_ref,
        'task_checkpoint':identity(task),'task_sha256':digest(task_bytes),'runtime_scope':scope}
    request_json=json.dumps(request,sort_keys=True)
    with sqlite3.connect(path.as_uri()+'?mode='+('ro' if dry_run else 'rw'),uri=True,timeout=10) as db:
        db.execute('BEGIN' if dry_run else 'BEGIN IMMEDIATE')
        if not has_amendments(db):
            raise ValueError('The prior audited 10 to 12 amendment must exist')
        replay=db.execute('SELECT request_json,audit_json FROM allowance_amendments WHERE amendment_id=?',(amendment_id,)).fetchone()
        if replay:
            if replay[0]!=request_json:raise ValueError('Amendment identifier conflicts with its original request')
            return {'applied':False,'replayed':True,'audit':json.loads(replay[1])}
        prior=db.execute('SELECT audit_json,ledger_path FROM allowance_amendments ORDER BY rowid').fetchall()
        if len(prior)!=1 or prior[0][1]!=identity(path):
            raise ValueError('This exact original ledger must have only its prior one-time amendment')
        audit=json.loads(prior[0][0])
        if audit['before']['max_calls']!=10 or audit['after']['max_calls']!=12:
            raise ValueError('Unexpected prior amendment history')
        if digest(path.read_bytes())!=expected_ledger_sha256:raise ValueError('Ledger fingerprint changed')
        closed,money,calls=db.execute('SELECT closed,limit_nano,max_calls FROM batch WHERE id=1').fetchone()
        rows=[dict(zip(('id','held','reserved','input_bound','usage','status','response_id'),row))
            for row in db.execute('SELECT id,held,reserved,input_bound,usage,status,response_id FROM requests ORDER BY id')]
        if closed or money!=100_000_000 or calls!=12 or len(rows)!=12:
            raise ValueError('Expected the open, exhausted 12-call USD0.10 policy')
        if any(row['usage'] is None or row['status']=='reserved' for row in rows):raise ValueError('Outstanding or unknown usage blocks amendment')
        if money-sum(row['held'] for row in rows)<RESERVATION:raise ValueError('Remaining balance cannot reserve one request')
        policy=json.loads(task_bytes);state=Budget(path,task_limit_file=task).task_availability(db)
        if (policy['baseline_count']!=12 or policy['max_calls']!=1 or policy['max_reserved_nano']!=RESERVATION
            or not state['can_request'] or state['request_count']!=0):
            raise ValueError('An unused one-call USD0.005 checkpoint on the current 12 rows is required')
        before={'closed':closed,'limit_nano':money,'max_calls':calls};after={**before,'max_calls':13}
        audit={'request':request,'before':before,'after':after,'used_calls':12,'held_nano':sum(row['held'] for row in rows),
            'usage_records_sha256':digest(json.dumps(rows,sort_keys=True).encode()),'runtime_scope':scope,
            'applied_at':None if dry_run else datetime.now(timezone.utc).isoformat()}
        if not dry_run:
            if task.read_bytes()!=task_bytes:raise ValueError('Checkpoint changed during amendment')
            db.execute('UPDATE batch SET max_calls=13 WHERE id=1 AND max_calls=12 AND closed=0')
            db.execute('INSERT INTO allowance_amendments VALUES (?,?,?,?,?,?)',(amendment_id,request_json,json.dumps(audit,sort_keys=True),identity(task),digest(task_bytes),identity(path)))
        return {'applied':not dry_run,'replayed':False,'audit':audit}
