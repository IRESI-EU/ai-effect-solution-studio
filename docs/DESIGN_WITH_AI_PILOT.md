# Gated Design with AI foundation

The opt-in pilot creates designer-owned, revisioned drafts from operator-approved
saved templates. A private MCP connection exposes inspection, proposal validation,
Apply, Undo and explicit Save; it exposes no workflow deployment tool. Requests
carry bounded approved context. The server validates model output and ownership
before displaying a proposal; receiving a proposal does not mutate the draft.

Enable only in an isolated development profile with the normal server-side
DESIGN_AI_* settings. Keep provider credentials outside Git. The persistent local
acceptance allowance is a fail-closed test guard, not a billing service. It never
automatically replenishes or retries requests. Real-provider tests require their
own explicit authorization; unit tests use provider fixtures and disposable data.

## Review dependency

Base: the existing published `feature/production-ui-polish-v1` line, which supplies
authentication/ownership, package onboarding, runtime readiness and the versioned
operation registry. This branch includes the unpublished pilot prerequisites from
local commits af72cd2, f4409e5, 63457d1, 64a472d, 320c4cd and 12aae82, consolidated
from their exact source files. Original commits/checkpoints remain untouched.
Raw local runtime reports, screenshots, private configuration and operator backups
are intentionally excluded; they are not portable implementation dependencies.

## Offline verification

Install apps/api/requirements.txt plus the existing test/acceptance requirements.
Set PYTHONPATH=apps/api and run `python -m pytest apps/api/tests -q`.
The portable suite uses SQLite fixtures and mocked provider/HTTP boundaries;
it does not verify PostgreSQL locking or invoke a paid model. The separate
apps/api/postgres_tests suite creates its own local random test databases when
explicitly supplied TEST_DATABASE_URL. Never point it at a preserved pilot database.
Use the web workspace's typecheck/build and Node utility tests for UI changes.

No production compatibility, independent usability or new algorithm execution is
claimed. Keep rollout disabled pending review. The module/composer PR is stacked
on this foundation; it supplies its own sanitized scope and test provenance.

Publication checks: 51 portable API tests and 5 web utility tests passed; TypeScript
passed; the Next 16 production build passed in supported webpack mode. Default
Turbopack rejected this isolated worktree's shared dependency junction; no product
configuration was changed to hide that environment limitation. Gitleaks staged
scan passed after an exact annotation of a known disposable test-login fixture.
