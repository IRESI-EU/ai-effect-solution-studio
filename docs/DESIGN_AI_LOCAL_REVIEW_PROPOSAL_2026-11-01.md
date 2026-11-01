# Local review staging proposal — build preparation complete

**Destination selected by the owner: this Windows computer, Docker Desktop `desktop-linux`, Linux/amd64. No staging project, network, volume, database, account or application service has been started. No certificate trust has been installed.**

This is fresh, disconnected **authenticated portal review** with synthetic data. It does **not require production access**. Production inventory remains a prerequisite for a later production upgrade or connection. This first staging scope cannot reproduce the live Design with AI experiment: chat, workflow submission/execution, runtime probes and arbitrary-reference preview are denied; no WP3, worker, algorithm, provider or capture volume is included.

## Built candidate and exact inputs

Portal image source: **`0458b93949a4182e5dc8bab66cbd04e8bca26367`**, on existing draft PR #13, following baseline `1df280d3d8debff531ce3470aa000a7658623f96`. Operator source **`b8eadef9f0b74ec1ac4c920e9522d80c0942e420`** initializes the four core tables before the five additive migrations on a fresh database; it does not change any image input. Subsequent documentation packages this proposal/evidence. WP3's maintained dependency remains **`0221b7ecd4a2d5f072de640350ebc599df22131a`**; it is not installed in this first environment.

| Role | Exact local image identity | New tag where applicable |
|---|---|---|
| API | `sha256:8a998103f1ea42cb1a8fd461e8e3fbf32c992d98b60c3147917f9cac95a758e1` | `ai-effect-staging-api:0458b93949a4` |
| Web | `sha256:2c9ec04228b8e223d8fcd6adf86188b5a591e814c43eb25317ac95d33a20c36a` | `ai-effect-staging-web:0458b93949a4` |
| PostgreSQL 16 | `sha256:5d143123fdf80462d1778cd4f24b9f7ca13c87174bca19141fb194c5a1ebca59` | Existing installed image bytes only; no existing database/volume is reused |
| nginx | `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10` | Existing installed image bytes only |

The API/web images are built locally, non-root, separately from running demo images. No existing tag was overwritten. The [machine build record](DESIGN_AI_BUILD_PREPARATION_2026-11-01.json) records these identities, checks and unchanged demonstration state.

- Target is **Linux/amd64, CPython 3.12.14, Node 24.15.0, pnpm 11.25.0**. Python/Node match the complete validated host versions. The separate demo image's newer Python packages were not adopted.
- Python base: `python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` (`3.12.14-slim-bookworm`). Node base: `node@sha256:4e6b70dd6cbfc88c8157ba19aa3d9f9cce6ba4703576d55459e45efcbc9c5f5d` (`24.15.0-bookworm-slim`). Only those required bases were obtained; no WP3/country images were pulled.
- [Python runtime lock](../deploy/staging/build/requirements.lock) pins **48 packages and wheel SHA-256 values**. The runtime closure uses the validated host package versions, with Linux-only uvloop 0.23.0 from the existing Linux environment. In particular FastAPI 0.142.2, Starlette 1.7.0, Pydantic 2.13.5 and SQLAlchemy 2.1.3 are retained. SDKs remain mcp 1.30.0/openai 2.54.0. No unrelated upgrade occurred.
- [Input manifest](../deploy/staging/build/inputs.lock.json) pins exact wheel filenames/hashes and the pnpm archive SHA-256. The unchanged `pnpm-lock.yaml` pins web packages/integrities. pnpm's archive is checksum-verified before use; there is no floating Corepack activation. Python installation is offline with `--require-hashes`; only frozen web dependency acquisition uses registry networking. Tests, route type generation, typecheck and production compilation run without build networking.
- [API](../deploy/staging/build/Api.Dockerfile) and [web](../deploy/staging/build/Web.Dockerfile) are the explicit candidate recipes. The generic historical production Dockerfiles are not this candidate's build path. These are pinned build inputs and recorded image identities, not a claim that Next/BuildKit timestamps and generated build IDs are byte-for-byte deterministic across rebuilds.

From the PR checkout, reproducible input acquisition/build commands are:

```powershell
& $py deploy/staging/fetch_build_inputs.py --output <new-private-input-directory>
& $py deploy/staging/build_candidate.py --inputs <private-input-directory> --records <new-private-build-record-directory>
```

The fetcher accepts only the locked package files/digests. The builder requires committed source, pins `linux/amd64`, records the source label, and refuses to overwrite an existing candidate tag. Reuse the existing images for this proposal; an intentional rebuild needs a newly reviewed source/tag or a separately planned output identity. Do not substitute a moving base tag.

## Prerequisite review and newly run checks

The cumulative authentication, ownership and onboarding source beneath PR #8 was reviewed, including session/cookie/password handling, registration/approval, administrator lifecycle, legacy-owner assignment, package preview/atomic registration, service management, solution ownership and protected downloads. Two narrow release defects were corrected in **`6959925`**:

1. `/admin/users/{id}/approve` could rewrite an already-active account, including demoting the sole administrator, bypassing the normal update guard. Approval now applies only to pending registrations. Three isolated regressions first failed against the old behavior, then passed; rejected/replayed approval preserves user fields and audit count.
2. Concurrent account changes could both remove administrators, and concurrent legacy assignments could both read an unowned row and overwrite the first assignment. Account changes now take ordered active-administrator locks and recheck the actor after waiting. Solution/deployment/service owner assignments lock and refresh their target. Five real PostgreSQL race tests verify the administrator invariant, revoked-actor denial and first-owner preservation, including linked deployment ownership.

The generic reference-preview route still lacks a per-workflow ownership boundary. It remains **blocked**, including trailing/encoded variants; this task does not pretend that gateway denial repairs its underlying API contract. A future reopening needs an owned workflow/task/reference association, constrained protocol/destination/path resolution, integrity checks and cross-owner/SSRF/download regressions.

| Newly run check | Actual result |
|---|---|
| Portable backend inventory in the built API's Linux runtime | **291 passed**, 0 failures/skips, network disabled; includes the new prerequisite and synthetic-bootstrap tests |
| Existing authentication/ownership suite | **7 passed** on a fresh disposable PostgreSQL database |
| New real PostgreSQL concurrency cases | **5 passed** on disposable databases |
| Fresh four-core-table initialization, then migrations 001–005 twice | **1 passed** on a disposable database; original sentinel preserved and all authentication check constraints present |
| New bootstrap/operator/approval focus | **7 passed**; atomic synthetic bootstrap, existing-data/qualification refusal, and no mutation without explicit operator approval |
| Web tests in the pinned Linux build | **39 passed**, 0 failures/skips |
| Fresh route type generation / TypeScript / production webpack build | **Passed / passed / passed**, Node 24.15.0, Next 16.3.8; build ID `MHMxnSxQ4khLhh2UTWZpF` |
| Runtime dependency/native checks | `pip check` and psycopg/uvloop/crypto imports passed; Python 3.12.14; compiled web rewrite is `http://api:8080/:path*` |
| HTTPS/network boundary fixture | Certificate/IP verified with normal certificate validation; **12 denied requests returned 403**, including trailing/encoded paths; mock login proxy 204. No host port or provider/runtime endpoint was contacted |
| Proposal configuration | All four immutable images present; compose syntax passed; no staging services/accounts/trust created |

The earlier complete **392-test backend inventory**, **317 WP3 unit checks** and synthetic migration/backup-restore rehearsal remain historical evidence at their recorded sources. They were not rerun for documentation or unchanged WP3. Current real-PostgreSQL checks target the actual account/ownership changes; the Linux portable inventory tests the new runtime/dependency build. Existing deprecation warnings remain visible.

Failed build-preparation attempts remain in private logs: the pnpm archive needed the executable mode normally set by its installer; an initial web build incorrectly denied its own locked dependency fetch; and a test-only BuildKit stage tried to resolve an unpushed digest through a registry. The final build grants networking only for frozen web dependencies, and the test layer used the existing local tag after verifying its exact image ID. None is counted as a successful initial attempt or a provider/runtime test.

## Concrete local host, storage and browser proposal

- Docker project: **`ai-effect-review-staging-20261101`**, absent at preparation. Proposed volumes are `ai-effect-review-staging-20261101_database` and `ai-effect-review-staging-20261101_contracts`; network is `ai-effect-review-staging-20261101_private`, **internal**. No external/demo network, artifact mount, WP3/Redis/worker service.
- Only binding: **`127.0.0.1:24443 → gateway:8443`**. Port 24443 was unbound and outside Windows' excluded TCP ranges when inspected. API, web and PostgreSQL publish no ports. No LAN binding, tunnel, Contabo, production infrastructure or public DNS.
- Expected browser entry after approved startup/trust: **`https://127.0.0.1:24443/login`**. It is currently not listening. Users can sign in, review/edit/save their synthetic manual design, inspect the catalogue, and test admin registration/ownership controls against new staging data. They cannot chat, submit/execute workflows, verify runtimes or open arbitrary references. No experiment has executed in this environment.
- Limits: PostgreSQL 768 MiB/0.5 CPU, API 768 MiB/0.75 CPU, web 1,536 MiB/1 CPU, gateway 128 MiB/0.25 CPU: **3.125 GiB and 2.5 CPUs maximum**. Docker Desktop currently reports 14 CPUs and about 15.35 GiB RAM; existing workloads remain untouched. Reserve **at least 5 GiB free disk** for the fresh database, logs/backups and host/Docker headroom, with additional space for future image exports.
- **Current host blocker:** C: had **972,558,336 bytes (~0.91 GiB) free** when checked. Restore storage headroom before provisioning. No image/volume/cache/evidence pruning, Docker resource change or file move was performed to conceal this finding.
- Prepared private files: `<original-checkout>/local-backups/local-staging-proposal-20261101/`. `credentials.json` holds three new staging-only login secrets; `bootstrap.env` is for the one-time seed; `runtime.env` blanks all bootstrap/designer secrets while retaining only the staging DB connection secret. Accounts do not exist until the explicit bootstrap command. The directory ACL is restricted to the current Windows user and SYSTEM. Nothing is committed or baked into an image.
- `tls/localhost.crt` and its protected private key are a new 30-day self-signed localhost/127.0.0.1 server certificate. The private `proposal.json` pins its thumbprint. No trust store was modified. The browser needs the explicit CurrentUser trust step below; do not disable TLS validation or relax Secure cookies. The staging session cookie is **`ai_effect_review_staging_session`**, separate from demo sessions.

The [configuration template](../deploy/staging/compose.yaml), [TLS gateway](../deploy/staging/nginx.conf), [guarded operator](../deploy/staging/local_review.py) and [one-time atomic seed](../deploy/staging/synthetic_seed.py) are published. All provider, grant, checkpoint, ledger and capture settings are blank/false. The unreachable orchestrator placeholder is additional disconnection; explicit gateway denials and absence of runtime services are the submission boundary.

## Exact owner-approved operation sequence — not executed

Run PowerShell **from the original production-ui checkout**. The checks below do not provision anything:

```powershell
$original = (Get-Location).Path
$repo = Join-Path $original 'local-backups/design-ai-demo-portal'
$private = Join-Path $original 'local-backups/local-staging-proposal-20261101'
$py = Join-Path $original '.venv/Scripts/python.exe'
$ops = Join-Path $repo 'deploy/staging/local_review.py'
& $py $ops check --private-dir $private
if ((Get-PSDrive C).Free -lt 5GB) { throw 'Restore at least 5 GiB free space before provisioning.' }
Get-NetTCPConnection -LocalPort 24443 -State Listen -ErrorAction SilentlyContinue
# If another application owns this port, stop and revise the proposal; do not stop it.
```

**After explicit owner approval only**, trust the exact prepared local certificate in the current Windows user's store:

```powershell
$proposal = Get-Content (Join-Path $private 'proposal.json') -Raw | ConvertFrom-Json
$certFile = Join-Path $private 'tls/localhost.crt'
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($certFile)
if ($cert.Thumbprint -ne $proposal.certificate_thumbprint) { throw 'Certificate identity differs.' }
certutil.exe -user -addstore Root $certFile
```

Then create **only this new isolated review environment**:

```powershell
# Creates only this project's PostgreSQL/network/volumes, initializes the four
# core tables via a one-shot command (no server), then applies 001..005 in order.
& $py $ops migrate --private-dir $private --approve-provisioning
# One-shot command, not a server: refuses any existing users/services/solutions/deployments.
& $py $ops bootstrap --private-dir $private --approve-provisioning
# Starts postgres/api/web/gateway from runtime.env, with bootstrap secrets blank.
& $py $ops start --private-dir $private --approve-provisioning
# Confirm the actual Windows listener is 127.0.0.1 only. If it is wildcard/LAN,
# stop this project immediately and retain its volumes; do not continue review.
Get-NetTCPConnection -LocalPort 24443 -State Listen | Select-Object LocalAddress, LocalPort
# Uses the local certificate explicitly; probes login, health, anonymous denial and blocked routes.
& $py $ops verify --private-dir $private
```

The operator fixes the local `desktop-linux` context/project, verifies all four pinned image IDs and private configuration, and requires `--approve-provisioning` for mutations. There is no build/pull/start of an unrelated service. Read the credential file locally, sign in as reviewer A, confirm only A's synthetic solution is accessible, then reviewer B and the administrator. Use a real participant/observer for usability; do not invent observations. Confirm Secure/HttpOnly/SameSite cookies, disabled chat/execution, synthetic labels and zero deployment/submission records. These integrated browser checks remain pending approval/startup.

Shutdown and retention:

```powershell
& $py $ops backup --private-dir $private --approve-provisioning
& $py $ops stop --private-dir $private --approve-provisioning
```

Backup uses binary-safe `pg_dump -Fc`, exclusively creates a private timestamped file and reports its hash. Stop targets only this project's four services and retains both volumes. **Do not use `down -v`, reset, re-seed or overwrite a populated database.**

For the first deployment, rollback is `stop`: retain all new data and inspect the failure. For a later data rollback, stop application traffic and restore a retained staging backup into a **new** database, preserving the original:

```powershell
& $py $ops restore --private-dir $private --backup '<retained-private-backup.dump>' `
  --restore-name design_ai_staging_restore_20261101190000 --approve-provisioning
# Choose a new timestamp/name for each restore; an existing name fails, never gets reset.
# Review restored counts/owners. Explicitly set STAGING_DATABASE_NAME in runtime.env
# to that new database, then start and verify again. Do not run bootstrap on restored data.
```

Before later image upgrades retain this image/configuration manifest and a tested backup. Application rollback uses the previous authenticated compatible image IDs with additive schema/history retained; no downgrade to an unauthenticated app or automatic table removal. The existing synthetic backup/restore rehearsal does not claim that this not-yet-created staging database has already been backed up.

After shutdown, optional removal of **only this certificate's** trust:

```powershell
$thumb = (Get-Content (Join-Path $private 'proposal.json') -Raw | ConvertFrom-Json).certificate_thumbprint
if ($thumb -notmatch '^[A-F0-9]{40}$') { throw 'Unexpected certificate identity.' }
certutil.exe -user -delstore Root $thumb
```

## Separate engineering for a future qualified Dutch staging experiment

This is not enabled or implemented by this proposal:

1. Design an explicitly reviewed staging qualification identity/authority, independent of the local database name and `seed-orchestrator` address. Existing `qualified_demo.profile_enabled`/capture guards stay unchanged. Do not rename staging to `design_aie37_qualification` or copy its profile to impersonate qualification.
2. Build and qualify dedicated WP3/runtime images from the maintained dependency and reviewed wrappers; pin parameter/binding capabilities, canonical validator digest, module/proto/image provenance and the exact supported generator→benchmark contracts. Preserve `http-parameters-v1`/`whole-output-v1` compatibility checks and fail closed on drift.
3. Provide fresh, dedicated staging execution/capture storage and an authorized capture adapter with owned submission/workflow/task/node matching, separate generator-consumption and benchmark-input proofs, integrity checking and historical revalidation. Do not import the preserved local run as a new staging execution or weaken guards to read arbitrary files.
4. Integrate server-owned draft/save/readiness/attempt identity and single-grant claims with that new authority. Test stale contracts/writes, competing copies, uncertain submissions, wrong ownership/association, failure and runtime outage before live acceptance.
5. Separately authorize any actual provider request, outbound provider networking, budget/checkpoint and exactly bounded execution. The current shared allowance stays **13/13** and is not repurposed. No provider key, ledger or new grant is prepared here. Then define a fresh same-copy acceptance with explicit controls, stop conditions, captures/downloads and cleanup; retain the synthetic/no-op/scientific limitations.

## Owner actions and assessment

**Build preparation is ready. Local provisioning remains blocked on host disk headroom and owner approval.** The concrete proposed approval is: trust this one prepared localhost certificate, create this one new Docker project/volumes, apply the five migrations, create only the three synthetic accounts/two synthetic designs, and start the four pinned services on **127.0.0.1:24443**, with all AI/submission/execution guards retained.

No additional host or production decision is needed for this disconnected scope. Current production inventory is needed later for a production upgrade/connection. Vercel author-access failures are separate: the project owner still needs to grant linked GitHub author `adarshsunil` deployment access to the existing Vercel team/project and rerun #8–#10's original checks. No attribution, required check, PR stack base or history was changed to bypass them. Vercel access is not required to run this local Docker Desktop review.

Original live acceptance and separate correction remain unchanged; `wf-1b6eb7caaf57` and all four artifacts are preserved. Provider/grants remain disabled, allowance **13/13**, outstanding reservations **0**, new provider/workflow/algorithm calls **0**. No production, merge, infrastructure provisioning or tracker change occurred. Independent usability, broader AIE-38 composition and production compatibility remain unverified.
