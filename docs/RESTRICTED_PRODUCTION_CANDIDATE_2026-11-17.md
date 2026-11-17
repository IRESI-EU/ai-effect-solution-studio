# Restricted design-only beta: prepared candidate, activation blocked

**Built and tested locally; not deployed or approved for cutover.** Target A is
restricted design review for selected existing users. Portuguese execution and
any WP3 runtime upgrade are excluded. No production restart/migration, worker
change, provider call, budget amendment, algorithm, merge or account change occurred.
The original [assessment](PRODUCTION_RELEASE_READINESS_2026-11-17.md) remains historical.

## Fresh production baseline versus historical records

Read-only inventory used the recorded authorized SSH deployment connection on
17 November at **08:38:28 UTC**. Raw operational records remain private in the
original checkout's `local-backups/release-preparation-20261117`; no environment,
account/session rows, database contents, credentials or private paths are published.
[Sanitized inventory/package/migration/stack record](../deploy/release/PREPARED_CANDIDATE_2026-11-17.json).

| Component | Observed image/source/build | Difference from historical record |
| --- | --- | --- |
| Production API, healthy | `sha256:ded4f325be3769f834f5a40b1e3cf7f85aef0e0d25126b51d9509892cd562340`; all44 runtime Python files match `89072340c9a13f3aa49d3e433380de8928cc16dd` | Same image; source independently checked by complete runtime Python hash comparison |
| Production web, healthy | `sha256:851115fb98582c8c077ed28e3b6db46c40a1079467cb4e3a11faabf5c19f2a0f`; BUILD_ID `aLp4c1xkUjCM1v23PtrYY` | Same immutable image historically attributed to `df5b75873326ab56cad608990f3bd4add125bcc4`; no source label, so that attribution is not a fresh source-label observation |
| Production PostgreSQL, healthy | PostgreSQL16.15; `sha256:81bd698b4594e751a3269e4dcd3e03a4a0ec0daf7b72e7aa1abd43cce9887542` | Current schema observed; no production migration applied |
| Existing orchestrator | `sha256:15ebcb7261be2dd7b0a3a55b5b65953dcfa8a132c0dad46fcbf8fbd0830069cc` | Source label unavailable; do not attribute maintained WP3 tip to this image |
| Three existing running production workers | `sha256:759ed98555799d3e73cfa55be4f72544deb9046b0af412a2f5659c9b56723d28` | Inspected only; not stopped, restarted or upgraded |

There are39 retained server containers. Portal configuration hashes, mount/network
identities, states and source comparisons are retained privately; only hashes
appear in the sanitized record. Server root filesystem has82GiB available.
Verified public HTTPS `/login` and `/api/health` both return200. Certificate
SHA-256 `1dc34f96aabec02b9b4fbe3505dd5e6f77d52ea3c88feadf8bb90e140d256562`,
Let's Encrypt YR1, valid through17 December2026 10:18:52UTC. The running web's
Traefik labels identify the public platform/legacy-alias catch-all, auth-API,
public catalogue/health and management routes. Host nginx is inactive; no nginx
restart is appropriate. The management rule currently names admin/builder/publish/
deployments/solutions/API paths, but not `/design-ai`. Before cutover, the operator
must confirm intended middleware/priority coverage for this new path and retain
the complete current private Compose/ingress override chain. No routing was changed.

**Normal existing-account sign-in is unperformed.** The earlier failed temporary
credential was not retried. The owner must identify a valid existing reviewer
account and sign in normally; no password reset, account creation or ownership
assignment is proposed in production.

The current database has31 users,37 services,49 solutions,55 deployments,
494 audit events and99 sessions; **zero operation contracts**. Ownerless records:
16 services,2 solutions,1 deployment. They remain untouched. New ownership is
not inferred from historical names or paths. Legacy previews lacking immutable
submission/task/file association remain unavailable with a reason.

## Exact locally built candidate

Application/build source **`349f45166f319c040b2b3f2b98c4cefb9b537aa3`**, layered above
the documentation-only assessment `1f30b18859231e0a2acf269eb487661a80e99b0f` and
reviewed handoff `c0b9405657a3c64ba2b570cecb3c973ba1bcfb7e`.
These are new packages, not relabelled sandbox or production images.

| Package | Local immutable content identity |
| --- | --- |
| API `ai-effect-beta-candidate-api:349f45166f31` | `sha256:29a48dae5efceac7fbab0b151909803a70ccec74843159b3fbe2349d55ea6e67` |
| Web `ai-effect-beta-candidate-web:349f45166f31` | `sha256:57cf29da97ab875de93e78fa2068551ba6c44062233358de410a82c490ddc6c0` |
| Web BUILD_ID | `EY9BALGRvOJYRAkWG_pgJ` |

These are local image/config digests, not registry-published manifest digests.
Platform linux/amd64; Python3.12.14, Node24.15.0/Next16.3.8. Existing pinned
dependency images, base digests, lock hashes and every included source-file hash
are in the [build source manifest](../deploy/release/BUILD_SOURCE_MANIFEST_2026-11-17.json).
The existing restricted-beta packager exported tracked allowlisted sources only,
built with `--network=none --pull=false`, and retained old tags/images. No dependency
upgrade, private configuration, datasets, credentials, captures or local-backups
entered the build context. No WP3 image was built or selected for deployment.
Maintained WP3 review remains `d533219426af9ea6defaf0bc78956741201a5109`.

Both packages passed network-disabled import/metadata checks; API defaults have
provider/registration OFF. The web production build passed with19 packaged
frontend checks. Host typecheck and20 focused frontend checks passed. Existing
serving sandbox API/web/sidecar images were not replaced.

## Narrow implementation and remaining registration gate

`RegisteredParameters.deployment_design_input` adds an optional explicit target
environment, PostgreSQL host/port/database/role fingerprint, opaque CSV reference
and label. Existing reviewer ID, owned source revision, exact two service IDs,
active0.2.0 contract pins and full definition hashes remain mandatory. The target
environment setting defaults empty. The sandbox guard and its reviewer/CSV
configuration are unchanged; copying sandbox policy to another DB does not work.
The existing registration operator prepares this record read-only; it creates
no service, contract, data, source design, permission or execution grant.

Example **future preparation only**, using owner-selected target data:

```sh
python -m app.services.registered_parameters_operator \
  --reviewer-id "$EXISTING_REVIEWER_ID" --source-id "$OWNED_SOURCE_ID" \
  --registration-id "$TARGET_REGISTRATION_ID" \
  --design-environment "$TARGET_ENVIRONMENT" \
  --dataset-ref "$APPROVED_OPAQUE_DATASET_REF" --dataset-label "$PUBLIC_INPUT_LABEL"
```

Run against the target with `DESIGN_AI_REGISTRATION_ENVIRONMENT` set to the same
reviewed value; the operator computes its actual DB fingerprint. Do not substitute
the Windows reviewer/source/CSV or rename the DB. Keep the output private until
reviewed. Its explicit installation is outside this preparation pass.

The normal authenticated training-input endpoint exposes only that reviewer's
currently authorized label/reference, rechecking source/service/contract authority.
Wrong owner, stale pins/source/environment/database or unapproved input fail.
No files/storage/provisioning service or upload subsystem was added.

Outside the original sandbox, the exact experimental service family is denied
server-side **before** runtime probing/enqueueing, even without solution ID or
after removal of target registration. New registered copies retain a protected
design-only metadata policy through Save/Builder. UI inspection policy applies
only to those service IDs; unrelated existing workflows retain their behavior.
The generic native composer still excludes sidecars/external inputs.

**Activation remains blocked:** production has no active contracts, no owner-selected
reviewer/owned source and no approved target CSV registration. The fixed experimental
service IDs/0.2.0 definitions are the proposed review family, not owner attestation
or an assertion that those services are already eligible in production. The owner
must approve this exact family/input and arrange normal reviewed target registration,
or explicitly choose a different candidate scope. Nothing was published/activated
in the production catalogue to manufacture eligibility.

## Inactive configuration and accounting

[Production overlay](../deploy/release/restricted-beta.compose.yaml) and
[private-value template](../deploy/release/restricted-beta.env.example) default
AI OFF, restricted reviewer list empty, templates empty and provider/token empty.
Bootstrap credentials are explicitly empty. Existing production networks, mounts,
ports and orchestration remain inherited; only API/web image selection changes
in a later approved installation. Compose configuration validation passed with
synthetic placeholders; no services were created. Private audit FileHandler is
mounted at `/acceptance-audit`, with a dedicated owner-private directory writable
by UID10001. No credentials/authorization headers/raw payload are required in logs.
The new capture is in both the candidate source and built API image.

The original accounting batch is **28/28 permanently closed**, with zero outstanding
reservations; it is historical evidence, not production capacity. Current supported
phase transitions end at25→28 and refuse closed global state. Client URL/private
socket, authority ID, consumer/environment/DB fingerprint and fail-closed outage
behavior are reusable; historical credentials/CA/permits are not a production plan.
No copy, reopen, replacement ledger, new funds or amendment was made.

The smallest remaining accounting proposal is a **separately reviewed production
budget lifecycle policy using the existing authority/client**, with explicit
canonical host/storage identity, operator attribution, environment/DB binding,
call/money ceilings, concurrency/uncertainty rules and an approved way to create
new capacity while leaving the historical batch closed. Current code has no
supported production-capacity activation operation. Owner selection of budget
and authority placement plus that narrow operator implementation/review are
required before any live chat. This report does not select funds or authorize it.
On missing/partial/outage accounting configuration, no provider dispatch occurs.

## Observed-schema migration, backup and rollback plan

001 auth/RBAC and002 node rename effects are present in current schema. Read-only
aggregate follow-up found zero legacy `netherlands` users or service owner-node
values. Solutions
lack design_metadata; design_ai_drafts, execution_submissions/evidence receipts
and local_dutch_executions are absent. **Only003,004,005 are required** for this
candidate. Never rerun001 to bootstrap accounts or use create_all as a migration.
Current schema-only snapshot SHA-256:
`2f0ea70bdf430b0611b37d11fd3d76b5b1fa37101888a1cb30669975bc3a2488`.
Exact migration hashes are in the sanitized preparation record.

Actual rehearsal imported that observed DDL into two uniquely named disposable
local PostgreSQL databases, populated synthetic owned/ownerless rows, created a
20,802-byte custom backup, restored into the second DB, applied003–005 twice,
checked all old projections and retained a new metadata write. Both disposable
DBs were removed normally; no retained DB contents were copied. Old projection
comparison was normalized by ID after an initial row-order-only assertion failure.
**Full old-binary rollback and real production backup/restore were not rerun.**
An earlier private production dump remains historical; inventory does not make
it a current rollback point. A fresh consistent backup is a later cutover prerequisite.

Future operator sequence, **not executed here** (use current recorded container
identity, DB/role and private backup destination; never print passwords):

```sh
# After separately approved maintenance/write window and a fresh verified backup:
docker exec "$PG_CONTAINER" pg_dump -U "$DB_ROLE" -d "$DB_NAME" -Fc > "$PRIVATE_BACKUP"
# Restore verification is always a separate, explicitly disposable database:
[ "$FRESH_RESTORE_DB" != "$DB_NAME" ] || exit 1
docker exec "$PG_CONTAINER" createdb -U "$DB_ROLE" "$FRESH_RESTORE_DB"
docker exec -i "$PG_CONTAINER" pg_restore -U "$DB_ROLE" -d "$FRESH_RESTORE_DB" --exit-on-error < "$PRIVATE_BACKUP"
# Apply only the observed missing additive migrations; verify each hash first:
docker exec -i "$PG_CONTAINER" psql -X -U "$DB_ROLE" -d "$DB_NAME" -v ON_ERROR_STOP=1 < deploy/migrations/003_design_ai_pilot.sql
docker exec -i "$PG_CONTAINER" psql -X -U "$DB_ROLE" -d "$DB_NAME" -v ON_ERROR_STOP=1 < deploy/migrations/004_instance_submissions.sql
docker exec -i "$PG_CONTAINER" psql -X -U "$DB_ROLE" -d "$DB_NAME" -v ON_ERROR_STOP=1 < deploy/migrations/005_local_capture_records.sql
# Only a later approved API/web update; never include worker/DB services:
# PROD_COMPOSE_ARGS is the complete recorded current private -f/--env-file chain,
# including existing ingress/auth overrides; do not substitute repository defaults.
docker compose "${PROD_COMPOSE_ARGS[@]}" -f deploy/release/restricted-beta.compose.yaml --env-file "$PRIVATE_RELEASE_ENV" up -d --no-deps --no-build --pull never api web
```

Keep the actual old API/web images and original private config. On a later code
rollback, disable the new AI controls, restore **only** those API/web pins/config,
and use the same no-deps/no-build/pull-never command. Retain additive schema and
new writes; never restore an old DB over newer production activity. A data restore
needs a separate approved recovery operation. Do not touch current workers.

## Explicit staging adaptation and acceptance gate

The previously selected destination remains this Windows Docker Desktop host,
loopback HTTPS on the independently proposed24443 port, separate new project,
database, volumes and credentials. No provisioning, certificate trust, profile
creation or service start occurred. Recheck port availability immediately before
any later approved provisioning; do not reuse23121/23123/23124 or their storage.
The existing `deploy/staging/compose.yaml` retains internal networks, TLS/Secure
cookies and disconnected orchestration. Apply the explicit
[design-only override](../deploy/release/staging-design-only.compose.yaml) and
[staging-only gateway](../deploy/release/staging-design-only.nginx.conf) for this
candidate: controls can be enabled for exact staging reviewer/registration metadata,
and chat reaches normal authenticated disconnected-provider/accounting denial.
Submission, readiness, execution, runtime verification and generic artifact-preview
gateway denials remain. Never copy this gateway unchanged to production: it would
block existing supported production execution and previews.

Future compose selection: `-f deploy/staging/compose.yaml -f deploy/release/staging-design-only.compose.yaml`
with a new private environment file, exact built API/web IDs, separately retained
PG/gateway IDs and absolute TLS/gateway paths. Do not rerun the old hardcoded
local_review activation/bootstrap flow blindly: its AI-off verification belongs
to the earlier scope. Use existing isolated synthetic seed only for new staging
accounts/data, with controls still OFF; install reviewed target registration
after existing IDs/source/pins are known. There is no production fake-provider
fallback. Provider-double tests use dependency overrides confined to tests.

Retained staging inputs were rechecked locally: PostgreSQL
`sha256:5d143123fdf80462d1778cd4f24b9f7ca13c87174bca19141fb194c5a1ebca59`
and gateway `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`,
both linux/amd64. No listener was found on24443 at preparation time.
The explicit override mounts the existing synthetic seed script read-only because
the new restricted-beta API image deliberately does not bundle staging bootstrap.

After separate staging approval and private TLS/new-credential preparation,
from the Portal checkout in PowerShell (not run in this pass):

```powershell
$stageArgs = @('--context','desktop-linux','compose','--env-file',$privateStageEnv,
  '-f','deploy/staging/compose.yaml','-f','deploy/release/staging-design-only.compose.yaml')
# Private env must name a fresh project/storage, exact four images, loopback24443,
# TLS directory, REVIEW_DESIGN_GATEWAY_CONFIG and REVIEW_SYNTHETIC_SEED_FILE.
docker @stageArgs config --quiet
docker @stageArgs up -d --no-build --pull never postgres
# Wait for this new database's pg_isready. Initialize only its four core tables,
# then apply001–005 for a genuinely fresh staging schema (not to production).
docker @stageArgs run --rm --no-deps --pull never api python -c "from app.db import Base,engine;from app.models.service import Service;from app.models.solution import Solution;from app.models.deployment import Deployment;from app.models.operation_contract import OperationContract;assert engine.url.database=='design_ai_staging' and engine.url.host=='postgres';Base.metadata.create_all(engine,tables=[Service.__table__,Solution.__table__,Deployment.__table__,OperationContract.__table__])"
Get-ChildItem deploy/migrations/*.sql | Sort-Object Name | ForEach-Object {
  Get-Content -Raw $_.FullName | docker @stageArgs exec -T postgres psql -X -U staging -d design_ai_staging -v ON_ERROR_STOP=1
}
# Controls OFF during new-only synthetic seed; private bootstrap env only.
docker @stageArgs run --rm --no-deps --pull never api python /opt/staging/synthetic_seed.py
# Clear bootstrap passwords; install separately reviewed staging-only registration.
docker @stageArgs up -d --no-build --pull never api web gateway
# HTTPS entry: https://127.0.0.1:24443; use explicit local CA validation, never -k.
# Backup/restore only into a fresh design_ai_staging_restore_<timestamp> DB.
docker @stageArgs stop gateway web api postgres
```

Do not trust a certificate, allocate storage or run this sequence without the
separate staging decision. No production/source designs or sandbox data are used.
Use the acceptance matrix below rather than the old helper's chat403 expectation;
chat now reaches normal authorization/disconnected-provider denial. Failed
registration/accounting must not be repaired by inserting a synthetic production
catalogue or enabling a runtime. Roll back only staged API/web pins; retain new
staging data and inspect any restored backup as a different database.

| Required staging acceptance | Expected evidence / stop condition | This pass |
| --- | --- | --- |
| Login/session/logout, roles | Secure cookie over trusted HTTPS; existing-account identity and wrong-role denial; no password reset | Public production pages/TLS checked; authenticated journey unperformed |
| Catalogue/publishing | Synthetic role-owned draft/approval lifecycle; unauthorized publication denied; existing catalogue unchanged | Must run after approved staging provisioning |
| Saved workflows | Old/new/ownerless synthetic records remain; owner checks; null metadata/input and stale-save behavior explicit | Focused offline persistence/ownership tests pass |
| Monitoring/downloads | Owner/workflow/task/file association and hashes; cross-owner/remote-path denial; legacy missing association truthfully unavailable |13 focused owned-preview cases pass; production downloads unperformed |
| Restricted AI controls | Owner-approved target registration; independent IDs; parameters, required CSV, pins/binding; Apply/Undo/reapply/Save/Builder |9 target portability cases pass with offline route fixtures |
| Provider/accounting outage | No SDK dispatch or fallback; unresolved usage holds; metadata unavailable stays null; private capture |47 focused capture/accounting/configuration cases pass, provider doubled |
| New experimental execution | UI design-only, server denies preflight/submission before runtime/queue; policy removal/omitted solution ID cannot bypass; unrelated services preserved | Target/retained-sandbox regressions and scoped UI helper checks pass |
| Migration/restore and code rollback | Observed schema003–005 only; independent restore; old rows/new writes retained; exact old API/web binaries | Synthetic DB rehearsal passes; full binary rollback unperformed |
| Human usability | Colleague performs existing ten-minute guide; actual observations only | READY, NOT YET PERFORMED; sheet remains blank |

Target registration tests cover9 new cases plus65 existing registered/chain/
supervision cases. After corrections,71 passed in the broader run and the3 affected
endpoint cases passed separately;13 preview cases also passed.47 capture/accounting/
config checks and20 host frontend checks passed;19 packaged checks/build passed.
These are focused checks, not a claim to have rerun every backend suite or to
establish PostgreSQL request concurrency or production compatibility.

## Full review stack and remaining owner actions

Portal chain **8→9→10→11→12→13→14→15→16→17→18→19→20→21→22** starts from
`feature/production-ui-polish-v1`, not a presumed already merged main. WP3
**2→3→4** starts from the base recorded in the machine manifest. Every exact
head/base SHA and branch is in that record; immediate bases match predecessor
heads. Review cumulative API against8907234 and web againstdf5b758 independently.
No bulk merge, retarget, rewrite, reviewer invitation or self-approval occurred.
All18 PRs remain drafts; no submitted reviews were observed.

Refreshed branch lists mark the stack base branches unprotected; visible repository
rulesets are empty. No enforced required-check list was returned by these APIs.
This is not permission to bypass checks or a claim about inaccessible organization
policy. PR8–10 retain Vercel failures linked to a team invitation/project-author
access issue; Preview Comments success is a different check. The Vercel project
owner must authorize the existing Git author/project access and rerun applicable
checks without rewriting attribution. Later Vercel successes are not API/DB/runtime
qualification. Maintainers must confirm required review/check policy before merge.

**Smallest remaining actions:** owner supplies/uses valid existing production
sign-in and selects one existing reviewer/owned source plus approved target
Portuguese family/contracts/CSV; maintainers review this bounded portability and
full stack; accounting owner specifies a separately reviewed future capacity policy;
deployment operator confirms shared Traefik protection for `/design-ai`, retains
the current private Compose chain and prepares approved isolated
staging acceptance plus full old-binary rollback. Complete the human observation
sheet. No final release approval is requested while these gates are unmet.

Local parameterisation and bounded Design with AI behavior verified; provider audit evidence remains partial; independent usability and code review remain outstanding.
