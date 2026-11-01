# Design with AI staging candidate — 1 November 2026

**Prepared for review; integrated staging has not been deployed or accepted.** The known backend baseline failure is resolved through test fixtures, with write-time validation unchanged. No feature, screen redesign, new live experiment, profile, execution grant or allowance change is part of this consolidation.

## Candidate and actual release baseline

| Identity | Exact source or build |
|---|---|
| Portal application/migration validation source | `46f757fa31f86a3ae928d83bab799c0993e0b077` |
| Candidate application and prepared operations source | `da5b9540265697acd13bdc39921e5107a18c03f8` — identical `apps/` content to the validated source; adds staging boundaries/build exclusions |
| Backend source fingerprint, including all tests | `595feecd52c8299dbe0aa5c9c6ed4935e44faa32c0451dce5328ee73107fd72f` |
| Separate candidate web build | `Gy7DHenxjR0fhStkloYHm`, `.next-staging-candidate-20261101`; does not replace the running build |
| Maintained WP3 dependency, PR #3 | `0221b7ecd4a2d5f072de640350ebc599df22131a` |
| WP3 prerequisite, PR #2 | `6f6f16d36fd5bf7f5344451698f51c4bad171cb4` |
| Shared parameter validator SHA-256 | `1861736c1bd9c8a1e4d3aa86b1a2f58ef27bf5e272d682a619062cfb8b7171aa` — Portal and published WP3 bytes match |
| Actual GitHub **Production web** deployment | `7390379741`, success, source `70168fd14bfe4fe64229b16e1d75dbc1e419457d`, checked 1 November |
| Preserved local demonstration | application `d0568d89ea018e91c4af65c9b6a8833e321c1e58`, web `_9OUF0yBLv4pKPA0e0pex`, API `sha256:993302f295ac9feb511b448ea9730bf9aa6b64312841b43ac82b9a880a00cce8` |

Subsequent documentation-only commits on PR #13 package this record. Use the PR's exact recorded head for the review envelope; do not use a moving branch or tag as an operational pin. The machine [verification record](DESIGN_AI_STAGING_EVIDENCE_2026-11-01.json) identifies the tested sources and exact check categories.

The cumulative comparison used the actual Production web source above, **not just PR #12**. That source has four API tables and no portal authentication settings in `core/config.py`; it has no `docker-compose.prod.yml`. This candidate includes the intervening authentication/RBAC, onboarding, runtime/artifact, typed parameter, registry/binding, persistence and usability work. The later `feature/production-ui-polish-v1` head `df5b75873326ab56cad608990f3bd4add125bcc4` is **not** already integrated into that Production source. PR #7 was merged from an earlier head, `56b4505fe2138d235bfa9e7b3f7aee736000f544`. Those prerequisites require review too.

**Production web metadata does not identify the currently serving integrated API/WP3 server.** The older `evpa-uat` production acceptance/runbook is historical evidence, not a fresh server inventory. Current server source, private configuration, schema/migration level, image digests, storage and runtime capability declarations remain unverified. A read-only inventory/connection record was requested; none was available during this consolidation. No production environment contents were read or changed. The synthetic migration rehearsal below does not substitute for that inventory.

The existing PR heads/bases and all other local checkouts were inspected. The original dirty checkout and its local changes were preserved; no source was copied out of that dirty tree. No branch was rebased, force-pushed, merged, deleted or reset. Only the existing PR #13 review branch receives these focused commits.

## Corrected tests and necessary rollout fixes

The old missing-service test tried to POST an invalid new solution and expected 200 to manufacture a later load error. `create_solution` and `update_solution` call `validate_builder_configurations` before any mutation; catalogue resolution deliberately raises the actionable `solution_service_missing` 409. The authenticated load path checks ownership before hydration. The contract is retained.

Focused commit **`125191d`** separates the cases:

- New invalid creates and updates are rejected with the exact error code, service IDs, message and recommended action. Existing solution fields, timestamps and audit counts remain unchanged; another owner cannot update the solution.
- The historical broken solution is inserted only into the suite-allocated test database with an actual authenticated designer owner. Its owner receives the actionable load-time 409; a different designer receives ownership denial first. Loading changes neither the row nor audit count. The fixture removes its solutions, sessions, users and audit records.

A later focused invocation exposed a separate ZIP fixture timing problem: two newly generated ZIPs can carry different timestamps/digests and therefore different proposed IDs. Commit **`46f757f`** reuses the exact archive bytes for the repeat-upload case and additionally compares all original service columns after the rejected repeat. An earlier failed invocation remains a pre-final finding; it is not counted as a pass.

The same commit adds **`005_local_capture_records.sql`** and its PostgreSQL regression. Previously the local capture table depended on `create_all` at API import, with no explicit release migration. The additive migration creates its existing model shape/indexes without copying evidence or changing any guard. Reapplication preserves history.

Commit **`da5b954`** excludes private `local-backups`, `local-secrets`, environment/build caches and SQLite state from Docker context, and prepares an isolated staging compose/gateway boundary. No new application behavior is enabled.

## Final checks newly run

| Check | Actual result |
|---|---|
| Complete portable API inventory, `apps/api/tests` | **284 passed**, 0 failures/errors/skips |
| Complete PostgreSQL legacy API inventory, `apps/api/app/tests` | **94 passed**, 0 failures/errors/skips |
| Complete dedicated PostgreSQL inventory, `apps/api/postgres_tests` | **14 passed**, 0 failures/errors/skips |
| **Complete Portal backend total** | **392 passed**, no exclusion or skip; same final backend fingerprint in all three isolated processes |
| Complete frontend inventory, all 10 `app/components/lib` test files | **39 passed**, 0 failures/skips |
| TypeScript / Next 16.3.8 webpack production build | **Passed / passed**; Python 3.12.14 and Node v24.15.0 were used for host checks |
| Exact published WP3 PR #3 complete unit inventory | **317 passed**, 0 exclusions/skips; HTTP/fakeredis doubles, network disabled |
| Synthetic migration and backup/restore rehearsal | **Passed**; baseline schema generated from actual Production web commit's models; all five migrations applied and reapplied; every candidate model column/type matches; synthetic original rows preserved |
| Prepared staging compose and nginx boundary | **Passed** syntax and network-disabled mock-upstream checks; five prohibited POST routes return 403, normal mock auth proxy returns 204 |
| Secret scan / diff check | **Passed** cumulative 51-commit range from Production source through operations source; 1.67 MB scanned; existing two exact local-image-tag exceptions unchanged; whitespace checks passed |
| Preserved state | Other worktrees, both evidence/profile engineering databases, original acceptance/correction, captured files, checkpoints and ledger unchanged; four original downloads still hash-match and require authorization |

The full backend inventory ran **once on the final application/migration test source**, in separate processes because the SQLite and PostgreSQL harnesses deliberately cannot share cached application modules. Later changes are operations/docs only; `apps/` is byte-identical. Existing datetime/FastAPI deprecations and Node's typeless-module warning remain visible. No failure is suppressed. The earlier 369-pass/one-failure and focused 111-pass records remain historical; they are not presented as these newly run checks.

WP3 tests used only the installed dependency image `sha256:0cf40e15edc3508d26f907fc7619980d47f31f16b9ddf7be4429c832db717f06`, with the **published PR #3 source mounted read-only** over the test import path, writable disposable files and `--network none`. This is not a claim that that older image was rebuilt from PR #3 or is the final staging runtime. No worker, Redis work queue, algorithm or real workflow was invoked.

The migration rehearsal allocated two random `staging_rehearsal_*_test` databases on the existing local cluster, generated only synthetic old-style rows, performed `pg_dump -Fc`/`pg_restore`, applied 001–005 twice and checked row/column/type equality. Both allocated databases were removed. The first verifier rejected equivalent SQLAlchemy timestamp representations; only its type comparison was corrected before the successful rehearsal. No production or existing evidence database was migrated or restored.

## Cumulative risk review and ranked blockers

| Priority | Finding and disposition |
|---|---|
| **1 — integrated baseline** | Current production API/WP3/configuration/schema/image/storage identities are unknown. Obtain a read-only owner-supplied inventory and compare it with these sources before approving any integrated staging connection or migration. Do not treat the Vercel web deployment as that inventory. |
| **1 — qualified scope** | `qualified_demo.profile_enabled` explicitly requires the local qualification database identity and isolated orchestrator URL. The existing capture adapter also requires pinned Dutch images, operations, endpoints and manifests. A new normal staging database must **not** be renamed to impersonate that profile. The complete demonstrated goal-to-results execution/capture journey is not a deploy-anywhere feature. Agree a separate reviewed staging qualification plan before enabling it; do not broaden guards in this PR. |
| **2 — unmerged prerequisites/review** | The stack starts on a feature branch containing authentication, ownership, onboarding and operational changes absent from current Production web source. Review that cumulative base and its migration/legacy-owner policy before the ordered stack. Draft/Preview success does not approve these changes. |
| **2 — shared artifact boundary** | The qualified results/download routes check deployment ownership before reading and revalidate artifact hashes/associations. The inherited generic `/data-references/preview` requires sign-in but accepts references without per-workflow ownership. Prepared staging blocks it and mounts no shared artifact volumes. A shared integrated release needs a separate ownership/egress decision or narrower repair before reopening that route. |
| **2 — build/config reproducibility** | Web dependencies are locked; generic Python requirements and Docker base tags still float, and the host web checks used Node 24 while the generic Dockerfile names Node 22. No new dependency versions were installed or silently pinned. Owner must select immutable build bases, retain a resolved Python dependency manifest, build/import candidate images from these sources and record their digests before provisioning. Existing demo image IDs are preservation evidence, **not staging image defaults**. |
| **2 — remote access checks** | #8–#10 still have Vercel failures: **“Git author adarshsunil must have access to the project on Vercel to create deployments.”** The Vercel project owner must grant that linked GitHub author deployment access to `ai-effect-solution-studio` in `cammardella17-7147s-projects` (team `team_atCBn1XywvEITw7mpJXE2VxE`), then rerun/redeploy those original checks through Vercel. Do not amend attribution or bypass required checks. #11–#13's inspected heads had successful Vercel Preview status; this is not integrated staging acceptance. |
| **3 — independent acceptance** | Independent usability is still unverified. Broader composition, scientific/KPI validity, all-country runtime qualification and production compatibility are incomplete. Use the existing unfilled participant/observer materials; invent no observations. |

Parameter review: registry-owned immutable contract/version and exact shared validator are authoritative. Parameter transport requires advertised compatible runtime checks; stale versions/digests or unrecognized capabilities fail closed. Optional unconfigured legacy workflows preserve their earlier path; this is not universal parameter support. Configured Save/submission locks check expected revisions, contract state and immutable request identity. No historical setting is reconstructed from editable designs.

Submission review: the qualified journey records an owned attempt before dispatch, serializes a single grant claim across copies and preserves unknown outcomes without redispatch. These guarantees are local to that journey; they are not distributed exactly-once or global retry protection for every legacy submission route. The prepared gateway denies both real legacy submission and qualified execution routes.

Evidence review: terminal observations, workflow/submission/task/node identities, generator consumption and benchmark input are independently checked. Historical files and associations are revalidated on inspection/download; unavailable, pending, inaccessible, conflicting and invalid states remain distinct. Protected downloads use attachment/no-store/nosniff/sandbox headers. No cached completion or lone valid artifact certifies every task.

## Prepared staging configuration — not deployed

[Compose](../deploy/staging/compose.yaml) and [gateway](../deploy/staging/nginx.conf) are a **closed preparation baseline**, not a ready integrated demo. There are no default images, passwords, project name, port or WP3 endpoint; required values must be owner-selected. `pull_policy: never` prevents an implicit image update. Nothing from a local profile is imported.

- Select a new project name and new volumes/accounts/secrets. Generate a fresh URL-safe database password for the prepared connection string and protect the private environment file. Never use production/demo project names, database volumes, credentials, ledgers or evidence directories. Use a distinct staging HTTPS origin so existing localhost sessions cannot be confused with staging accounts.
- Supply immutable API/web/WP3/build dependency identities; never `latest` or the local qualification profile's container names. Web build must resolve `/api` to `http://api:8080`; verify its rewrite manifest before starting it. Public Vercel Preview renders only the web build and is not a substitute for that private API route/database/runtime.
- Only the gateway has a host binding, explicitly loopback. API, web and PostgreSQL have no published ports. The private network is internal. **No WP3, algorithm or worker is provisioned by this file.** An owner-approved staging WP3 service/alias would have to join a new dedicated network; do not attach existing production/demo services or networks to make it work.
- Before a later start, configure owner-managed HTTPS in front of the loopback gateway. Cookies remain `Secure`, HttpOnly and SameSite Lax; do not relax them just to use plain HTTP. Bootstrap a fresh staging administrator only after provisioning is separately approved, then remove bootstrap values and recreate only that staging API.
- All AI/qualification flags are false; templates are empty; provider key, ledger/checkpoint paths, capture roots and execution-grant path are blank. Do not copy a local `.env`, grant, provider key, capture or credential file into staging.
- The gateway explicitly denies `/api/design-ai/chat`, `/api/design-ai/drafts/*/execute`, both workflow submission routes and the generic reference-preview route. Denial was tested against a mock upstream without any provider/runtime network. These guards remain in place until a separately reviewed acceptance permission and appropriate application/runtime qualification exist.

With owner-generated **staging-only** values in a private environment file, the reproducible pre-deployment syntax check is:

```text
docker compose --env-file <private-staging-only-env> -f deploy/staging/compose.yaml config --quiet
```

This document does not authorize `up`, infrastructure provisioning, network attachment, profile recreation, publishing localhost or replacing any running application. No integrated staging URL has been created.

## Migration order, backup and rollback

1. Establish actual schema/runtime/configuration baseline first. Use an isolated database/schema clone approved for staging, with synthetic data by default. **Never use existing local evidence databases as rehearsal targets.** Audit row counts, legacy null owners, constraints and extensions. Have the owner approve the legacy ownership policy; migrations do not guess owners or bulk-assign historical records.
2. Quiesce only the approved staging writers and make a PostgreSQL custom-format backup plus a storage/configuration/image manifest. Rehearse restore into a second disposable database and compare rows before migration. Keep artifact volumes and database snapshots associated; never overwrite the successful local run's files.
3. Using a private PostgreSQL service entry for the **staging database**, apply, with `ON_ERROR_STOP=1`, in order: **001 authentication/ownership**, **002 Dutch node normalization**, **003 AI drafts/design metadata**, **004 immutable submissions/receipts**, **005 local capture records**. Do this before starting the new API; `create_all` is not an existing-column migration tool. For example: `psql "service=design_ai_staging" -v ON_ERROR_STOP=1 -f deploy/migrations/001_auth_rbac.sql`, then each subsequent file in order. Check migration hashes against the chosen commit and compare counts/constraints. The node normalization changes only `netherlands`→`dutch` in its declared fields.
4. New tables/columns are additive. Contract parameter/binding extensions remain JSONB; absent declarations remain legacy rather than being filled with invented defaults. Retain original submitted snapshots, digest receipts, terminal observations and all new history when disabling features or rolling back an application.
5. For application rollback, keep traffic/writes stopped, restore previous **authenticated, compatible** API/web/WP3 image/configuration identities, and leave additive tables/columns intact. Do not expose an older unauthenticated app to a newer private dataset or automatically drop tables to satisfy it. Verify compatibility in disposable data before using an older binary.
6. If a genuine data rollback is required, restore the verified backup to a **separate** database/volumes, reconcile any newer writes/history and obtain owner approval before switching that staging connection. Preserve the original database for reconciliation. Do not roll back by deleting immutable evidence, ledger records or execution claims. Production rollback/cutover is outside this approval.

For reproducibility, a source-only export is `git archive --format=zip --output=<private-output>/portal-candidate.zip da5b9540265697acd13bdc39921e5107a18c03f8`; export WP3 `0221b7ecd4a2d5f072de640350ebc599df22131a` separately. Build images only after the immutable dependency/build inputs have been approved; record final image digests and runtime capability/contract hashes in the staging inventory.

## Short future staging acceptance, permissions pending

After owner-approved isolated provisioning and successful migrations: verify HTTPS login/session/logout, designer/admin ownership boundaries, empty/new-only data and disabled AI/grants; verify anonymous and cross-owner result/download denial with synthetic fixtures, plus submission/chat gateway denials. Create/read/edit a synthetic manual design only within the approved new staging data, and check stale-write/invalid-reference rejection without partial mutation. Check saved contract pins and read-only readiness/capability endpoints against the separately approved exact WP3 source/runtime; no workflow or algorithm invocation is a health check. Keep the generic reference route closed until its separate ownership decision is resolved.

A paid provider request, new execution grant, allowance amendment or workflow/algorithm acceptance is **not approved** by this preparation. Any future integrated goal-to-results test needs a separately bounded owner authorization, supported staging qualification and explicit stop conditions. Independent usability requires a real participant and completed observer notes; the original local run cannot stand in for a fresh staging run. Production compatibility remains unverified.

## Review/merge order and completion map

First review the cumulative `feature/production-ui-polish-v1` prerequisites against actual Production source; PR #7's old merge does not include that later head. Then, only after future merge authorization: **Portal #8 → #9 → #10 → #11 → #12 → #13**. Maintained **WP3 #2 → #3** must be reviewed/available before enabling Portal #9 parameter transport or later dependent runtime acceptance. No automatic squash, merge or history rewrite is prepared.

After each approved lower merge, confirm its changes are actually in the intended target; retarget the next dependent PR onto that target, review the newly computed diff and rerun checks required by any merge result. If squash merging removes ancestry, stop and reconcile the stack explicitly rather than silently rebasing or duplicating commits. All PRs remain draft/In Review; no retarget was performed here.

The canonical [current review-readiness table](DESIGN_AI_GOAL_TO_RESULTS.md#current-review-readiness) records delivered scope, evidence, remaining acceptance and recommended status for AIE-18/37/38/40/41. No tracker status was changed.

The preserved workflow is `wf-1b6eb7caaf57`, saved solution `ef10cde8-15d4-4f6d-82dd-0525a16de4fd`, seed **43**, both tasks completed. [Its existing results](http://localhost:23121/deployments/wf-1b6eb7caaf57#results) and four downloads remain accessible. Original acceptance failure and separate correction records remain unchanged. Provider and execution grants are disabled; the shared ledger is unchanged at **13/13**, zero outstanding reservations, **zero new requests/executions**. No staging/production deployment, merge, infrastructure provisioning, tracker update or independent-usability claim occurred.
