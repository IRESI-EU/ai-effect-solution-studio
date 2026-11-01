-- Additive historical records for the opt-in qualified local capture adapter.
-- The adapter remains disabled unless its existing explicit profile guards pass.
-- Apply after 001..004 with ON_ERROR_STOP; safe to reapply. No evidence is copied.
BEGIN;

CREATE TABLE IF NOT EXISTS local_dutch_executions (
  id varchar PRIMARY KEY,
  workflow_id varchar,
  solution_id varchar NOT NULL,
  owner_user_id varchar NOT NULL,
  submitted jsonb NOT NULL,
  collection jsonb,
  phase varchar NOT NULL DEFAULT 'prepared',
  created_at timestamp DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_local_dutch_executions_workflow_id ON local_dutch_executions(workflow_id);
CREATE INDEX IF NOT EXISTS ix_local_dutch_executions_owner_user_id ON local_dutch_executions(owner_user_id);

COMMIT;
-- On application rollback retain these records, snapshots and all earlier tables.
-- Do not drop history to run an older application; restore a verified backup to
-- a separate database if a true data rollback is required.
