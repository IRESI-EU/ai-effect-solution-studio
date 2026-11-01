"""Fresh local-review schema initialization on a suite-created test database."""
from pathlib import Path

from sqlalchemy import inspect, select
from app.db import Base
from app.models.service import Service
from app.models.solution import Solution
from app.models.deployment import Deployment
from app.models.operation_contract import OperationContract


def test_four_core_tables_then_additive_migrations_initialize_fresh_review_database(fresh_database):
    _, engine = fresh_database
    core = [Service.__table__, Solution.__table__, Deployment.__table__, OperationContract.__table__]
    Base.metadata.create_all(engine, tables=core)
    assert set(inspect(engine).get_table_names()) == {table.name for table in core}
    with engine.begin() as db:
        db.execute(Solution.__table__.insert().values(id="synthetic-schema-sentinel", name="Synthetic empty review",
                                                    nodes=[], edges=[], status="draft"))
        before = dict(db.execute(select(Solution.__table__)).one()._mapping)
    migrations = sorted((Path(__file__).resolve().parents[3] / "deploy/migrations").glob("*.sql"))
    assert len(migrations) == 5
    for _ in range(2):
        Base.metadata.create_all(engine, tables=core)
        for migration in migrations:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as db:
                db.exec_driver_sql(migration.read_text(encoding="utf-8"))
    schema = inspect(engine)
    assert set(schema.get_table_names()) == set(Base.metadata.tables)
    for table in Base.metadata.sorted_tables:
        assert {column["name"] for column in schema.get_columns(table.name)} == set(table.columns.keys())
    assert {constraint["name"] for constraint in schema.get_check_constraints("users")} >= {
        "ck_users_role", "ck_users_status", "ck_users_node", "ck_node_manager_assignment"}
    with engine.connect() as db:
        assert dict(db.execute(select(Solution.__table__)).one()._mapping) == before
