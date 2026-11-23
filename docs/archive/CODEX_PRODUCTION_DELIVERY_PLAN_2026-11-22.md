# AI-EFFECT production delivery plan

Updated: 22 November 2026. This is the current delivery baseline for reusable service parameterisation and Design with AI.

## Purpose and current decision

Deliver complete user tasks on https://platform.ai-effect.eu/. R1 is the active release target. Its next checkpoint is CP01. Production release status is **NOT READY**. CP01 is BLOCKED on unconfirmed Portuguese service/data authority and deployment/shared-staging ownership. Fresh read-only inventory, isolated R1 packaging and PostgreSQL subset evidence are recorded below; no checkpoint has passed.

The latest local foundations are Portal publication `6228504349017fc8cb730f638b9ac18f6984dd60`. That commit is not an assembled production candidate. The default branch, development sources, running demonstrations and deployed components have different identities. Publishing this plan on main does not merge development features or establish the production source.

The user requires credible demonstrable outcomes every two to three working days and production increments. Test counts, scripted conversations, saved historical demonstrations and preparation reports support delivery; they do not complete a production checkpoint.

## Releases and target dates

Dates are planning targets in Europe/Dublin, assuming work starts 23 November, one focused developer, deployment support and timely service/data-owner access. CP01 must confirm or revise them from observed gaps. They are not deployment promises. Record a missed gate, its consequence and revised date; never silently move a date or weaken acceptance.

| Release | Production target | Complete user outcome | Scope and required live demonstration |
| --- | --- | --- | --- |
| R1: Configurable service execution | 4 December 2026 | An authorised designer opens a supported solution, selects permitted input, changes settings manually, explicitly Runs and inspects results belonging to that configuration. | One real approved service family. Run two configurations through the ordinary portal. Show submitted and effective settings, evidence of actual consumption, associated outputs and unchanged first-run history. AI stays disabled for the new release scope until R2 acceptance. |
| R2: AI-assisted configuration and execution | 11 December 2026 | The designer uses chat on the same saved solution, selects the intended instance, resolves invalid input, reviews and saves a change, explicitly Runs and sees its results. | R1 remains usable manually. Use a fresh genuine conversation on the release build, with bounded shared spending, correct selection/guidance, ordinary accounts and the normal execution/results path. |
| R3: Reusable onboarding and solution building | 18 December 2026 | A provider publishes reviewed settings and input/output definitions; a designer uses another node's service through the same process and completes a supported connected solution. | A second independently supported real service family, normal provider/admin onboarding, compatible connections and actual execution/results. No portal branch keyed to a particular node/service. AI-assisted construction is accepted only for the supported combinations actually demonstrated. |

Portuguese services are the intended R1 execution candidate. CP01 must establish their real endpoint, runtime support, permitted data, parameter semantics and accountable owner. If unavailable, record the dependency and obtain the product owner's decision before changing the release family. Never substitute a synthetic fixture and report the release complete.

R3 does not promise automatic configurability or arbitrary compatibility for every catalogue service. Document supported services/interfaces and unresolved node dependencies.

## Checkpoint tracker

Only observed requirements advance a status. Planning, historical evidence and partial local checks do not mark a checkpoint passed.

| ID | Due | Release | Required observation | Responsible roles to name at CP01 | Status | Fresh evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| CP01 | 24 Nov 2026 | R1 | Read-only current deployment inventory; exact candidate/integration gaps; first real service/data and parameter confirmation; staging/deployment access; named owners. Confirm or revise release dates. | Implementer, deployment operator, service/data owner, product owner | BLOCKED | [22 November CP01 evidence](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/74bacf229fc9343b9d824bf65a0a8e99f74c6e55/docs/R1_CP01_2026-11-22.md); current inventory refreshed; candidate packaged. Service/data approver and deployment/shared-staging operator unconfirmed. 4 Dec unconfirmed; no defensible revised date without owner/access ETA. Application baseline a257508; packaged candidate a8a2674.  |
| CP02 | 26 Nov 2026 | R1 | Ordinary authenticated browser journey in isolated shared staging: configure, Run, inspect actual output. Identify submitted/effective values and the specific remaining blocker if incomplete. | Implementer, service owner, independent walkthrough reviewer | BLOCKED | Owner-approved Portuguese runtime/data/contracts and shared-staging access unresolved. 26 Nov at risk; historical fixture Runs do not verify this release build.  |
| CP03 | 1 Dec 2026 | R1 | Exact candidate on the production database technology; existing-data migration rehearsal, account/ownership checks, concurrent/stale edits, repeated runs, retained results, backup/restore and binary rollback. | Implementer, deployment operator, reviewer | IN PROGRESS | [22 November CP01 evidence](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/74bacf229fc9343b9d824bf65a0a8e99f74c6e55/docs/R1_CP01_2026-11-22.md); six local PostgreSQL16 checks and synthetic backup/restore passed. Production-data rehearsal, repeated real Runs and previous-binary rollback remain NOT VERIFIED.  |
| CP04 | 3 Dec 2026 | R1 | Concrete release package: exact Portal/API/WP3/node versions and image identities, required migrations/configuration, permitted users/services/data, passing applicable checks, rollout/rollback and responsible operator. List every unresolved defect and release decision. | Release reviewer, deployment operator, product owner | IN PROGRESS | [22 November CP01 evidence](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/74bacf229fc9343b9d824bf65a0a8e99f74c6e55/docs/R1_CP01_2026-11-22.md); exact local API/web images and guarded manual overlay prepared, AI off. Current WP3/node package mapping, permitted cohort/data and accountable operator/reviewer remain unresolved.  |
| CP05 | 4 Dec 2026 | R1 | Authorised production rollout, followed by the ordinary-user two-configuration walkthrough on the actual deployed version. | Deployment operator, independent reviewer | NOT VERIFIED | None recorded for this plan. |
| CP06 | 8 Dec 2026 | R2 | Genuine current-build setting edit, explicit instance choice, valid/invalid guidance, no-change, boolean/saved-edit and ordinary informational/workflow-question behaviour; review/save followed by actual Run/results in staging. | Implementer, AI spending owner, reviewer | NOT VERIFIED | None recorded for this plan. |
| CP07 | 10 Dec 2026 | R2 | Review exact R2 package, shared-user ownership, concurrent quota admission/settlement, expiry, uncertain requests, outage behaviour, R1 regressions and disable/rollback controls. | Implementer, spending owner, deployment operator, reviewer | NOT VERIFIED | None recorded for this plan. |
| CP08 | 11 Dec 2026 | R2 | Authorised production rollout to the named cohort; fresh real conversation through explicit Run and linked results with spending recorded. | Deployment operator, independent reviewer, spending owner | NOT VERIFIED | None recorded for this plan. |
| CP09 | 15 Dec 2026 | R3 | Another node's provider completes normal onboarding and confirms settings/I/O/runtime/data; no special portal service-ID code is required for the supported interface. | Second service/data owner, implementer, administrator | NOT VERIFIED | None recorded for this plan. |
| CP10 | 17 Dec 2026 | R3 | Ordinary designer builds a genuinely compatible connected solution through the shared manual/AI path; selected data, actual execution, associated results and earlier-family regression acceptance succeed in staging. Review exact release package. | Implementer, service owners, independent reviewer, deployment operator | NOT VERIFIED | None recorded for this plan. |
| CP11 | 18 Dec 2026 | R3 | Authorised production rollout and independent provider-to-results walkthrough. Publish the exact supported-service/interface boundary. | Deployment operator, independent reviewer, service owners | NOT VERIFIED | None recorded for this plan. |

Owners are not assigned by this document. CP01 must name actual people for implementation, deployment, service/data approval, product decisions, independent acceptance and later AI spending. Missing owner/access is a blocker, not a hidden assumption.

## Evidence required to pass

Each checkpoint record must contain:
- Collection date, exact source commit(s), actual running build/image identities and environment. A commit alone does not identify running code.
- A normal-user walkthrough, fresh run/solution identifiers and observed outputs where execution is in scope.
- Permitted input reference, service/contract version, requested/submitted/effective settings and evidence that the actual operation consumed them. Explain provider-approved normalisation; do not hide a changed value.
- Relevant positive and negative checks on the exact candidate, including ownership and stale/concurrent behaviour as applicable.
- Evidence links and the remaining defects, dependencies, responsible person and next action.

A number need not alter the output on every dataset. Actual consumption and service semantics are the criterion. Never infer execution from a healthy endpoint, successful compile, saved setting or model claim.

Use statuses NOT VERIFIED, IN PROGRESS, BLOCKED, FAILED or PASSED. PASSED requires the observation above. Use RELEASED only for the release itself after authorised deployment and live verification. Separate source implemented, locally verified, staging verified and production verified.

Store sanitised evidence in reviewed repository files or accessible CI artifacts. Keep credentials, raw personal data, private database copies and operator secrets out of Git. User account or endpoint details must be appropriate for this public repository.

## Work selection and drift control

At the start of every delivery pass:
1. Read this plan, its latest checkpoint log, the active branch/worktree instructions and the latest failed/blocked evidence.
2. Establish actual branch/commit, dirty work, running version and applicable spending state. Preserve retained demos, historical results and closed ledgers.
3. State the active release/checkpoint, the previous problem and the smallest observable result that advances it.
4. Implement necessary release work, verify it and update the tracker/log. Do not stop after writing another plan when implementation is possible.

R1 deployment/integration and real execution are the priority. Remaining conversational repairs belong to R2 unless evidence shows a direct R1 dependency. Do not expand AI frameworks, authentication replacement, additional demonstrations, service families or unrelated UI work to avoid the current blocker.

If a new issue appears, record whether it blocks the active release, belongs to a later release or is unrelated. Carry unresolved blocking work into the next pass. Do not switch the active target silently. Explicit new user instructions take precedence; record the resulting scope/date decision.

Do not bulk-merge the historical PR stack. Assemble only the required reviewed changes into a coherent candidate. Preserve existing production users, workflows, publishing, inputs and historical outputs.

This plan does not authorise paid model calls, new cloud purchases, production migrations, runtime contract activation or cutover. Continue reversible implementation and offline checks under existing task authority. Obtain any separately required concrete spending/deployment authority only when the candidate and limits are ready to review. Never reopen a closed spending scope.

The 8 am daily automation remains paused. This document creates no scheduled execution. A future status report must read the latest checkpoint and prior failure first.

## Known baseline and unresolved work

Historical evidence is retained with its original scope:
- [Latest offline guidance correction, 22 November](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/6228504349017fc8cb730f638b9ac18f6984dd60/docs/SETTING_VALIDATION_GUIDANCE_2026-11-22.md): invalid request -> published guidance -> valid choice -> browser save/reopen; no current genuine-model proof.
- [Genuine target-choice execution](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/f4674e48eda79f740a2ae9e80cf67572ce38099f/docs/SETTING_CHOICE_EXECUTION_2026-11-21.md): real South-only edit and browser persistence passed; invalid clarification failed; E/F unattempted; scope closed.
- [Release gaps and observed production baseline, 19 November](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/6228504349017fc8cb730f638b9ac18f6984dd60/docs/RELEASE_GAPS_AFTER_GENUINE_JOURNEY_2026-11-19.md): source consolidation, packaging, database, provider/data approval, concurrency, operations and release gaps. Its production inventory is dated, not current verification.
- [Broader implementation and execution checkpoint](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/6228504349017fc8cb730f638b9ac18f6984dd60/docs/PRODUCT_ALIGNMENT_AND_DELIVERY_2026-11-18.md): reusable foundations and historical real-runtime evidence, with remaining limits.

An additional R2 concern observed in the latest router: all clarification/unsupported responses are routed to setting guidance, potentially replacing useful workflow-level questions; informational answers in a selected-setting context also need coverage. Verify and narrow that boundary as necessary. This concern does not justify delaying independent R1 manual execution/release preparation.

The reset requirement remains generic service parameterisation and AI-assisted solution building on one saved solution. The existing public portal and WP3 foundation are retained. Separate local successes must not be combined into an unobserved current-version end-to-end PASS.

## Checkpoint log

### 22 November 2026 — delivery baseline recorded

- Active release/checkpoint: R1 / CP01.
- What worked? Published historical reports establish reusable local foundations and narrow demonstrations.
- What failed? No complete production candidate or current end-to-end release acceptance is established. Prior work overemphasised isolated conversational outcomes.
- What can I demonstrate now? The preserved genuine and offline local demonstrations identified above; no newly released production enhancement.
- What specific problem are we tackling next? Refresh the release/deployment and Portuguese service/data facts, name owners, and assemble R1's manual configuration-to-results candidate.
- Evidence scope: repository documentation review only. This entry claims no new application test, provider call, workflow Run, staging acceptance or deployment.
- Schedule decision: target dates above remain unconfirmed until CP01. No checkpoint marked PASSED.

### 22 November 2026 — R1 architecture and launch review

- Active release/checkpoint: R1 / CP01; status remains NOT VERIFIED. This is a source/evidence review, not a fresh runtime or production observation.
- What worked? Existing canonical saved-solution, parameter validation, explicit execution and owned-results foundations should be reused. The Portuguese report records two real DGAN qualification runs.
- What failed? Those runs did not establish a normal designer Run. Portuguese contracts remained draft with provider attestations false, and their published test bounds were software fixtures. Requested batch 16 became effective batch 8. Source defaults and successful fixture runs must not be treated as production approval.
- What can I demonstrate now? Preserved historical local demonstrations only; no new R1 release proof from this review.
- What specific problem are we tackling next? Establish one reviewed Portal/WP3 candidate and the real Portuguese service/data authority; fix the first observed blocker in the ordinary manual configuration-to-results path, or complete independent packaging/migration work if owner/access is missing.
- Scope decision: keep the generic platform foundations; avoid an R1 rewrite, service-ID exception, new evaluator framework or R2 conversation repair. AI disabled for the R1 release scope means no paid-provider acceptance is on its critical path.
- Resource discipline: use targeted source reads and focused checks. Reuse the candidate, existing run path and existing tools. Publish one concise checkpoint update per pass; do not create a new general plan, launcher or evidence harness for each minor issue. Preserve affected historical state without copying entire environments unnecessarily.
- Schedule: 4/11/18 December remain targets pending CP01. No production date is confirmed by this review.
- Evidence: [Portuguese qualification, fixed source](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/6228504349017fc8cb730f638b9ac18f6984dd60/docs/WINDOWS_PORTUGUESE_QUALIFICATION_2026-11-18.md).

### 22 November 2026 — CP01 current inventory and isolated R1 package

- Active R1 / CP01 is **BLOCKED**. Packaged Portal source `a8a2674bab8f9b752ded2bf1edb17352f166b751` selects normal-designer base `a25750807bdcd0e386ae75fd2cbc8d53df1ea4bd`; paired clean WP3 `69f7408e12908eb85a5de50af037e4f134e2be49`. This does not identify deployed production code.
- What worked? Fresh authorised read-only production inventory, a coherent AI-disabled manual candidate, read-only schema startup gate and existing additive migration packaging. Six local PostgreSQL checks, synthetic separate backup/restore, 96 component and 58 web checks/typecheck/build passed; immutable local API/web images and packaged-source checks are recorded in the linked evidence.
- What failed? Production lacks the saved-design column/execution tables; that boundary is fixed in the package, not migrated in production. Deployed Portuguese image differs from qualified local DGAN. Zero production parameter contracts; endpoint/capability/data/limits and accepted batch normalisation remain unconfirmed. Initial fixture setup and web recipe guard failures are retained in evidence with their corrections.
- What can I demonstrate now? Preserved 23124/23125 demos and historical 23126 ordinary-browser real DGAN SOFTWARE FIXTURE results, plus the isolated PostgreSQL/package checks. No fresh R1 browser Runs/shared-staging acceptance, partner approval or production enhancement is claimed. Retained evidence/closed ledgers and dirty originals were preserved.
- What specific problem are we tackling next? Name Portuguese service/data approver and deployment/shared-staging operator (both explicitly unconfirmed by the user); obtain reviewed endpoint/runtime/connector/data/settings approval and shared staging access; then verify two actual configurations through ordinary sign-in/save/Run/owned results. Product decision and independent reviewer remain unassigned. Continue exact WP3/node packaging and existing-data/previous-binary rollback independently; no R2 repair.
- Date impact: CP01 due 24 Nov BLOCKED; CP02 due 26 Nov BLOCKED/at risk; CP03/CP04 IN PROGRESS only. 4 Dec remains unconfirmed and cannot be defensibly revised until owner/access ETAs and staging/rollback/release-review work are established. CP01 must resolve the date decision. No production writes, activation, workflow Runs or paid calls were authorised/performed.
- Evidence: [CP01 report and exact image/source identities](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/74bacf229fc9343b9d824bf65a0a8e99f74c6e55/docs/R1_CP01_2026-11-22.md), [sanitised observations/checks](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/74bacf229fc9343b9d824bf65a0a8e99f74c6e55/docs/verification/r1-cp01-20261122.json). Only this checkpoint entry is appended for this delivery pass.

### Required format for each subsequent pass

Append a dated entry containing the active release/checkpoint, source/running version, previous failure, actual changes, observations/evidence links, blocker/owner, date impact and these four answers:

1. What worked?
2. What failed?
3. What can I demonstrate now?
4. What specific problem are we tackling next?

Update the corresponding tracker row. If blocked, record the minimum missing access, service decision or repair; continue independent work that advances the same release. Leave unobserved steps NOT VERIFIED. A failed checkpoint remains visible after correction, with a separate fresh verification record.
