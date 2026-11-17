# Local Codex handoff — production release preparation

Continue the AI-EFFECT release preparation from the source assessment in `docs/PRODUCTION_RELEASE_READINESS_2026-11-17.md`. Read applicable AGENTS.md and the latest release/acceptance handoffs. Preserve unrelated work.

## Objective and authority

Prepare one concrete restricted, design-only production beta candidate. This pass authorizes read-only production inventory using the existing authorized deployment connection; narrow implementation and offline tests for necessary release gaps; package preparation; and publication to the existing draft PRs. Complete useful preparation before requesting any final deployment decision.

No production restart, migration, merge, cutover, new provider spending, accounting amendment or algorithm execution. Do not start/stop current production workers. Retained sandbox workers remain stopped, provider disconnected and historical 28/28 accounting closed.

## Freeze actual state first

Assessment sources: Portal `c0b9405657a3c64ba2b570cecb3c973ba1bcfb7e`; maintained WP3 `d533219426af9ea6defaf0bc78956741201a5109`. A later documentation-only release-preparation commit may sit above Portal; inspect actual heads and do not reset them.

Trace the full Portal PR8→PR22 and WP3 PR2→PR4 chains, including their base branches. Do not review only the last pair or bulk-merge. Portal PR8–10 have Vercel failures associated with project access; confirm applicable required checks and identify the owner action without changing authorship or bypassing checks.

Historical production API source is `89072340c9a13f3aa49d3e433380de8928cc16dd`; web is `df5b75873326ab56cad608990f3bd4add125bcc4`. They are different component baselines. Refresh running images/source labels/build IDs, configuration hashes, routing/TLS, mounts, schema and backup/restore identities through the existing authorized connection. Keep raw operational inventory private; publish only sanitized facts. Do not print environment, credentials, sessions or database contents. Use read-only queries and ordinary existing-account sign-in. No bootstrap, account reset or legacy ownership assignment.

If the existing connection is unavailable, report the exact missing inventory/access step, continue independent packaging/configuration preparation, and mark live checks unperformed. Do not probe for unrelated credentials or claim historical records are current.

## Resolve the actual release gaps narrowly

1. Inspect `registered_parameters.authority()` and `capability_bindings.sandbox_profile_enabled()`: the Portuguese registered path requires database `pt_parameter_sandbox` and sandbox-specific owner/CSV configuration. Determine the minimum explicit, target-environment design-registration/input-authority extension. Preserve sandbox behavior and exact reviewer/service/contract/dataset checks. Do not rename staging/production databases, copy sandbox reviewer authority or remove restrictions globally. Keep new experimental designs execution-denied. If another authorized candidate is proposed instead, state the scope change explicitly; do not invent eligibility.
2. Prepare a default-off restricted-beta production configuration using existing mechanisms. Include exact owner-selected reviewer identities, candidate registration, provider settings, private audit sink, accounting transport and outage behavior. Do not activate it. The original ledger is closed at 28/28 and supports only historical transitions; it is not production capacity. Inspect supported options and document the smallest separately reviewed policy/implementation needed for future spending. Do not reopen/copy/replace it or silently bypass accounting.
3. Reuse existing pinned build recipes. Package the current reviewed API/web sources, including future provider evidence capture, and record actual image digests/source manifests/build IDs. Never label old sandbox images as new production packages. Do not upgrade WP3 unless the concrete first-release scope requires it.
4. Adapt the prepared staging baseline explicitly: it currently disables AI and blocks chat. Preserve isolation, TLS and denial boundaries while preparing a usable design-only test setup. Do not apply the old gateway unchanged to production or remove denials globally. Do not provision or attach live production services during this pass.

Implement only necessary release portability/configuration work. Reuse existing validators, registration, persistence, accounting and packaging; introduce no new framework or general dataset subsystem. If an owner decision is genuinely needed, finish all independent work and present the exact remaining choice.

## Verify and prepare the final release gate

Use focused offline checks and provider doubles for registration portability, unauthorized/wrong-owner input, stale pins/revisions, independent instances, Apply/Undo/Save/Builder persistence, evidence capture, accounting denial and execution blocking. No genuine-provider request and no algorithm call.

Prepare migration/restore/rollback instructions from the observed schema. Historical production is expected to need additive 003–005; verify rather than reapplying 001 blindly. Rehearse only against explicitly disposable staging state if available. Preserve existing data and never restore an old DB over new writes.

Prepare the exact staging acceptance matrix for login/roles, catalogue/publishing, existing saved workflows and monitoring/downloads, legacy records, restricted AI controls, provider/accounting outage, server-side denial of new experimental execution, and code rollback. Existing production behavior must remain covered. Preserve PARTIAL historical provider evidence and leave human observations blank until performed.

Publish sanitized source/configuration and preparation evidence to the existing draft PRs; scan changed material for secrets and verify remote heads. No merge, reviewer invitation or production deployment.

Return current production baseline versus historical records; exact candidate sources/images; resolved/unresolved release gaps; prepared migration/staging/rollback plan; review/check dependencies; and the smallest remaining operator/human actions. State clearly what was prepared, built or tested and what remains unperformed. Do not request a release approval until there is a concrete candidate and sufficient target-environment evidence to assess it.
