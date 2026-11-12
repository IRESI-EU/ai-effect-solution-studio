# Restricted beta engineering review — 11 November 2026

**Prepared, not activated or deployed.** This is an append-only follow-up to the [10 November acceptance report](DESIGN_AI_CONVERSATIONAL_ACCEPTANCE_2026-11-10.md) at e0145d09a6603b239fcb17468ce4c3dacda1c630. Original failures, catalogue stops and acceptance outcomes remain unchanged. No new genuine acceptance or independent participant observation occurred.

## Reviewable candidate

Application/accounting source: **7165a398c1583daae567fb5cf48aabf35fe32a7b**. This remains on draft [PR #17](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/17), stacked on PR #16; no PR was merged, retargeted or self-approved.

| Component | Retained local candidate |
|---|---|
| New API | ai-effect-beta-candidate-api:7165a398c158; sha256:3717c012fed8d8cd4f04469335b8f93a42224708f54dfd08c3b6858aa4d74c19 |
| Unchanged web | sha256:fba983fef01d461e79db22444c34c76b9737df84365d200972085672a4052614; source 4ff3285bdaf6cd0951b946b1d1667212b197e74d |
| Web BUILD_ID | XLX_batDPkRXN0X7avzOq |
| Platform | linux/amd64 |
| New source-only context SHA-256 | 1700a51b0efb83087022ae913c4a4a372c7182be2d203d3b93c103329ed60f4b |

The API build used only the retained dependency image sha256:8a998103f1ea42cb1a8fd461e8e3fbf32c992d98b60c3147917f9cac95a758e1 and python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e. The committed requirements.lock and installed versions/pip check passed inside the build. No dependency upgrade, download, pull or application-service start occurred. The recipe now supports --roles api to avoid rebuilding unchanged web code. A read-only, network-disabled utility container verified all **68 API Python files** against the committed-source manifest and confirmed provider/authority defaults disabled. The web image retains its original source label; byte identity of web/build/dependency source against 4ff3285 was checked, rather than relabeling or rebuilding it.

Private logs/manifests are under the original checkout at local-backups/restricted-beta-work-20261111/, including api-build-7165a39/. The prior production backup/restore evidence and rollback identities remain under local-backups/restricted-beta-release-20261110/. They are not committed or included in image contexts. Existing demonstration builds/profiles were not replaced.

## Dutch contract findings

Four versioned **0.1.0-draft.1** proposals, actual inputs/defaults/output behavior, exact deployed image identities, nine selected source-file hashes and the Dutch-owner checklist are in [the contract dossier](contracts/dutch-production/README.md). Every proposal is unconfirmed, owner_confirmation=null and activation_allowed=false. Schema validation is not owner approval; binding_transport and execution_parameters remain null, so these drafts cannot advertise a compatible pair.

The deployed Paulban generator and benchmark control/operation/protobuf files exactly match [paulban/ai-effect-wp3 at ba598b2459f9986dac4e37dcc5d7d3298f25dc3a](https://github.com/paulban/ai-effect-wp3/tree/ba598b2459f9986dac4e37dcc5d7d3298f25dc3a/use-cases/dutch_node). This establishes those selected source bytes, not whole-image reproducibility or scientific qualification.

- **Imported family:** the strongest owner-review starting point. Its HTTP control generator takes optional inline JSON, defaults to seed 42 and returns a grpc GetGridData reference. Benchmark control fetches that reference and supplies built-in benchmark/algorithm defaults. Direct gRPC request shapes differ from this control-reference path.
- **Package family:** uploaded protobuf request/response messages are empty. Declared GHCR images differ from the running Paulban services addressed by their health URLs. Exact missing ZIP digests, manifest/protobuf files and GHCR source/build provenance are named in the dossier; health success is insufficient evidence.
- **Concrete implementation gaps:** the deployed ExecuteRequest has no parameters field/validated http-parameters-v1 route, so the composer's flat seed=43 setting is not established as consumed. GetGridData reads a process-wide latest cache through an empty request, not a task-specific immutable snapshot. Do not substitute captured_grid, local wrapper pins or a seed [42,43] enum. An owner-approved strict setting-delivery change and a task/grid-specific association change are separately required for the corresponding claims.

No production registration, contract, source or running service was changed. The owner must choose one authoritative family and attest inputs/settings, reference schema/MIME/cardinality and binding behavior through normal governance. Runtime/scientific qualification remains separate from design compatibility.

## Shared accounting implementation

The [accounting runbook](../deploy/restricted-beta/ACCOUNTING.md) describes a separate private authority over the **same original ledger on its canonical Windows host**. Application environments use authenticated clients; no allowance/database replica is created. All new settings default empty. The authority factory refuses an unactivated policy and is not mounted in the portal API.

The reviewed operator supports exactly **13 to 15** calls for a new two-permit acceptance scope (USD0.010 lifetime reservations) and, only after two accounted permits plus attributable acceptance-pass evidence, **15 to 25** for ten beta permits (USD0.050). Each reservation is USD0.005; the original global USD0.10 ceiling and historical usage/audits remain. Neither transition was applied. Earlier checkpoints cannot reopen. The legacy local database guard is unchanged; the new opt-in path explicitly binds PostgreSQL host/port/database/role, consumer, environment and scope. Legacy writers are denied once the authority is installed.

BEGIN IMMEDIATE and FULL synchronous rollback journaling serialize multiple processes/environments. One unresolved permit blocks all further requests. Fresh nonces authorize dispatch once; lookup/replay never dispatch. Usage settles before model parsing and is acknowledged separately, so a lost settlement response keeps the system paused. Unknown usage retains the complete hold; a process crash does not refund calls, and an overrun is recorded before closing spending. No automatic mutation retries, timeout refunds, replacement ledgers or stale-backup reactivation exist. Every transaction checks audited state, canonical path and filesystem identity. Only numeric usage/response identity is persisted, not prompts or output text.

The provider adapter retains gpt-6-luna, low reasoning, Standard/default processing, output <=2,000, zero SDK retries/fallback, a bounded framed input and explicit 30m cache-write policy. Pricing is linked and dated in the runbook and must be checked again before spending. A disconnected, denied, corrupt, conflicting or unavailable authority prevents SDK construction/dispatch.

**Transport release prerequisite:** the proposed private Windows loopback authority plus existing SSH-forwarded Linux Unix socket is not provisioned or end-to-end qualified. Exact reviewer/environment fingerprints, the Windows/OpenSSH forward, API-UID socket permissions/mount and outage behavior must be reviewed and exercised in isolation before activation. A host/tunnel outage must pause AI requests. Unit/ASGI tests do not establish that production transport works. No token, service, tunnel or mount was created here.

## Cumulative review against verified production

Use the actual server baseline from the preceding report, not the historical Vercel metadata:

| Scope | Exact review diff / material changes |
|---|---|
| API baseline 89072340c9a13f3aa49d3e433380de8928cc16dd | [Cumulative API candidate diff](https://github.com/IRESI-EU/ai-effect-solution-studio/compare/89072340c9a13f3aa49d3e433380de8928cc16dd...7165a398c1583daae567fb5cf48aabf35fe32a7b). Review Design with AI, typed contracts/settings/binding compiler, immutable submission/capture history, ownership checks, disabled execution and new accounting. |
| Web baseline df5b75873326ab56cad608990f3bd4add125bcc4 | [Cumulative candidate diff](https://github.com/IRESI-EU/ai-effect-solution-studio/compare/df5b75873326ab56cad608990f3bd4add125bcc4...4ff3285bdaf6cd0951b946b1d1667212b197e74d), restricted to apps/web for this component. Review conversational discovery/review/Create/Apply/Undo/Save, Builder, historical evidence and honest disconnected/paused wording. No new UI changes this follow-up. |
| This follow-up | [Exact incremental diff](https://github.com/IRESI-EU/ai-effect-solution-studio/compare/e0145d09a6603b239fcb17468ce4c3dacda1c630...7165a398c1583daae567fb5cf48aabf35fe32a7b): accounting, tests, source-backed unconfirmed drafts and selective build packaging. |

GitHub comparison pages include repository-wide changes; use the stated component paths and recorded image source labels. The API and web production baselines differ. Portal source parity does not pin or upgrade partner runtimes.

**Authentication/onboarding:** production already has session authentication/RBAC and ownership columns. The candidate must not be described as introducing authentication into an unauthenticated server. Existing auth/dependencies are unchanged against the verified API baseline; cumulative admin changes add row locking/self-lockout protection and serialize legacy ownership assignment. Restricted Design with AI additionally requires exact existing active reviewer IDs and approved roles on every route, including config; no admin bypass. No user or reviewer was created/inferred, password changed or permission granted.

**Artifact authority:** the candidate fixes generic preview and deployment-claim defects identified in the preceding review. Preview requires an authorized deployment, integrity-checked server submission matching workflow/owner/solution, same-workflow task output and resolved workflow file namespace. Legacy/unknown associations, symlink escapes and unqualified remote transports stay blocked. POST deployments cannot manufacture authority for an arbitrary runtime ID. Existing qualified-capture downloads remain a separate guarded path; a cached success or completed task alone does not authorize an unrelated artifact. These repairs remain candidate source, not deployed fixes.

**Migrations:** additive 003_design_ai_pilot.sql, 004_instance_submissions.sql and 005_local_capture_records.sql are still required above the verified production schema. The prior consistent 86,227-byte custom backup (SHA-256 b5d862f4d99c57d3e4532166cc171a57b053f8eb439a8a90be2d0c5915b59764) restored twice, and migrations were applied/reapplied with all original rows preserved. Migration files and dependencies are unchanged this follow-up; no new production migration or repeated restore was necessary. Authority schema changes are a separate future audited operator transaction in the original ledger, never a production SQL workaround.

**Rollback:** the running production API image sha256:ded4f325be3769f834f5a40b1e3cf7f85aef0e0d25126b51d9509892cd562340, web image sha256:851115fb98582c8c077ed28e3b6db46c40a1079467cb4e3a11faabf5c19f2a0f and their retained release/configuration directories are unchanged. There is nothing to roll back now. A later code rollback must not overwrite new user writes with the older database backup or fork/revert newer allowance history. Existing demonstrations, accounts, capture volumes and original failed evidence are not migration seeds.

## Checks and preservation

| Check newly run | Result |
|---|---|
| Eight focused backend files on final application source | **111 passed**, 203 deprecation warnings, 49.36s |
| Accounting concurrency/failure coverage | Cross-consumer contention, count/phase/shared-money caps, one-dispatch nonce, immutable history, unavailable/busy/missing/corrupt store, identity/fork denial, uncertain usage, lost reserve/settlement replies, crash before/after commit, restart recovery, stop/late settlement and no local fallback |
| Provider/protocol coverage | Authenticated ASGI authority + HTTP transport doubles; SDK doubles only; no real provider requests. Raw usage settles before invalid-output parsing; output/model/tier/cache/retry controls checked. |
| Contract drafts | All four proposed_contract objects pass OperationContractWrite validation; activation remains prohibited |
| Packaging | API build/pip check and exact 68-file verification passed; web/dependency/migration parity checked |
| Publication | Source commit secret scan and whitespace checks pass; final evidence/published-head status recorded separately |

The final eight files are test_shared_allowance.py, test_allowance_authority_protocol.py, test_design_ai_budget.py, test_design_ai_task_limit.py, test_design_ai_provider.py, test_restricted_beta.py, test_allowance_amendment.py and test_demo_allowance.py. Earlier intermediate 110-test runs overlap and are not added to 111. No unrelated full inventory, new browser walkthrough, typecheck or web build was repeated for unchanged web source. Historical backend failures and their later fixes remain in the original records; this focused result is not a new complete-suite or PostgreSQL concurrency claim. Accounting concurrency here is exercised on its actual SQLite ledger engine, including subprocess death.

Read-only inspection of the real original ledger before/after produced the same SHA-256 c5d34d33914623978335c02471f635239b1fae29bee6fcf2f77411e930a8477f: **13/13**, USD0.10 ceiling, held/accounted upper USD0.004207375, conservative remainder USD0.095792625, **zero outstanding reservations**, authority inactive. No checkpoint, binding credential, grant, policy or ledger write occurred. New usage **0 calls / USD0**. Disk headroom before packaging was **24.46 GiB**; no cleanup or recovery was needed.

Production/source inspection was read-only. The failed temporary credential was not retried. No provider call, contract activation, workflow, readiness probe, new profile, production deployment, merge or tracker update occurred.

## Reviewer and activation checklist

- [ ] Review cumulative API/web and prerequisite PRs, ownership/onboarding changes, generic artifact authority and all additive migrations; preserve required checks and attribution. No self-approval.
- [ ] Dutch owner selects one actual family, reviews source-backed drafts and supplies approved settings/transport/reference evidence. Seed delivery and immutable same-grid retrieval need explicit service/adapter engineering, not attestation of nonexistent behavior.
- [ ] Existing owner signs in normally and confirms exact existing reviewer IDs. Prior HTTP 401 is preserved; no reset/retry/new account substitutes.
- [ ] Review and isolate-test the one-authority scope, canonical file, private transport/ACL, crash/lost-message recovery and pinned provider pricing. Do not copy/fork the budget or impersonate the local qualification DB.
- [ ] Only after applicable prerequisites pass, apply the supported new acceptance scope and run the two previously authorized exact cases once each under their original caps/stops. Do not change messages or expectations after responses. Existing paid authorization persists.
- [ ] Only after genuine acceptance and code review, apply the distinct ten-permit beta scope. Keep new composed workflow execution disabled. No release or production-compatibility claim until actual environment checks pass.

| Release checklist | Current state |
|---|---|
| Completed | Source-backed contract drafts/comparison/owner checklist; durable accounting/operator/client implementation and focused regressions; pinned API package and cumulative review evidence |
| Awaiting Dutch-owner confirmation | Authoritative family, corrected seed-setting transport, actual reference schema/binding and versioned active contracts; task-specific grid association before runtime claims |
| Awaiting normal production sign-in | Existing account and exact reviewer identities remain unverified; prior 401 not retried |
| Awaiting code review | Cumulative draft stack and new authority scope/protocol remain unapproved; checks/author attribution preserved |
| Remaining implementation/release gaps | Partner setting-delivery and immutable-grid changes are not implemented; private cross-environment accounting transport is not provisioned/qualified. No known failing focused accounting regression. |

Target remains https://platform.ai-effect.eu/design-ai **after** gates pass; no beta access is enabled. Independent human usability, genuine model interpretation for the production pair and production compatibility remain unverified.


## 12 November follow-up: implemented partner seed-delivery patch

The [concrete Dutch owner-review package](partner-review/dutch-parameters/README.md) now supplies actual generator control/handler code and 24 focused passing tests against partner baseline **ba598b2459f9986dac4e37dcc5d7d3298f25dc3a**. Local-only partner head **c08c86aa09a577915cec5d868c7deef73ec408ad** is exported as a cumulative reproducible patch, with exact-baseline replay/tree verification, before/after request, unconfirmed 0.2.0-draft.1 contract/capability proposals and owner checklist. No partner push or PR occurred.

The previously missing strict parameter-delivery implementation is prepared for review: exact maintained configuration envelope and shared validator, seed type/bounds/version checks, no silent invalid-setting defaults, explicit dual-source rejection, default 42, and valid 43 observed at both constructor call sites with algorithm doubles. Registry schema/digest round-trip passes. No real algorithm or new workflow ran; latest-cache association and safe concurrency are deliberately unresolved. Production still runs its prior implementation; partner approval/deployment and all other release gates above remain unmet.

Portal application/migration source and existing candidate images remain unchanged. No contract activation, provider/allowance policy change, paid request, grant, saved-design edit, account change, deployment, merge or tracker update occurred. Shared allowance remains **13/13**. The original 11 November findings and earlier acceptance failures remain historical evidence.
