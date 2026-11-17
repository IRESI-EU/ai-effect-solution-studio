# Isolated design-only staging: API and rollback passed; browser pending

This is a new synthetic staging environment, not production or another Portuguese
execution profile. No provider request, workflow or algorithm was executed.
The historical genuine-provider acceptance remains **PARTIAL**; this record does
not replace it. Independent human usability remains **NOT PERFORMED**.

[Sanitized observations and exact identities](../deploy/release/STAGING_ACCEPTANCE_2026-11-17.json).
Authorized configuration: `20de4bdeb428c23a4ac66065e3761abc9dc85a2c`.
Narrow configuration correction: `c7ee549396614e08c5a6719083edbb5b211a6491`.
Application source remains `349f45166f319c040b2b3f2b98c4cefb9b537aa3`;
no application rebuild or dependency change was needed.

| Area | Result | Actual evidence |
| --- | --- | --- |
| Frozen packages / isolation | PASS | Exact API/web/PG/gateway images; 174 packaged source hashes checked against source, accounting for Windows CRLF; only gateway joins an edge bridge; sole published port is loopback24443 |
| HTTPS / auth / roles | PARTIAL | Certificate-verified HTTPS200, authenticated Secure cookies, logout→401; designer publication/approval and wrong-reviewer access denied. Browser sign-in/session/logout remains pending |
| Synthetic governance / discovery | PASS (API) | New staging-only accounts; labelled synthetic services imported pending review, approved by staging admin; draft0.2.0 contracts validated and activated only in staging. Registration binds actual environment/DB fingerprint/reviewer/source/full contract hashes |
| Configuration / persistence | PASS (API fixture) | Missing/unapproved CSV and stale revision denied without draft mutation; 2epochs/4batch/20sequences, Review/Apply/Undo/reapply/Save/compile; independent instance IDs, input, pins and model_ref binding retained |
| Visible packaged browser journey | PENDING | No substitute prepared example or API fixture is reported as browser acceptance. Await owner-confirmed scoped certificate trust and connected review browser |
| Permanent execution boundary | PASS | Direct API readiness/submission403, bypassing gateway; also403 with registration/environment removed and solution identity omitted. Exact configuration restored |
| Disconnected provider | PASS | Actual chat503: durable accounting/scoped allowance required. Provider config false; keys/tokens empty; API internal-only. No SDK dispatch authorized or possible through this guarded path |
| Monitoring / downloads | PASS (isolated fixtures) |13 owned-preview cases plus26 synthetic monitoring/download cases; exact bytes/hashes, wrong-owner/association/path/integrity denial. No synthetic artifact installed as generated staging output |
| Fresh migration / backup / restore | PASS | New schema core tables then001–005; consistent36,627-byte custom dump; restored into separate `design_ai_staging_restore_20261117110132`, matching saved rows; original DB retained |
| Actual binary rollback | PASS | Candidate→actual old API/web→candidate against same additive schema. Old and candidate records readable; old-binary write retained; restored candidate saved state exact. Old web BUILD_ID independently checked |
| Retained profiles / ledger | PASS | All56 original container IDs/images/mounts/states unchanged; historical results accessible; nine completed journal jobs/four closed scopes/queues unchanged; ledger28/28 closed, zero outstanding |

## Serving identities and provenance

- API: `sha256:29a48dae5efceac7fbab0b151909803a70ccec74843159b3fbe2349d55ea6e67`.
- Web: `sha256:57cf29da97ab875de93e78fa2068551ba6c44062233358de410a82c490ddc6c0`.
- Web BUILD_ID: `EY9BALGRvOJYRAkWG_pgJ`; linux/amd64.
- Maintained WP3 remains `d533219426af9ea6defaf0bc78956741201a5109`; no WP3 binary
  is deployed into this four-service staging environment.

Project `ai-effect-design-staging-20261117` owns new database/contracts volumes.
Database is `design_ai_staging`, not the sandbox. No private dataset bytes, grants,
ledger files, production rows, old accounts or execution captures were copied.
`staging-synthetic-csv-20261117` is an opaque design-only fixture reference, not
proof that a real training file exists in staging. Service labels explicitly say
SYNTHETIC STAGING and deny Portuguese-owner attestation/runtime availability.

The fixed public family/pins remain `pt-experimental-chain-TrainModel` /
`pt-experimental-chain-GenerateData`, `pt-chain-train-v2` /
`pt-chain-generate-v2`, version0.2.0; model_ref→model_ref/whole-output-v1.
Their source metadata records synthetic staging provenance. Full definition hashes,
reviewer, source digest and actual database fingerprint are in the evidence file.
The existing registration operator prepared/validated that policy read-only before
explicit installation. Bootstrap account passwords are absent from the running API.

## Demonstrated preparation corrections and initial failures

The mounted seed's direct file invocation could not import `app`; it failed before
account creation. Invoke it from `/app` through `python -c` and `runpy.run_path`,
as corrected in the existing staging helper. No image rebuild was required.

Docker29 retained HostConfig's loopback port mapping but did not publish a port on
an internal-only network. Only the HTTPS gateway now joins `review_edge`; API/web/DB
remain exclusively on the internal network. API/web/DB have no host ports. This
staging-only overlay must not be applied to production.

An initial rollback login500 occurred before the old API was healthy; the candidate
was restored automatically. Repeating this non-executing rehearsal with both web
and API health barriers passed. The failed observation is retained here rather than
reported as a first-attempt pass. There was no algorithm or workflow retry.

The source daemon uses legacy image-config IDs. Docker Desktop imported OCI IDs:
old API `ded4f325…`→`66125fea…`, old web `851115fb…`→`4e06e7f0…`.
Every root filesystem layer and nonempty image configuration value matched the
actual read-only source images; only legacy empty/false configuration defaults were
omitted by OCI presentation. This is recorded conversion, not rebuilt/relabelled
code. Old web BUILD_ID is `aLp4c1xkUjCM1v23PtrYY`. No production container changed.

Focused checks:22 target-registration/owned-preview +29 release-boundary/synthetic
monitoring/download +1 stale-source = **52 passed**. The first unprivileged test
attempt had9 passes then13 temporary-directory permission errors; the bounded
rerun outside that filesystem sandbox passed. Deprecation warnings remain. These
SQLite fixtures do not establish PostgreSQL concurrency or live scientific results.
The real staging route and binary checks used PostgreSQL. No unrelated full suite
or redundant frontend build was run for configuration-only changes.

## Inspection and the pending browser step

Entry: <https://127.0.0.1:24443/design-ai>.
Private account record in the **original checkout**:
`local-backups/staging-acceptance-20261117/profile/credentials.json`.
Use `designer_a` / `reviewer-a@staging.invalid`; do not copy its password into reports.

[Saved API regression fixture](https://127.0.0.1:24443/builder?solutionId=908f8d2c-fd7e-44bf-8c9f-84016b68b012)
is explicitly **not** a browser-assembled acceptance design. Its new instances and
saved state survived rollback. The eventual visible walkthrough must create a
different draft using normal controls, select the CSV and2/4/20, review/apply/undo/
reapply/save/refresh/open Builder/validate. No helper should prepopulate that draft.
There are zero staging deployments/submissions/execution records.

The automation in-app browser exposes no scoped certificate-trust control and
blocks `chrome://certificate-manager`; no bypass or Windows trust change occurred.
Visible acceptance remains pending until the owner confirms trusted HTTPS and a
connected review browser. Certificate SHA-256:
`sha256:7d53d601d64bda6476e1a8aa32508c3ed6f26b5df8800f2d83b0c6d0ebcc57da`;
expires17 December2026 10:47:18UTC; SANlocalhost and127.0.0.1.

A supported owner-operated alternative is a separate Chrome134+ local profile
without sync: open `chrome://certificate-manager`, Custom→Trusted certificates→
Import the private staging `tls/localhost.crt` (never its key), verify the fingerprint,
and constrain trust to127.0.0.1/localhost where offered. Stop if directed to Windows
Certificate Manager. Do not use an interstitial exception or disable verification.
Chrome's custom server-certificate database is profile-scoped, distinct from OS
trust: [Chromium guide](https://chromium.googlesource.com/chromium/src/+/main/net/data/ssl/chrome_root_store/faq.md),
[profile storage implementation](https://chromium.googlesource.com/chromium/src/+/main/chrome/browser/net/server_certificate_database_service_factory.cc).
That profile must be connected to Codex before automated visible acceptance can resume.
Import has not been performed or claimed here.

From the original checkout, the private operator entry point is:

```powershell
./local-backups/staging-acceptance-20261117/Inspect-Staging.ps1 -Action Status
# Stop only these four staging services; retain volumes/data:
./local-backups/staging-acceptance-20261117/Inspect-Staging.ps1 -Action Stop
# Later normal restoration, no build/pull:
./local-backups/staging-acceptance-20261117/Inspect-Staging.ps1 -Action Start
```

Staging remains available for inspection, provider/execution disabled. The private
profile retains its exact environment, certificate, rollback overlay and verified
backup. Do not use `down -v`, recreate accounts, mount sandbox evidence or start a worker.

## Production remains separately gated

No production compatibility or release approval is established. Remaining gates:
complete this visible staging journey and independent human observation; review the
full Portal8–22/WP32–4 stack and required checks (Vercel author/project access is
distinct from code failure); valid normal production reviewer sign-in; owner-approved
Portuguese family/contracts/input and target-bound registration; separately reviewed
future accounting-capacity lifecycle; reviewed production migration/current consistent
backup and complete Traefik protection/configuration. Portuguese-hosted execution
needs deployment-specific qualification. No production migration, contract, ingress,
worker, account or spending policy was changed.
