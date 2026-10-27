-- Additive AIE-18 records. No updates to solutions, deployments, pilot ledgers or history.
CREATE TABLE IF NOT EXISTS execution_submissions (
  id varchar PRIMARY KEY,
  owner_user_id varchar NOT NULL,
  solution_id varchar,
  workflow_id varchar UNIQUE,
  submitted jsonb NOT NULL,
  submitted_sha256 varchar NOT NULL,
  phase varchar NOT NULL DEFAULT 'prepared',
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_execution_submissions_owner_user_id ON execution_submissions(owner_user_id);
CREATE INDEX IF NOT EXISTS ix_execution_submissions_solution_id ON execution_submissions(solution_id);
CREATE INDEX IF NOT EXISTS ix_execution_submissions_workflow_id ON execution_submissions(workflow_id);
CREATE TABLE IF NOT EXISTS instance_evidence_receipts (
  submission_id varchar NOT NULL,
  task_id varchar NOT NULL,
  manifest_sha256 varchar NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (submission_id, task_id)
);
