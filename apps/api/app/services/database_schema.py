"""Read-only release startup gate. Migration is an explicit operator action."""
from sqlalchemy import inspect


def require_migrated_schema(engine, metadata):
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = []
    for name, table in metadata.tables.items():
        if name not in existing:
            missing.append(name)
            continue
        columns = {c['name'] for c in inspector.get_columns(name)}
        missing.extend(name+'.'+c.name for c in table.columns if c.name not in columns)
    if missing:
        raise RuntimeError('Database migrations are required before startup: '+', '.join(sorted(missing))+
            '. Apply the reviewed additive migration bundle explicitly; startup made no schema changes.')
    # These constraints prevent ambiguous workflow associations and overwriting
    # pinned task evidence. Mere column existence does not establish them.
    unique = [c['column_names'] for c in inspector.get_unique_constraints('execution_submissions')]
    unique += [c['column_names'] for c in inspector.get_indexes('execution_submissions') if c['unique']]
    if ['workflow_id'] not in unique:
        raise RuntimeError('Database migration incomplete: execution_submissions.workflow_id must be unique.')
    if set(inspector.get_pk_constraint('instance_evidence_receipts')['constrained_columns']) != {'submission_id','task_id'}:
        raise RuntimeError('Database migration incomplete: task evidence receipt primary key differs.')
