"""Actual PostgreSQL tests. Only databases created by this run may be reset.

TEST_DATABASE_URL supplies connection credentials, never a database to erase.
Each run creates fresh random *_test databases on a loopback cluster.
"""
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

raw = os.environ.get("TEST_DATABASE_URL")
if not raw:
    raise RuntimeError("TEST_DATABASE_URL is required for the isolated PostgreSQL suite")
connection_url = make_url(raw)
if connection_url.get_backend_name() != "postgresql" or connection_url.host not in {"localhost", "127.0.0.1", "::1"}:
    raise RuntimeError("This acceptance suite only creates databases on an explicit local PostgreSQL cluster")
connection_url = connection_url.set(drivername="postgresql+psycopg")
created = []


def allocate():
    name = "design_ai_" + uuid4().hex + "_test"
    with psycopg.connect(connection_url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(name)))
    created.append(name)
    return connection_url.set(database=name)


application_url = allocate()
os.environ["DATABASE_URL"] = application_url.render_as_string(hide_password=False)
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""
os.environ["DESIGN_AI_ENABLED"] = "false"

from app.main import app  # noqa: E402
from app.db import Base, engine, SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.service import Service  # noqa: E402
from app.models.solution import Solution  # noqa: E402
from app.models.deployment import Deployment  # noqa: E402
from app.services.solution_design import build_linear_builder_design  # noqa: E402

if engine.dialect.name != "postgresql" or engine.url.database != application_url.database:
    raise RuntimeError("Run the PostgreSQL suite in its own pytest process; cached application modules use a different database")


@pytest.fixture(scope="session", autouse=True)
def cleanup_owned_databases():
    yield
    engine.dispose()
    with psycopg.connect(connection_url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False), autocommit=True) as admin:
        for name in created:
            admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()", (name,))
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def fresh_database():
    target = allocate()
    target_engine = create_engine(target)
    yield target, target_engine
    target_engine.dispose()


@pytest.fixture
def seeded(monkeypatch):
    # The module itself created this database; never reset the caller's URL.
    assert engine.url.database in created
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "design_ai_enabled", True)
    import json
    policies = {key:{"solution_id":"source-"+key} for key in ("denmark","dutch")}
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps(policies))
    with SessionLocal() as db:
        db.add_all([User(id="a",email="a@example.test",display_name="Acceptance A",password_hash=hash_password("LocalAcceptance123"),role="solution_designer",status="active"),
                    User(id="b",email="b@example.test",display_name="Acceptance B",password_hash=hash_password("LocalAcceptance123"),role="solution_designer",status="active")])
        db.commit()
        for key, ops in {"denmark":["BuildRunConfig","GenerateTopology","RenderTopologies"],"dutch":["ConfigureAndSynthesize","RunBenchmark"]}.items():
            services={}
            for op in ops:
                services[op]=Service(id=key+"-"+op,name=op,description="Synthetic PostgreSQL integration fixture",provider="Test",category=key,input_type="test",output_type="test",status="approved",operation_name=op,container_name=key+op,proto_uri="test.proto")
                db.add(services[op])
            db.flush()
            nodes,edges=build_linear_builder_design(services,[{"source_service":a,"target_service":b} for a,b in zip(ops,ops[1:])])
            db.add(Solution(id="source-"+key,name="PostgreSQL fixture "+key,nodes=nodes,edges=edges,status="draft",created_by_user_id="a"))
        db.commit()
        db.add(Deployment(id="historical",workflow_id="synthetic-historical-id",solution_id="source-denmark",name="Historical fixture",status="completed",created_by_user_id="a"))
        db.commit()
    return SessionLocal
