"""Synthetic bootstrap and operator guard tests, confined to in-memory fixtures."""
import importlib.util
import json
from pathlib import Path
from secrets import token_urlsafe
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.core.config import settings
from app.models.user import User
from app.models.solution import Solution
from app.models.service import Service


def script(name):
    path = Path(__file__).resolve().parents[3] / "deploy/staging" / name
    spec = importlib.util.spec_from_file_location("isolated_" + name.replace(".", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def synthetic(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        original = db.execute
        monkeypatch.setattr(db, "execute", lambda query, *a, **kw: SimpleNamespace(scalar_one=lambda: "design_ai_staging")
            if str(query) == "SELECT current_database()" else original(query, *a, **kw))
        for key in ("design_ai_enabled", "design_ai_dutch_demo", "aie37_qualification"):
            monkeypatch.setattr(settings, key, False)
        for key in ("openai_api_key", "design_ai_demo_execution_grant_file", "design_ai_acceptance_budget_file", "design_ai_acceptance_task_limit_file"):
            monkeypatch.setattr(settings, key, "")
        monkeypatch.setattr(settings, "database_url", "postgresql://unused@postgres/design_ai_staging")
        monkeypatch.setattr(settings, "bootstrap_admin_email", "administrator@staging.invalid")
        password = "Aa0" + token_urlsafe(24)
        monkeypatch.setattr(settings, "bootstrap_admin_password", password)
        values = {"STAGING_REVIEW_SEED": "synthetic-only", "STAGING_DESIGNER_A_EMAIL": "a@staging.invalid",
                  "STAGING_DESIGNER_B_EMAIL": "b@staging.invalid", "STAGING_DESIGNER_A_PASSWORD": password,
                  "STAGING_DESIGNER_B_PASSWORD": password}
        yield db, values
    engine.dispose()


def test_synthetic_bootstrap_is_new_owned_data_and_refuses_reset(synthetic):
    db, values = synthetic
    module = script("synthetic_seed.py")
    result = module.seed(db, values)
    assert result == {"synthetic_only": True, "accounts": 3, "solutions": 2, "services": 1, "workflow_executions": 0}
    assert db.query(User).count() == 3 and db.query(Service).count() == 1
    assert len({row.created_by_user_id for row in db.query(Solution)}) == 2
    before = {user.id: user.password_hash for user in db.query(User)}
    with pytest.raises(RuntimeError, match="already exists"):
        module.seed(db, values)
    assert {user.id: user.password_hash for user in db.query(User)} == before
    assert db.query(Solution).count() == 2


def test_bootstrap_transaction_does_not_commit_half_an_account_set(synthetic, monkeypatch):
    db, values = synthetic
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("isolated commit failure")))
    with pytest.raises(RuntimeError, match="commit failure"):
        script("synthetic_seed.py").seed(db, values)
    db.rollback()
    assert db.query(User).count() == db.query(Solution).count() == db.query(Service).count() == 0


def test_bootstrap_refuses_qualification_identity(synthetic, monkeypatch):
    db, values = synthetic
    monkeypatch.setattr(settings, "database_url", "postgresql://unused@postgres/design_aie37_qualification")
    with pytest.raises(RuntimeError, match="fresh disconnected"):
        script("synthetic_seed.py").seed(db, values)
    assert db.query(User).count() == 0


def test_operator_mutation_requires_explicit_approval_before_docker(tmp_path, monkeypatch):
    module = script("local_review.py")
    (tmp_path / "proposal.json").write_text(json.dumps({"project": module.PROJECT}))
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: pytest.fail("Docker must not be called"))
    with pytest.raises(RuntimeError, match="requires explicit"):
        module.operate(tmp_path, "start", False)
