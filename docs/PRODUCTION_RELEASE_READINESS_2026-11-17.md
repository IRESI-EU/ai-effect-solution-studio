# Production release readiness — 17 November 2026

**Decision: proceed with production inventory and release-candidate preparation. Public cutover is not ready.**

The target is a restricted, design-only production beta for selected existing users, preserving existing production journeys. Portuguese experimental execution remains excluded. This assessment freezes source for review; it does not identify a deployed release candidate or authorize spending, migration, merge or cutover.

## What was actually checked

Read-only GitHub inspection covered all 18 open draft PRs, their exact head/base relationships, submitted reviews and reported commit statuses; both full candidate trees; cumulative file changes; production/staging configuration; migrations; registered-workflow and provider boundaries; and published acceptance/release evidence.

No production server or retained Windows runtime was connected. This assessment environment has neither Docker nor psql. No build, application test, migration, database inspection, provider request, algorithm, accounting amendment or deployment was performed. Earlier passing tests remain published historical evidence, not newly run checks.

## Frozen source and historical production comparison

| Component | Source for this assessment | Meaning |
| --- | --- | --- |
| Portal candidate | `c0b9405657a3c64ba2b570cecb3c973ba1bcfb7e` | Includes the source-only future provider capture change; new release images still need building |
| Maintained WP3 candidate | `d533219426af9ea6defaf0bc78956741201a5109` | Review envelope; does not require deploying the experimental Portuguese worker in the first beta |
| Historical production API | `89072340c9a13f3aa49d3e433380de8928cc16dd` | Recorded in the 11 November engineering review; refresh on the server |
| Historical production web | `df5b75873326ab56cad608990f3bd4add125bcc4` | Recorded server baseline; refresh independently of API |

The historical production API image is `sha256:ded4f325be3769f834f5a40b1e3cf7f85aef0e0d25126b51d9509892cd562340`; web is `sha256:851115fb98582c8c077ed28e3b6db46c40a1079467cb4e3a11faabf5c19f2a0f`. These are **historical rollback references, not verified current images**. The local sandbox images are different and are not production defaults.

Full blob-tree comparison finds **424 changed Portal files** relative to the PR8 feature-branch base: 395 additions, 29 modifications, no deletions. The GitHub compare response returned only 300 files, so that response alone is insufficient for the cumulative manifest. Component comparisons find 109 changed `apps/api` files against the historical API source and 48 changed `apps/web` files against the historical web source. Maintained WP3 has 34 changed files relative to its recorded main base. Counts include tests and documentation; they are not a defect count.

Sources: [11 November engineering review](DESIGN_AI_BETA_ENGINEERING_2026-11-11.md), [latest local handoff](PORTUGUESE_REVIEW_HANDOFF_2026-11-17.md), [machine assessment](../deploy/release/SOURCE_ASSESSMENT_2026-11-17.json), [complete changed-file lists](../deploy/release/CHANGED_FILES_2026-11-17.json).

## Complete dependency and review order

Both chains are internally consistent: every dependent PR's base SHA equals the preceding PR's head SHA. All are drafts. No submitted reviews were returned for any of these 18 PRs. This does not identify branch-protection rules or establish that none apply; required-check policy still needs verification.

| Portal PR | Scope | Immediate prerequisite | Reported commit status |
| --- | --- | --- | --- |
| [8](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/8) | Gated AI foundation | Production UI feature branch | Vercel failure |
| [9](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/9) | Instance settings | 8 | Vercel failure |
| [10](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/10) | Dutch qualification | 9 | Vercel failure |
| [11](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/11) | Bounded analyzer addition | 10 | Vercel success |
| [12](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/12) | Builder review usability | 11 | Vercel success |
| [13](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/13) | Goal-to-results path | 12 | Vercel success |
| [14](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/14) | Catalogue discovery | 13 | Vercel success |
| [15](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/15) | Two-operation composition | 14 | Vercel success |
| [16](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/16) | AI workspace | 15 | Vercel success |
| [17](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/17) | Restricted beta/accounting | 16 | Vercel success |
| [18](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/18) | Parameter-consumption evidence | 17 | Vercel success |
| [19](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/19) | Genuine composition acceptance | 18 | Vercel success |
| [20](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/20) | Supervised local pilot | 19 | Vercel success |
| [21](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/21) | Conversation preservation | 20 | Vercel success |
| [22](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/22) | Portuguese integration/evidence | 21 | Vercel success |

| Maintained WP3 PR | Scope | Immediate prerequisite | Reported status |
| --- | --- | --- | --- |
| [2](https://github.com/AI-EFFECT/ai-effect-wp3/pull/2) | Optional legacy parameters | Main | No commit statuses returned |
| [3](https://github.com/AI-EFFECT/ai-effect-wp3/pull/3) | Instance validation/delivery | 2 | No commit statuses returned |
| [4](https://github.com/AI-EFFECT/ai-effect-wp3/pull/4) | Experimental Portuguese adapter | 3 | No commit statuses returned |

No PR-triggered GitHub Actions runs were returned for the two candidate tips. Vercel success is not API, PostgreSQL, worker or production acceptance. Earlier evidence attributes PR8–10's Vercel failures to author/project access; current status URLs point to team invitations. Have the project owner confirm and resolve that access issue and rerun applicable checks. Do not change authorship or bypass required checks.

Review the full difference against **each current deployed component**, including any unmerged feature-branch prerequisites. Preserve existing branch histories. Merge sequencing must account for GitHub's actual base relationships after each merge; this report is not permission to bulk-merge the stack.

## Concrete release blockers and decisions

| Gate | Finding | Next action / responsible role |
| --- | --- | --- |
| Current server baseline | Historical component sources exist; fresh inventory is unavailable here | Deployment operator records current API/web/WP3 images, source labels, build IDs, schema, mounted storage, routing and configuration hashes |
| Portuguese design portability | `registered_parameters.authority()` explicitly requires `sandbox_profile_enabled()`. That guard requires database `pt_parameter_sandbox`, plus a configured owner and sandbox CSV | Developer prepares a narrowly scoped deployment registration/input-authority change for a normal staging database, with exact reviewer/service/contract/dataset scope and execution denial. Do not rename a DB or remove guards globally |
| AI operating configuration | `docker-compose.prod.yml` is byte-identical to the historical web baseline and does not pass the new AI/accounting configuration | Prepare a reviewed restricted-beta override with default-off controls, exact existing reviewer IDs, authorized target-environment candidates, private evidence sink, network policy and accounting transport |
| Spending authority | Current supported original-ledger transitions end at 28; the published session and batch are closed | Do not replay historical operator requests, reopen the batch, copy the ledger or bypass accounting. Propose any future production spending policy through a separately reviewed, supported process; keep provider disconnected during preparation |
| Staging scope | Existing `deploy/staging/compose.yaml` disables AI; its gateway also blocks AI chat and other routes | Reuse isolation/TLS/pinned-build foundations, but prepare an explicit design-only staging configuration and test matrix for this release. Do not copy that gateway to production unchanged or remove denials globally |
| Build parity | Latest capture code is source-only; old local images do not include it | Package from reviewed commits using existing pinned builders; record source manifests, dependency locks, build IDs and immutable image digests |
| Database/rollback | Additive 003–005 exist; previous restore/migration rehearsals are historical | Confirm current schema, rehearse the exact remaining migrations on disposable staging data, restore into a separate DB and verify old/new rows and binary rollback compatibility |
| Human/code review | Walkthrough not performed; no submitted PR reviews | Colleague performs the existing ten-minute walkthrough; maintainers review cumulative API/web/WP3 boundaries and changed release controls |

Code anchors: [Portuguese authority](../apps/api/app/services/registered_parameters.py), [sandbox profile/input checks](../apps/api/app/services/capability_bindings.py), [settings](../apps/api/app/core/config.py), [production Compose](../docker-compose.prod.yml), [private staging](../deploy/staging/compose.yaml), [staging gateway](../deploy/staging/nginx.conf), [historical accounting mechanism](../deploy/restricted-beta/ACCOUNTING.md).

The accounting runbook retains earlier preparation statements. Use the 16 November acceptance/closure report for the actual 28/28 closed outcome; do not interpret stale preparation prose as fresh spending authority.

## Release scope

**Target A — restricted design-only beta:** reviewed Builder/UI changes; declared per-instance settings; authorized recommendations, proposals, Apply/Undo/Save and Builder handoff for selected existing users; private sanitized provider evidence and bounded authorized accounting. New AI-composed/experimental designs must remain server-side execution-denied in the target environment. Existing production users, roles, workflows, publishing and previously supported execution behavior must be preserved.

Target A must have at least one actually authorized target-environment workflow/candidate. A local saved solution, sandbox CSV label or reviewer UUID is not production registration. If Portuguese registration portability is unfinished and no other candidate is qualified, report that beta activation is blocked; do not call a hidden AI tab the completed restricted beta.

**Target B — Portuguese execution:** separate owner-confirmed service family, endpoint/authentication if applicable, data permission, parameter semantics, contract/binding mapping, resource limits, target-specific qualification and bounded execution acceptance. It is excluded from Target A. A source dependency may need review without deploying or activating every experimental component.

## Production inventory: read-only, no secrets in reports

The operator should use the existing authorized deployment connection and the actually running Compose projects. Record UTC collection time and retain raw inventory privately.

1. Identify running API/web/WP3/worker/DB/proxy containers. Record IDs, image digests, narrowly selected source/build labels, Compose project/service labels, restart policy, state and health. Do not dump container environment, command lines or unfiltered inspect output.
2. Record deployed source tree/worktree status where available, release/configuration file hashes, image/build manifests, proxy route/TLS identity, network attachments and artifact/contract volume identities. Keep secret file contents and private paths out of public evidence.
3. Through the existing normal account, verify sign-in/role and existing journeys without starting a workflow. Record the exact existing reviewers privately. No password reset, bootstrap or ownership reassignment.
4. With read-only PostgreSQL queries, inspect table/column/index/constraint shapes, row counts and null-owner counts. Do not read user rows, session tokens, design contents or dataset bytes into a public report. Determine whether 001/002 are already applied before choosing migration order.
5. Record available backup/restore evidence, storage headroom, log retention and an operator who can perform rollback. Inventory does not create a backup or change services by itself.
6. Compare each observed component with its own historical source. Report drift before freezing a candidate. Production web metadata alone cannot identify the API or WP3 baseline.

## Staging and cutover sequence

1. Complete inventory and freeze the deployment-specific release manifest. Keep candidate image fields unfilled until actual builds exist.
2. Complete the colleague walkthrough and review cumulative changes and concrete portability/accounting scope. No further feature expansion.
3. Build immutable packages with the existing builders. Prepare an isolated staging project, database, credentials, TLS origin and networks. Do not attach production worker queues or import the Windows sandbox/ledger/evidence as staging state.
4. Rehearse backup/restore and migrations required by the observed schema. Never rely on `Base.metadata.create_all()` to add columns to existing tables. For the historical baseline the expected additions are 003, 004 and 005; apply earlier migrations only if inventory establishes the need.
5. Run the exact candidate's focused API/PostgreSQL/frontend/build checks. Test existing sign-in, RBAC, catalogue, publishing, saved Builder designs, monitoring and authorized artifact access, plus wrong-owner denial and legacy-record behavior. Explain newly blocked unverifiable legacy artifacts instead of inventing ownership.
6. Test the design-only beta with isolated provider doubles first: target registration, defaults/settings, required input, stale revision/contracts, independent IDs, Apply/Undo/Save/reopen, unauthorized reviewers, accounting outage and server-side execution denial. Verify no submission reaches WP3. Any new genuine-provider session needs applicable spending authority; historical closed permits do not cover it.
7. Rehearse API/web code rollback against post-migration disposable data. Retain additive tables and new writes; never restore an old production DB over newer activity. Determine whether this beta actually requires a WP3 runtime change; do not upgrade it by default.
8. Prepare one final cutover request identifying source/images, migration hashes, affected components, access scope, expected interruption, monitoring, rollback trigger and responsible operator. Only then approve and execute that concrete release.

## Schedule and next handoff

The earlier 5–10-working-day estimate remains provisional. Inventory, the sandbox-bound registration and an authorized post-pilot accounting policy are dependencies that can change it. Do not set a public release date until the exact target environment and implementation gap are known.

Immediate task: run [the local Codex release-preparation handoff](PRODUCTION_RELEASE_LOCAL_CODEX_2026-11-17.md). It starts with read-only production inventory and completes independent staging preparation. No extra provider or algorithm call is needed to close this source assessment.

The genuine local behavior remains PASS; the original overall provider acceptance remains PARTIAL. Independent usability, code review and target-environment qualification remain outstanding. This report changes no historical acceptance result.
