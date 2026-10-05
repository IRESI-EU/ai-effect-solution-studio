BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    display_name VARCHAR(160) NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(40) NOT NULL DEFAULT 'solution_designer',
    node VARCHAR(40),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    last_login_at TIMESTAMP,
    CONSTRAINT ck_users_role CHECK (role IN ('solution_designer', 'node_manager', 'platform_admin')),
    CONSTRAINT ck_users_status CHECK (status IN ('pending', 'active', 'rejected', 'suspended')),
    CONSTRAINT ck_users_node CHECK (node IS NULL OR node IN ('germany', 'portugal', 'denmark', 'netherlands')),
    CONSTRAINT ck_node_manager_assignment CHECK (role <> 'node_manager' OR node IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_agent VARCHAR(500),
    ip_address VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR PRIMARY KEY,
    actor_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id VARCHAR(200),
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_audit_events_actor_user_id ON audit_events(actor_user_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_created_action ON audit_events(created_at, action);

ALTER TABLE services ADD COLUMN IF NOT EXISTS owner_node VARCHAR(40);
ALTER TABLE services ADD COLUMN IF NOT EXISTS created_by_user_id VARCHAR;
ALTER TABLE solutions ADD COLUMN IF NOT EXISTS created_by_user_id VARCHAR;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS created_by_user_id VARCHAR;

CREATE INDEX IF NOT EXISTS ix_services_owner_node ON services(owner_node);
CREATE INDEX IF NOT EXISTS ix_services_created_by_user_id ON services(created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_solutions_created_by_user_id ON solutions(created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_deployments_created_by_user_id ON deployments(created_by_user_id);

COMMIT;
