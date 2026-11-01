"""Explicit capture schema rollout; only suite-allocated disposable databases."""
from pathlib import Path

from sqlalchemy import inspect, select

from app.models.local_dutch_execution import LocalDutchExecution


def test_capture_migration_is_additive_and_reapply_preserves_history(fresh_database):
    _, engine = fresh_database
    migration = Path(__file__).resolve().parents[3] / "deploy/migrations/005_local_capture_records.sql"
    ddl = migration.read_text(encoding="utf-8")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as db:
        db.exec_driver_sql(ddl)
    table = LocalDutchExecution.__table__
    with engine.begin() as db:
        db.execute(table.insert().values(id="isolated-migration-history", workflow_id="wf-fixture",
            solution_id="fixture-solution", owner_user_id="fixture-owner",
            submitted={"seed": 43}, collection={"historical": True}, phase="submitted"))
        before = dict(db.execute(select(table)).one()._mapping)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as db:
        db.exec_driver_sql(ddl)
    assert {column["name"] for column in inspect(engine).get_columns(table.name)} == set(table.columns.keys())
    indexes = {index["name"]: index for index in inspect(engine).get_indexes(table.name)}
    assert indexes["ix_local_dutch_executions_workflow_id"]["unique"] is True
    assert indexes["ix_local_dutch_executions_owner_user_id"]["column_names"] == ["owner_user_id"]
    with engine.connect() as db:
        assert dict(db.execute(select(table)).one()._mapping) == before
