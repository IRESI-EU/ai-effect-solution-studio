-- Additive and reversible. Apply to a private development/staging database first.
ALTER TABLE solutions ADD COLUMN IF NOT EXISTS design_metadata JSONB;
CREATE TABLE IF NOT EXISTS design_ai_drafts (
    id VARCHAR PRIMARY KEY,
    owner_id VARCHAR NOT NULL REFERENCES users(id),
    revision INTEGER NOT NULL DEFAULT 0,
    state JSONB NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_design_ai_drafts_owner_id ON design_ai_drafts(owner_id);
-- Rollback after disabling DESIGN_AI_ENABLED and stopping pilot traffic:
-- DROP TABLE design_ai_drafts;
-- Keep design_metadata so previously saved drafts retain provenance and input defaults.
