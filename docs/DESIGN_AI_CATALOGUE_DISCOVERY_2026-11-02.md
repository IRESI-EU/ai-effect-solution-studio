# Catalogue-grounded discovery and clarification

Separate review milestone, stacked on PR #13 at `2c9ba3e648d3782cb5db760a0378d3dc612af2cf`. Tested implementation: **`2e40306e2497dcd55077056758960e3d779eb625`**. Later commits in this branch record documentation only. The completed consolidation, built staging images and original live acceptance are unchanged.

## What a user can do

Describe an objective in the existing Design with AI conversation. The provider can select an advertised capability, ask a specific clarification, or return no supported match. Discovery no longer selects a country or silently substitutes the sample-grid experiment. A useful service match can be explained even when the application cannot create an experiment from it.

The existing registered Dutch generator → benchmark is still the only qualified creation path in this milestone. When enabled and currently authorized, its recommendation carries a supported user-selected seed and an authority fingerprint. Explicit Create delegates to the established copy/proposal/Apply/Undo/Save path; readiness and execution remain separate existing actions. This work enables no execution or spending.

Catalogue-only recommendations display purpose, required inputs/settings, contract uncertainty and the absence of a supported creation path. Create is disabled. Active contracts, matching formats and similar display names do not establish composition or runtime availability. No new runtime adapter, graph synthesis, branching, onboarding or AIE-38 structural permission is added. Legacy configured-template clients and existing draft editing remain supported.

## Authority and data boundary

- The authenticated private MCP tool `discover_catalogue_capabilities` reads existing service visibility, approval/lifecycle state and operation contracts. It separately projects services, uniquely resolved supported operations, and operator-registered workflows with an existing creation path. Shared service discovery contains no country/operation-name special cases; the existing qualified workflow adapter remains a legacy registration.
- At most 40 eligible visible service records are considered in stable order; the projection is capped at 24,000 JSON characters and explicitly discloses truncation. Contract projections support at most eight inputs, outputs and settings each. Oversized, ambiguous, invalid or credential-bearing contracts stay unresolved; required information is never silently omitted from a resolved contract. This is a bounded catalogue view, not an exhaustive catalogue search.
- Only allowlisted purpose/input/setting/connection metadata is projected. Credentials, source references, internal addresses, filesystem paths, artifact contents and runtime configuration are excluded. Descriptions/history remain untrusted data. The model receives no network-fetching or execution tools; catalogue text cannot cause a tool invocation. Its output may select only server-advertised candidate IDs.
- Structured outcomes are `clarification_needed`, `supported_recommendation` and `no_supported_match`. Inconsistent output, invented selections and missing registered-workflow settings are rejected. The provider selects the outcome/candidate/question; server-validated facts supply recommendation and creation claims. A no-match response cannot promote an invented service from free-form provider prose.
- The server refreshes authorization after the provider wait and compares the selected candidate's current authority fingerprint. Create locks/rechecks the source, catalogue and contracts before writing a draft. Generic and legacy registered Create share the complete fingerprint, including runtime metadata. Stale or inaccessible recommendations fail without creating a draft. Existing row-locking behavior is reused; this milestone adds no claim of newly verified PostgreSQL concurrency.
- Runtime and data availability are **not checked** by discovery or recommendation. Parameter values are not invented for catalogue-only services. Registered creation requires the supplied supported seed; otherwise the provider must clarify. A matching service is not automatically an executable workflow.

## Actual checks

| Check on the implementation above | Actual result |
|---|---|
| New discovery/clarification/privacy/stale-authority regressions | **39 passed** |
| Related legacy, provider SDK serialization, draft/settings/structural editing and registered journey regressions | **103 passed** |
| Combined focused backend run | **142 passed**, zero failures/errors/skips; SQLite and explicit provider/runtime doubles |
| Frontend conversation storage, creation request, allowance/navigation and static React rendering | **17 passed**, zero failures/skips |
| Typecheck using retained installed dependencies | **Passed**, `--noEmit --incremental false` |
| Gitleaks on the staged implementation | **No findings**; existing exact exceptions unchanged |
| Preservation | **250 file hashes unchanged**, retained native web build unchanged, shared allowance **13/13**, zero outstanding reservations |

The new test module forbids network connections, permitting only Windows asyncio's authenticated ephemeral standard-library socketpair. Application DB access uses the existing in-memory SQLite harness. The second capability family is explicitly **synthetic demand-study metadata**, with no qualified creation path. Test doubles are confined to tests; no production phrase-to-response assistant or fallback was added. Static rendering uses the already-installed Next compiler in memory and starts no application.

Focused backend files: `test_catalogue_discovery.py`, `test_design_ai.py`, `test_design_ai_provider.py`, `test_guided_dutch.py`, `test_guided_provider_context.py`, `test_prompt_first_discovery.py`, `test_targeted_instance_edit.py`, `test_structural_composition.py`, `test_goal_to_results.py`. Set `PYTHONPATH=apps/api`, then run these with the existing host Python, `-p no:cacheprovider` and a fresh private `--basetemp` directory. No configured runtime/evidence database is used.

Frontend checks use the existing Node 24 host and `--experimental-test-isolation=none --test` with `app/design-ai/{session,allowance}.test.ts`, `lib/experiment-journey.test.ts` and `components/discovery-recommendation.test.cjs`, relative to `apps/web`. Typecheck is the retained `apps/web/node_modules/typescript/bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json` from repository root. No dependencies were acquired or upgraded.

Initial failed attempts remain in private logs: missing `PYTHONPATH`, Windows socketpair/temp-directory permissions, Node subprocess isolation and test compiler resolution. The first compatibility pass also caught the legacy unknown-selector status and the expected private tool inventory; both were corrected before the final passing run. Existing FastAPI/Pydantic/SQLAlchemy deprecations and Node module-type warnings remain visible. Full historical inventories were not rerun.

Raw logs, JUnit and preservation manifests remain in `<original-checkout>/local-backups/catalogue-discovery-20261102/`; no private files are published. [Sanitized machine evidence](DESIGN_AI_CATALOGUE_DISCOVERY_EVIDENCE_2026-11-02.json) records the exact implementation and checks.

**Unavailable verification:** no paid/provider interpretation, integrated browser demonstration, PostgreSQL concurrency, live runtime qualification or independent participant walkthrough occurred. Docker/API recovery remains separate and unresolved; no new feature build/server/profile/port was created. The existing native build still serves its retained earlier source. This feature is not in the already-built staging images, and no staging provisioning or certificate trust occurred. Production compatibility remains unverified.

## Three short review conversations

Illustrative review scripts, **not real-provider transcripts**:

1. **Existing qualified workflow:** “Create a sample electricity grid using seed 43 and benchmark it.” → Recommend the existing registered generation → benchmark workflow with seed 43; availability remains unchecked. Offer explicit Create, then preserve proposal review/Apply/Undo/Save. No experiment executes through discovery or saving.
2. **Clarification and a catalogue-only match, synthetic fixture:** “I want to study demand.” → “Which data source should this study use?” User: “I have hourly electricity-demand observations.” → Explain the synthetic demand-study capability and its required observations/settings; no supported creation path, Create disabled. This fixture establishes neither a genuine additional qualified capability nor real-provider understanding.
3. **Unsupported goal:** “Control a live plant and guarantee optimality.” → No supported match in the advertised capabilities. Do not substitute the sample-grid workflow or create a draft.

## Recommended task status only

Recommend **In Review** for this bounded catalogue-discovery/clarification milestone and the associated catalogue-contract review. Keep broader **AIE-38 composition incomplete / In Progress**; this is not arbitrary composition or live interpretation acceptance. AIE-18 remains **In Review**. Independent usability and production compatibility remain unverified. No Confluence/Jira/tracker update, merge or production change was made.
