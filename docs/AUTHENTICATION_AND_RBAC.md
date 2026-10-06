# Authentication and role-based access control

## Status

Implemented for local validation. Do not deploy this change until the database migration, initial administrator creation, backup and rollback steps have been approved.

## Account onboarding

1. A researcher opens `/register` and provides a name, email, password, requested role and affiliated node.
2. The account is stored with `pending` status. Pending accounts cannot sign in.
3. A Platform Administrator opens **Admin → User access**, verifies the email and node affiliation outside the portal, and either approves or rejects the request.
4. Approval records the administrator and approval time. The user can then sign in.
5. Suspended and rejected accounts cannot sign in. Suspending a user revokes all active sessions.

Email verification is an administrator-controlled manual process in this version. Automatic mailbox verification links require an institutional SMTP or transactional-email service and are intentionally not simulated.

## Roles and permissions

| Capability | Platform Admin | Node Manager | Solution Designer |
|---|---:|---:|---:|
| View active service catalogue | Yes | Yes | Yes |
| Build and deploy solutions | Yes | Yes | Yes |
| Manage own solutions and deployments | Yes | Yes | Yes |
| View all solutions and deployments | Yes | No | No |
| Publish services | Yes | Assigned node only | No |
| Manage service lifecycle and contracts | Any service | Assigned node only | No |
| Approve or reject services | Yes | No | No |
| Approve, reject, suspend and reactivate users | Yes | No | No |
| View the audit log API | Yes | No | No |

Supported node assignments are `germany`, `portugal`, `denmark` and `netherlands`.

## Enforcement model

- Permissions are enforced by the FastAPI backend. Frontend navigation is only a usability aid.
- Services store `owner_node` and `created_by_user_id`.
- Solutions and deployments store `created_by_user_id`.
- Administrators may manage legacy records whose ownership is empty. Other users cannot take ownership of legacy records implicitly.
- Service approval remains separated from service publication: a Node Manager cannot approve a service from their own node.
- Destructive user-facing actions archive records rather than deleting them.
- Security and governance actions create immutable audit-event records.

## Session and password security

- Passwords use Python's standard-library `scrypt` password derivation with a unique random salt.
- The browser receives an opaque random session token. Only its SHA-256 digest is stored in PostgreSQL.
- Session cookies are `HttpOnly`, `SameSite=Lax`, scoped to `/`, and marked `Secure` in production.
- Sessions expire after 12 hours by default.
- Passwords require at least 12 characters, uppercase and lowercase letters, and a number.
- Signed-in users can change their password under **My account**. This revokes every active session and requires a fresh login.
- There is no public administrator-registration option.

## Initial administrator

Set the following only for the first authenticated startup:

```env
BOOTSTRAP_ADMIN_EMAIL=admin@institution.example
BOOTSTRAP_ADMIN_PASSWORD=<unique-password-from-password-manager>
BOOTSTRAP_ADMIN_NAME=Platform Administrator
SECURE_COOKIES=true
SESSION_HOURS=12
```

The bootstrap process runs only when no Platform Administrator exists. After the first successful administrator login, remove `BOOTSTRAP_ADMIN_PASSWORD` from the production environment and restart the API container.

## Existing-database migration

Before starting the new API image against an existing database:

1. Create and verify an off-server PostgreSQL backup.
2. Stop portal writes during the short migration window.
3. Apply `deploy/migrations/001_auth_rbac.sql` to the Solution Studio database.
4. Start the new API with temporary bootstrap-administrator variables.
5. Sign in as the bootstrap administrator and verify **Admin → User access**.
6. Remove the bootstrap password, restart the API and confirm the existing administrator still signs in.
7. Test registration, approval, all three roles and all four node boundaries.

The migration adds tables and nullable ownership columns; it does not delete or rewrite existing services, solutions or deployments.

### Preserving work created before login

Solutions, deployments and services created before this feature have empty ownership fields. They remain visible to Platform Administrators and are listed under **Admin → Data preservation**.

- Select the approved user who created an existing solution and assign it. Any still-unowned deployments linked to that solution are assigned at the same time.
- Assign an unlinked deployment individually when necessary.
- Assign each existing service to its German, Portuguese, Danish or Dutch node.
- Assignment is explicit, audited and limited to currently unowned records. It never deletes or recreates the solution, deployment or service.

Complete this ownership step before asking researchers to verify their personal workspaces.

## Production acceptance checklist

- Unauthenticated users can browse only the public catalogue and public dashboard.
- Pending, rejected and suspended users cannot sign in.
- A Solution Designer cannot publish a service or open the Admin area.
- A Node Manager can publish and manage services only for the assigned node.
- A Node Manager cannot archive another node's service.
- Non-administrators can see and manage only their own solutions and deployments.
- Only Platform Administrators can approve services and users.
- Suspending a user immediately invalidates their sessions.
- HTTPS is active and the session cookie is marked `Secure`.
- The legacy shared proxy Basic Authentication gate is disabled. Management
  pages and APIs rely on the portal session and role-based authorization, so
  users see only the portal login.

## Deferred enhancements

- Automatic email ownership verification after an SMTP/email provider is selected.
- Self-service password reset using time-limited email tokens.
- Institutional OpenID Connect or Microsoft Entra federation.
- Multi-factor authentication for Platform Administrators.
- Reverse-proxy login rate limiting and automated stale-session cleanup.
