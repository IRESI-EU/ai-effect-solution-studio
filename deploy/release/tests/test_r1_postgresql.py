"""R1-only PostgreSQL16 checks, schema-only production fixture + synthetic rows.

Opt in with a NEW local r1_cp01 database/role. Never uses production data or
dispatches workflows. Existing databases are neither reset nor dropped.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
from threading import Barrier
from uuid import uuid4

import pytest
import psycopg
from psycopg import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError, IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[3]
DSN = os.environ.get('R1_POSTGRES_TEST_DSN')
pytestmark = pytest.mark.skipif(not DSN, reason='Requires separately prepared local R1 PostgreSQL16 database')


@pytest.fixture
def database():
    url = make_url(DSN)
    assert url.host in {'127.0.0.1','localhost'} and url.database == 'r1_cp01'
    assert url.username == 'r1_operator', 'Never use a production/staging account'
    name = 'r1_cp01_test_'+uuid4().hex
    admin = dict(host=url.host, port=url.port, user=url.username, password=url.password, dbname=url.database)
    with psycopg.connect(**admin, autocommit=True) as c:
        c.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(name)))
    engine = create_engine(url.set(database=name), pool_size=4, max_overflow=0)
    schema = (ROOT/'deploy/release/tests/fixtures/production-schema-20261122.sql').read_text(encoding='utf-8')
    with psycopg.connect(**(admin | {'dbname':name}), autocommit=True) as c:
        c.execute(schema)
        c.execute('SET search_path TO public') # pg_dump intentionally clears it.
        c.execute("""INSERT INTO users(id,email,display_name,password_hash,role,status,created_at,updated_at)
          VALUES('r1-owner','owner@r1-fixture.invalid','R1 fixture owner','unused-test-hash','solution_designer','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
                ('r1-other','other@r1-fixture.invalid','R1 fixture other','unused-test-hash','solution_designer','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);
          INSERT INTO solutions(id,name,nodes,edges,status,created_at,updated_at,created_by_user_id)
          VALUES('r1-owned','Synthetic R1 design','[]','[]','draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'r1-owner'),
                ('r1-ownerless','Historical ownerless fixture','[]','[]','draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,NULL);
          INSERT INTO deployments(id,workflow_id,name,status,created_by_user_id)
          VALUES('r1-old-deployment','r1-old-workflow','Historical synthetic result','completed',NULL);""")
    # Load model definitions only. Importing app.main would itself bootstrap the
    # schema in legacy mode and conceal the missing-column boundary under test.
    for path in (ROOT/'apps/api/app/models').glob('*.py'):
        if path.stem!='__init__': importlib.import_module('app.models.'+path.stem)
    try: yield engine, name, admin
    finally: engine.dispose()  # Preserve this task's small synthetic DBs for review.


def migrate(engine):
    url = engine.url
    with psycopg.connect(host=url.host, port=url.port, user=url.username, password=url.password,
                         dbname=url.database, autocommit=True) as c:
        for path in sorted((ROOT/'deploy/migrations').glob('00[345]*.sql')):
            c.execute(path.read_text(encoding='utf-8'))


def legacy_rows(engine):
    with engine.connect() as c:
        return {table:[dict(r) for r in c.execute(text(query)).mappings()] for table,query in {
            'solutions':'select id,name,nodes,edges,created_by_user_id from solutions order by id',
            'deployments':'select id,workflow_id,name,status,created_by_user_id from deployments order by id',
            'users':'select id,email,role,status,password_hash from users order by id'}.items()}


def test_current_production_schema_fails_read_only_gate_then_migrates_twice(database):
    from app.db import Base
    from app.models.solution import Solution
    from app.services.database_schema import require_migrated_schema
    engine,_,_=database; before=legacy_rows(engine)
    assert len(inspect(engine).get_table_names())==7
    with pytest.raises(RuntimeError,match='solutions.design_metadata'):
        require_migrated_schema(engine,Base.metadata)
    assert len(inspect(engine).get_table_names())==7 # Gate issued NO DDL.
    with Session(engine) as db, pytest.raises(ProgrammingError) as error:
        db.get(Solution,'r1-owned')
    assert error.value.orig.sqlstate=='42703' # Actual PostgreSQL undefined_column.
    for _ in range(2):
        migrate(engine);require_migrated_schema(engine,Base.metadata)
        assert legacy_rows(engine)==before
    with Session(engine) as db:
        assert db.get(Solution,'r1-owned').design_metadata is None


def test_concurrent_canonical_saves_reject_stale_writer_and_other_owner(database):
    from app.models.solution import Solution
    from app.models.user import User
    from app.schemas.solution import SolutionUpdate
    from app.services.solution_editing import update, owned_solution
    engine,_,_=database;migrate(engine)
    with Session(engine) as db: version=db.get(Solution,'r1-owned').updated_at.isoformat()
    barrier=Barrier(2)
    def save(name):
        with Session(engine) as db:
            owner=db.get(User,'r1-owner');barrier.wait(timeout=10)
            try:
                update('r1-owned',SolutionUpdate(name=name,expected_updated_at=version,
                    design_metadata={'run_input':{'fixture':'permitted synthetic reference'}}),db,owner)
                return 200
            except HTTPException as exc:db.rollback();return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(save,'R1 fixture choice '+n) for n in ['A','B']]
        assert sorted(f.result(timeout=20) for f in futures)==[200,409]
    with Session(engine) as db:
        original=deepcopy(db.get(Solution,'r1-owned').design_metadata)
        with pytest.raises(HTTPException) as denied:owned_solution('r1-owned',db,db.get(User,'r1-other'),lock=True)
        assert denied.value.status_code==403;db.rollback()
        with pytest.raises(HTTPException) as legacy:owned_solution('r1-ownerless',db,db.get(User,'r1-owner'))
        assert legacy.value.status_code==403
        assert db.get(Solution,'r1-owned').design_metadata==original
        assert db.get(Solution,'r1-ownerless').created_by_user_id is None


def test_separate_immutable_submission_records_and_task_receipt_conflict(database):
    from app.models.user import User
    from app.models.execution_submission import ExecutionSubmission, InstanceEvidenceReceipt
    from app.services.execution_submission import prepare, view
    engine,_,_=database;migrate(engine)
    class PersistenceFixture:
        solution_id='r1-owned'
        def __init__(self,value):self.value=value
        def model_dump(self,**_):return {'fixture_only':True,'settings':{'count':self.value},'run_input':{'fixture':'permitted synthetic reference'}}
    with Session(engine) as db:
        owner=db.get(User,'r1-owner')
        a=prepare(db,owner,PersistenceFixture(1),{'fixture_only':True});a.workflow_id='r1-fixture-association-a';db.commit()
        frozen=deepcopy(view(a));a_id=a.id
        b=prepare(db,owner,PersistenceFixture(2),{'fixture_only':True});b.workflow_id='r1-fixture-association-b';db.commit()
        db.expire_all();assert view(db.get(ExecutionSubmission,a_id))==frozen
        assert a.submitted_sha256!=b.submitted_sha256
        db.add(InstanceEvidenceReceipt(submission_id=a.id,task_id='r1-fixture-task',manifest_sha256='a'*64));db.commit()
        db.add(InstanceEvidenceReceipt(submission_id=a.id,task_id='r1-fixture-task',manifest_sha256='b'*64))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        assert db.get(InstanceEvidenceReceipt,(a.id,'r1-fixture-task')).manifest_sha256=='a'*64
        assert view(db.get(ExecutionSubmission,a_id))==frozen
        b=db.get(ExecutionSubmission,b.id);b.workflow_id='r1-fixture-association-a'
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        assert view(db.get(ExecutionSubmission,a_id))==frozen


def test_synthetic_backup_separate_restore_and_old_column_reads(database):
    engine,name,admin=database;migrate(engine)
    with engine.begin() as c:
        c.execute(text("update solutions set design_metadata=cast(:metadata as jsonb) where id='r1-owned'"),
                  {'metadata':json.dumps({'run_input':{'fixture':'synthetic'}})})
    before=legacy_rows(engine)
    container=os.environ['R1_POSTGRES_TEST_CONTAINER']
    assert container=='aie-r1-cp01-postgres-20261122'
    dump=subprocess.run(['docker','exec',container,'pg_dump','-U',admin['user'],'-d',name,'-Fc'],capture_output=True,timeout=30)
    assert dump.returncode==0,'Synthetic backup failed; do not expose raw diagnostics'
    restored='r1_cp01_restore_'+uuid4().hex
    with psycopg.connect(**admin,autocommit=True) as c:c.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(restored)))
    result=subprocess.run(['docker','exec','-i',container,'pg_restore','-U',admin['user'],'-d',restored,'--no-owner','--exit-on-error'],input=dump.stdout,capture_output=True,timeout=30)
    assert result.returncode==0,'Synthetic separate restore failed'
    other=create_engine(engine.url.set(database=restored))
    try:
        assert legacy_rows(other)==before
        with other.connect() as c:assert c.execute(text("select design_metadata from solutions where id='r1-owned'")).scalar()=={'run_input':{'fixture':'synthetic'}}
    finally:other.dispose()
    if os.environ.get('R1_EVIDENCE_DIR'):
        p=Path(os.environ['R1_EVIDENCE_DIR'])
        (p/'synthetic-r1-backup.private.dump').write_bytes(dump.stdout)
        (p/'postgres-backup-result.private.json').write_text(json.dumps(dict(synthetic_only=True,
            sha256=hashlib.sha256(dump.stdout).hexdigest(),bytes=len(dump.stdout),separate_restore=True,old_column_reads=True)),encoding='utf8')


@pytest.mark.parametrize('kind',['workflow','receipt'])
def test_startup_rejects_missing_history_integrity_constraint(database,kind):
    from app.db import Base
    from app.services.database_schema import require_migrated_schema
    engine,_,_=database;migrate(engine)
    with engine.begin() as c:
        c.execute(text('ALTER TABLE execution_submissions DROP CONSTRAINT execution_submissions_workflow_id_key'
            if kind=='workflow' else 'ALTER TABLE instance_evidence_receipts DROP CONSTRAINT instance_evidence_receipts_pkey'))
    with pytest.raises(RuntimeError,match='migration incomplete'):
        require_migrated_schema(engine,Base.metadata)
