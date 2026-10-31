"""Disposable test ledgers only. No shared policy, checkpoint or funds touched."""
import json
from pathlib import Path
import sqlite3
import pytest
from fastapi import HTTPException
from app.services.design_ai_allowance_operator import amend_calls
from app.services.design_ai_demo_allowance import amend_demo_call
from app.services.design_ai_budget import Budget
from test_allowance_amendment import prepared, rows, sha


@pytest.fixture
def demo_allowance(prepared,tmp_path):
    path,old_task,old_args=prepared
    amend_calls(**old_args,dry_run=False)
    budget=Budget(path,task_limit_file=old_task)
    for _ in range(2):
        identifier=budget.reserve(16000,2000)
        budget.settle(identifier,{'status':'completed','usage':{'input_tokens':1,'output_tokens':1}})
    task=tmp_path/'OFFLINE-goal-results-one.json'
    from app.services.design_ai_allowance_operator import digest
    task.write_text(json.dumps({'ledger':path.name,'baseline_count':12,'baseline_sha256':digest(json.dumps(rows(path),sort_keys=True).encode()),
        'max_calls':1,'max_reserved_nano':5_000_000}))
    args={'path':path,'expected_ledger_sha256':sha(path),'expected_limit':12,'new_limit':13,'amendment_id':'OFFLINE-demo-one',
        'operator':'test-only operator','reason':'one OFFLINE provider attempt','authorization_ref':'test-only explicit authorization','task_limit_file':task}
    return path,old_task,task,args


def test_preview_and_one_slot_preserve_history_money_and_checkpoint(demo_allowance):
    path,old_task,task,args=demo_allowance
    original,old_bytes,task_bytes,usage=path.read_bytes(),old_task.read_bytes(),task.read_bytes(),rows(path)
    preview=amend_demo_call(**args)
    assert not preview['applied'] and path.read_bytes()==original
    assert preview['audit']['before']['max_calls']==12 and preview['audit']['after']['max_calls']==13
    applied=amend_demo_call(**args,dry_run=False)
    assert applied['applied'] and applied['audit']['after']['limit_nano']==100_000_000
    assert rows(path)==usage and old_task.read_bytes()==old_bytes and task.read_bytes()==task_bytes
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM allowance_amendments').fetchone()[0]==2
    assert not Budget(path,task_limit_file=old_task).availability()['can_request']
    assert not Budget(path).availability()['can_request']
    budget=Budget(path,task_limit_file=task);identifier=budget.reserve(16000,2000)
    budget.settle(identifier,{'status':'completed','usage':{'input_tokens':1,'output_tokens':1}})
    assert len(rows(path))==13 and not budget.availability()['can_request']
    with pytest.raises(HTTPException):budget.reserve(16000,2000)
    assert amend_demo_call(**args,dry_run=False)['replayed']


@pytest.mark.parametrize('mutation',['hash','larger','money','outstanding','closed','scope','missing_author','repeat_extension'])
def test_invalid_amendment_cannot_write(demo_allowance,mutation):
    path,old_task,task,args=demo_allowance
    if mutation=='hash':args['expected_ledger_sha256']='0'*64
    elif mutation=='larger':args['new_limit']=14
    elif mutation=='missing_author':args['authorization_ref']=''
    elif mutation=='scope':
        value=json.loads(task.read_text());value['max_calls']=2;task.write_text(json.dumps(value))
    elif mutation=='repeat_extension':
        amend_demo_call(**args,dry_run=False);args['amendment_id']='OFFLINE-another'
    else:
        with sqlite3.connect(path) as db:
            if mutation=='money':db.execute('UPDATE batch SET limit_nano=200000000')
            elif mutation=='closed':db.execute('UPDATE batch SET closed=1')
            else:db.execute('UPDATE requests SET usage=NULL WHERE id=12')
        args['expected_ledger_sha256']=sha(path)
    original=path.read_bytes()
    with pytest.raises((ValueError,HTTPException)):amend_demo_call(**args,dry_run=False)
    assert path.read_bytes()==original


def test_runtime_mapping_requires_actual_existing_profile_mounts(demo_allowance,monkeypatch):
    from app.services import design_ai_demo_allowance as operator
    path,old_task,task,args=demo_allowance
    info={'Id':'test-container-id','Image':'sha256:'+'a'*64,'Config':{'Image':'ai-effect-aie37-api:goal-results-v1',
        'Labels':{'com.docker.compose.project':'ai-effect-aie37','com.docker.compose.service':'api'}},
        'Mounts':[{'Destination':target,'Type':'bind','Source':str(folder)} for target,folder in [('/acceptance',path.parent),('/task-limits',task.parent)]]}
    monkeypatch.setattr(operator.subprocess,'check_output',lambda *a,**k:json.dumps([info]))
    preview=amend_demo_call(**args,runtime_container='ai-effect-aie37-api-1')
    assert preview['audit']['runtime_scope']['ledger_path']=='/acceptance/'+path.name
    # The real Windows Docker Desktop representation resolves to the SAME full
    # host directory, rather than authorizing another copy of the ledger.
    import os
    if os.name=='nt':
        for mount in info['Mounts']:
            folder=Path(mount['Source'])
            mount['Source']='/run/desktop/mnt/host/'+folder.drive[0].lower()+folder.as_posix()[2:]
        assert amend_demo_call(**args,runtime_container='ai-effect-aie37-api-1')['audit']['runtime_scope']==preview['audit']['runtime_scope']
    info['Mounts'][0]['Source']=str(path.parent/'wrong')
    before=path.read_bytes()
    with pytest.raises(ValueError):amend_demo_call(**args,runtime_container='ai-effect-aie37-api-1',dry_run=False)
    assert before==path.read_bytes()
