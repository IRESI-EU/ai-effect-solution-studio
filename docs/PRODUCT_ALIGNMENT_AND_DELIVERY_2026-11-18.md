> Latest offline correction: [Ambiguous setting target choice — 20 November 2026](SETTING_TARGET_CHOICE_2026-11-20.md). Application-enforced choice preserves earlier pending work; offline browser South-only Apply/save/reopen passed. Genuine case 5 remains failed, cases 6–10 unattempted and spending CLOSED.

> Latest execution checkpoint: [Genuine setting interpretation —20November2026](SETTING_INTERPRETATION_EXECUTION_2026-11-20.md). Cases1–4 passed and case1 passed browser Apply/save/reopen; case5 guessed an ambiguous target. Scope CLOSED; cases6–10 NOT_ATTEMPTED.

> Latest preparation checkpoint: [Frozen setting interpretation acceptance —20November2026](SETTING_INTERPRETATION_ACCEPTANCE_2026-11-20.md). Ten cases prepared; zero metered calls; genuine interpretation remains unverified.

# Product alignment and delivery checkpoint — 18 November 2026

> Latest bounded delivery: [20 November trustworthy setting edit](DAILY_DELIVERY_2026-11-20_TRUSTWORTHY_SETTING_EDIT.md) — application diff/review/Apply-and-save/reopen demonstrated in the local browser with offline response replay; genuine model interpretation remains unverified. The 19 November J2 failure stays historical and closed.

> Later same-day delivery: [Portuguese-priority onboarding](DAILY_DELIVERY_2026-11-18_PORTUGUESE_ONBOARDING.md) implements source-query discovery and records the revised priority, concrete demonstration and runtime dependency.

Baseline: the approved eight-page **AI_EFFECT_Product_Reset_and_Delivery_Plan.docx**. This checkpoint supersedes current-status statements in the earlier onboarding and native-execution checkpoints; those files remain historical evidence.

The reusable parameter core and native execution work fit the target. The earlier chat workspace still used a separate pilot draft, registered workflows and paired composition. Those remain retained regression evidence, not the architecture for the normal product. This pass connects normal chat to the canonical saved Builder solution and corrects a circular onboarding dependency. It does **not** establish the product Definition of Done or production readiness.

## Findings and decisions

| Area | Assessment | Decision in this pass |
| --- | --- | --- |
| Parameter core | Typed definitions, one validator, contract pins and compiler delivery are reusable. | Keep them. No service-specific portal settings or duplicate parameter validator. |
| Provider qualification | A draft required runtime confirmation, but the installable runtime contract was only downloadable after publication. | Save definitions first; export a draft qualification contract for isolated node testing; confirm actual checks against the exact saved definition/runtime; publish after normal service approval. |
| Review protection | The generic registry could create an unreviewed parameter draft. | Activation of new parameter drafts now requires the provider review and runtime attestations. Existing active contracts are not modified. |
| Manual execution | Real native generator and renderer consume saved settings and produce associated immutable results. | Keep this path and use it for assistant-applied settings. |
| Saved input | Submission compared configured nodes/edges but did not require declared saved input to match. | Reject different input before preflight/submission. New designs declaring `run_input` also pin the saved graph and revision, including fixed services. Legacy designs without an input declaration retain their established explicit input path. |
| Chat editing | Separate pilot graphs and special compositions would repeat the earlier narrowing. | Normal chat is attached to one saved Solution. Apply and Undo call the same canonical writer as Builder. No chat execution tool. |
| Compatibility | Similar JSON labels do not prove that connected services work together. | New chat connections require the existing provider-published I/O contracts and supported whole-output transport. Reject unsupported joins/cycles rather than claim execution support. |
| Evidence | Source checks and injected responses can overstate normal-user readiness. | Record automated API/runtime acceptance separately from browser, partner, live-model and production acceptance. |

## Implemented behavior

Normal `/design-ai` opens a choice of the signed-in designer's saved solutions or creates an empty normal solution. Both lead to Builder, which contains the conversation alongside manual controls. Explicit historical draft/conversation URLs and retained experimental profiles retain their old workspace. The new workspace is unavailable in those restricted profiles; their reviewer and spending scopes are not expanded.

The assistant receives a bounded projection of approved real catalogue metadata, published settings/I/O, and the selected solution's logical graph. Workflow input contents and runtime addresses are excluded from this projection. The first catalogue projection is capped at 40 services and advertises truncation. This is not an exhaustive search implementation for a larger catalogue.

The server accepts grounded proposals to rename/describe, change step labels/settings, add/remove/replace catalogue services, and connect/disconnect compatible operations. It assigns new instance IDs, preserves unspecified settings, and uses the existing validator. The request is bounded to 10 edits and 24 service instances; there is no two-operation or predefined-workflow requirement. Published input requirements are not silently satisfied with invented data.

Messages and pending edit proposals use the existing conversation persistence table, associated with the saved solution and actor. No second editable graph is introduced. A single previous-content snapshot supports guarded Undo. Pending proposals include the saved version/content digest and catalogue/runtime/definition authority digest. Apply validates again, rejects manual or catalogue changes, and writes the saved solution and conversation atomically. Provider failures and invalid proposals preserve the prior pending review. Manual changes prevent a stale Apply or Undo. Execution still requires the existing explicit Builder action.

The provider form now saves an unqualified draft without fabricated test claims. Providers can download its qualification contract before administrator approval, install it in an **isolated qualification runtime**, perform normal/invalid tests, and confirm their evidence against the definition fingerprint. Draft settings cannot be selected for designer configuration or normal Portal compilation/execution. Confirmation does not activate the contract. Publication requires the normal administrator service approval, a current review/runtime fingerprint and all qualification confirmations. Downloading does not install, approve, publish or execute anything.

## Verification

Final local verification: **172 backend checks passed**, **23 additional offline accounting/verification-guard regression checks passed**, **18 rendered UI/component checks passed**, and the Next production build (including TypeScript) passed. The shared parameter-validator byte/provenance check against both WP3 copies passed. The backend emitted existing dependency/time deprecation warnings; no failing checks remain in this suite. PostgreSQL-specific tests were not run in the SQLite harness.

The backend suite covers `test_saved_solution_assistant`, `test_native_control_execution` (both edit modes), `test_parameter_onboarding`, `test_instance_parameters`, `test_parameter_compatibility`, `test_capability_bindings`, `test_design_ai`, `test_design_ai_metadata`, `test_design_ai_navigation`, `test_design_ai_provider`, `test_targeted_instance_edit`, `test_native_instance_evidence` and `test_owned_artifact_preview` under `apps/api/tests`. Run with `PYTHONPATH=apps/api WP3_SOURCE_ROOT=/absolute/path/to/matching/wp3 pytest -q ...`. The native test dependencies are in `apps/api/requirements-native-test.txt`; use the retained hash-verified development dependency closure, not an unreviewed stack install.

The additional offline regressions are `test_design_ai_budget.py`, `test_design_ai_task_limit.py` and `test_provider_verification_guard.py`. They use disposable fixtures and do not reopen historical allowances.

Frontend commands from `apps/web`: `npm run build` and `node --test app/design-ai/page.test.cjs components/saved-solution-assistant.test.cjs components/discovery-recommendation.test.cjs`. Validator check from the Portal root: `python deploy/aie18/sync_wp3_contract.py --wp3-root ../wp3 --check`.

The sanitized real-runtime checkpoint is [saved-solution-assistant-execution-20261118.json](verification/saved-solution-assistant-execution-20261118.json).

The API walkthrough uses normal authenticated provider, administrator and independent designer roles in an isolated SQLite Portal. It registers runtime services through normal onboarding, saves an unqualified draft, downloads/installs its qualification export, observes valid/invalid real HTTP behavior and actual consumption, confirms the draft and publishes it. Node limits and administrator approval remain explicitly synthetic test evidence, not Danish owner approval.

It then runs the same saved two-service solution through real HTTP WP3, native Redis, Worker, the actual topology enumerator and SVG renderer. Both manual and assistant-mediated changes are exercised: cap 1 produces one topology/SVG; cap 3 produces three. The original submission/artifacts remain unchanged; ownership denial and artifact-conflict detection are checked. Assistant mode injects an explicit structured provider response only at the provider boundary. The actual model is not called.

A separate synthetic provider-I/O fixture constructs three connected operations through a single reviewed proposal, saves to the same solution and compiles with verified bindings. This establishes that the implementation is not restricted to a pair. It does not establish a second independently parameterised production service or genuine three-step algorithm execution.

Not established: independent browser/normal-user acceptance; PostgreSQL locking and migration acceptance; Docker image qualification; genuine paid-model prompt-to-run acceptance; partner-approved parameter semantics/limits; a second independently parameterised real service family; exact production serving source/image/migration/configuration inventory; production deployment. The workspace cannot inspect the retained Windows checkout or its engine. Those designs/results/demo were not changed.

The matching WP3 source remains the isolated local commit `9e07ea4473c655a6f58143dc55b708ed6f9b88da`. Its exact patch remains preserved under `deploy/patches/wp3-native-control-configuration-20261118.patch` in the Portal branch. Direct WP3 repository write is still unavailable through the current integration. No new WP3 changes were needed for this pass.

## Remaining delivery estimate

Estimate for the approved **first coherent supported release**, with two independently onboarded adjustable service families and useful composition: **12–20 further focused developer days, approximately 3–5 calendar weeks for one developer**. This is effort estimation, not a production deployment promise or a claim that every catalogue service/interface will be upgraded. It assumes timely runtime-owner responses and development/staging access. Waiting for external decisions is additional.

| Remaining work | Effort | Concrete milestone/dependency |
| --- | --- | --- |
| Complete supported I/O and dataset onboarding/discovery, refine normal chat interaction and recoverable errors | 3–5 days | Provider-published compatibility and authorised selected data visible to the ordinary designer; genuine model interaction accepted separately before paid calls. |
| Add a second independently adjustable real service and prove useful multi-step reuse | 4–6 days | Another provider follows the same onboarding without service-ID branches in the Portal. Dutch generation/benchmark is a candidate, subject to its owners' actual interface and runtime confirmation. |
| Assemble release from verified serving versions; qualify PostgreSQL, browser, authentication, migration and rollback | 3–5 days | Operator supplies exact Portal/API/WP3 images, revisions and environment; WP3 contribution can be reviewed/published. Preserve the retained demo and existing histories. |
| Ordinary-user acceptance, bounded live-model acceptance and release corrections | 2–4 days | Provider/admin/designer journeys on staging, real linked results for both families, then a concrete release approval package. |

Node owners must confirm meanings, defaults/limits, supported mappings, interface contracts, deployed runtime versions and actual data/output access. The Danish topology family remains the first runtime: three source-observed candidates reach its existing enumerator. Synthetic fixture bounds in automated verification are not production definitions. The Dutch family needs its own wrapper/contract and durable result qualification; the retained two-step demonstration is not enough.

Production deployment and new paid-provider acceptance remain separate explicit approval steps against concrete release/test candidates. No new provider spending or deployment is included in this checkpoint. Routine reversible implementation and offline tests continue under the existing authorisation.
