"""Portable, isolated pilot integration suite. JSONB uses SQLite JSON in tests only.

This does not verify PostgreSQL locking; the existing PostgreSQL suite remains separate.
No configured application database is read or mutated.
"""
import json
import os
from copy import deepcopy

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, compiler, **kw):
    return "JSON"


from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
import app.db as application_db  # noqa: E402
application_db.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
application_db.SessionLocal = sessionmaker(bind=application_db.engine, autoflush=False)
from app.main import app  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.service import Service  # noqa: E402
from app.models.solution import Solution  # noqa: E402
from app.services.solution_design import build_linear_builder_design  # noqa: E402
from app.services.design_ai_provider import get_provider  # noqa: E402
from app.schemas.design_ai import AssistantTurn  # noqa: E402


class TestProvider:
    """Explicit test-only provider; never registered by production application code."""
    __test__ = False

    def __init__(self, turn=None, error=None):
        self.turn, self.error, self.contexts = turn, error, []

    async def respond(self, context):
        self.contexts.append(deepcopy(context))
        if self.error:
            raise self.error
        return self.turn


@pytest.fixture
def environment(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "design_ai_enabled", True)
    monkeypatch.setattr(settings, "design_ai_templates", "{}")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "design_ai_model", "")
    with SessionLocal() as db:
        user = User(id="designer", email="designer@example.test", display_name="Test Designer", password_hash=hash_password("PilotTest12345"), role="solution_designer", status="active")
        other = User(id="other", email="other@example.test", display_name="Other", password_hash="unused", role="solution_designer", status="active")
        db.add_all([user, other])
        db.commit()
        policies = {}
        for key, operations in {"denmark": ["BuildRunConfig", "GenerateTopology", "RenderTopologies"], "dutch": ["ConfigureAndSynthesize", "RunBenchmark"], "portugal": ["ActualA", "ActualB", "ActualC", "ActualD"], "germany": ["ProvideData", "GenerateChronics", "FormatOutput"]}.items():
            services = {}
            for operation in operations:
                svc = Service(id=f"{key}-{operation}", name=operation, provider="Isolated test fixture", category=key, description=f"Test-only description for {operation}", input_type="test", output_type="test", status="approved", lifecycle_status="active", operation_name=operation, container_name=operation.lower(), proto_uri="test.proto", image="test:local", internal_port="8080")
                db.add(svc)
                services[operation] = svc
            db.flush()
            nodes, edges = build_linear_builder_design(services, [{"source_service": a, "target_service": b} for a, b in zip(operations, operations[1:])])
            db.add(Solution(id=f"source-{key}", name=f"Test {key}", description="Isolated saved workflow", nodes=nodes, edges=edges, status="draft", created_by_user_id="other"))
            policies[key] = {"solution_id": f"source-{key}"}
        db.commit()
    monkeypatch.setattr(settings, "design_ai_templates", json.dumps(policies))
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"email": "designer@example.test", "password": "PilotTest12345"}).status_code == 200  # gitleaks:allow -- disposable SQLite test login, not an API key
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db(environment):
    with SessionLocal() as session:
        yield session


@pytest.fixture
def provider(environment):
    value = TestProvider(AssistantTurn(message="Proposed name change", template_key=None, expected_revision=0,
        edits=[{"kind": "rename", "value": "My energy design", "node_id": None}]))
    app.dependency_overrides[get_provider] = lambda: value
    return value
