import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://solution_studio:solution_studio@postgres:5432/"
    "solution_studio"
)


def _normalized_database_url(raw_url: str):
    url = make_url(raw_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def _database_identity(url):
    return (
        url.host,
        url.port or 5432,
        url.database,
    )


raw_test_database_url = os.environ.get("TEST_DATABASE_URL")
if not raw_test_database_url:
    raise RuntimeError(
        "TEST_DATABASE_URL is required. Operation-contract tests never use "
        "the normal development database."
    )

normal_database_url = _normalized_database_url(
    os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
)
test_database_url = _normalized_database_url(raw_test_database_url)

if _database_identity(test_database_url) == _database_identity(normal_database_url):
    raise RuntimeError(
        "TEST_DATABASE_URL must not identify the normal DATABASE_URL database."
    )
if not test_database_url.database or not test_database_url.database.endswith("_test"):
    raise RuntimeError(
        "TEST_DATABASE_URL must use a database name ending in '_test'."
    )

# app.core.config reads DATABASE_URL at import time. Point the complete test
# application, including main.py's create_all call, at the isolated database
# before importing any application database module.
os.environ["DATABASE_URL"] = test_database_url.render_as_string(
    hide_password=False
)

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.deployment import Deployment  # noqa: E402,F401
from app.models.operation_contract import OperationContract  # noqa: E402,F401
from app.models.service import Service  # noqa: E402,F401
from app.models.solution import Solution  # noqa: E402,F401
from app.models.user import AuditEvent, User, UserSession  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from uuid import uuid4  # noqa: E402


test_engine = create_engine(test_database_url)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def isolated_database_schema():
    # Recreate the isolated schema so interrupted prior runs and test ordering
    # cannot affect this session.
    with test_engine.begin() as connection:
        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)

    yield

    app.dependency_overrides.clear()
    with test_engine.begin() as connection:
        Base.metadata.drop_all(bind=connection)
    test_engine.dispose()


@pytest.fixture(scope="session")
def client(isolated_database_schema):
    app.dependency_overrides[get_db] = override_get_db
    with TestingSessionLocal() as db:
        admin = User(
            id=str(uuid4()),
            email="test-admin@ai-effect.eu",
            display_name="Test Administrator",
            password_hash=hash_password("TestAdministrator123"),
            role="platform_admin",
            status="active",
        )
        db.add(admin)
        db.commit()
    with TestClient(app) as test_client:
        response = test_client.post(
            "/auth/login",
            json={"email": "test-admin@ai-effect.eu", "password": "TestAdministrator123"},
        )
        assert response.status_code == 200
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def anonymous_client(isolated_database_schema):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def session_factory(isolated_database_schema):
    return TestingSessionLocal


@pytest.fixture(scope="session")
def isolated_test_database_name():
    return test_database_url.database
