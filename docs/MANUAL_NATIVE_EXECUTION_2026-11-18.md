# Manual parameterisation to native execution — 18 November 2026

The next implementation increment connects the provider-reviewed parameter card to a real native Control runtime and its results. The isolated manual **API journey works** with the actual Danish topology enumeration and SVG rendering code, real HTTP calls and native Redis. Browser/human acceptance, Danish owner qualification, PostgreSQL verification and production deployment are still pending. Chat integration is unchanged.

## Observed journey

The automated walkthrough signs in through ordinary authentication as separate provider, administrator and designer users. The provider onboards GenerateTopology and RenderTopologies through normal manifest publishing; the administrator approves those disposable service records. The provider publishes and exports the reviewed parameter definition. The test node installs that exact export. A designer saves a solution, supplies structured input, checks readiness and explicitly submits the saved workflow through `/workflows/submit-to-orchestrator`.

The unchanged WP3 engine and Worker then call the real service endpoints. The enumerator and renderer execute; results are inspected through the existing owned preview and instance-evidence endpoints. No HTTP/algorithm/storage doubles are used in this walkthrough. The Portal database is the existing isolated SQLite test harness; native Redis 6.2.14 holds the real workflow state and queue. These disposable actors, approvals and numeric limits are test fixtures, not Danish node approval.

| Same saved solution | Requested cap | Algorithm argument | Generated topologies | SVGs |
|---|---:|---:|---:|---:|
| First explicit run | 1 | `max_results=1` | 1 | 1 |
| Edit, Save and second explicit run | 3 | `max_results=3` | 3 | 3 |

The recorded run IDs and output hashes are in [the sanitized execution checkpoint](verification/native-control-execution-20261118.json). The first submission and result bytes remain unchanged after the second run. Different owners cannot inspect them. Altering the disposable first-run artifact is detected; restoring its original bytes restores valid inspection. These are new source-runtime executions, distinct from all retained meeting/Portuguese/Dutch demonstrations.

## Product changes

- Normal provider publishing now offers **Download runtime contract** for an active card with a current provider review. Draft, changed-runtime, unreviewed and unauthorised exports are rejected. Exporting does not deploy anything.
- Native Control handlers recognise the existing configuration envelope, expose declared capabilities behind existing authentication and reject unsupported/malformed configuration before dispatch. Services without declared support no longer silently discard configured settings. Valid unconfigured calls retain their existing path.
- GenerateTopology loads an operator-installed contract with `SERVICE_PARAMETER_CONTRACT_FILE`. There is no built-in identity, version, default or numerical limit. It explicitly maps the three supported names to the actual enumerator arguments. The copied parameter validator is byte-identical to the maintained core, with checked provenance.
- Reviewed instance settings override upstream routing defaults. Supplies/loads and the upstream artifact are preserved. Output records distinguish requested/effective settings, actual arguments, input hash, contract digest and workflow/task/instance identities. Renderer outputs retain the producer record.
- Configured external service-task identities include the workflow identity in a deterministic hash. This fixes collisions when the same saved design runs again: WP3's logical task IDs remain the same, but the service task and result file belong to the new run. Completed configured files cannot be overwritten by replay or by stripping configuration.
- The Portal's existing instance-evidence path checks generic native JSON instrumentation against the immutable submission, observed task identity, exact input references/content and its existing digest receipts. It checks the recorded runtime destination before reading current runtime observations. This is provider/runtime argument instrumentation, not independent scientific qualification. It introduces no node-ID registry, new evidence table or execution bypass.
- Owned result preview now recognises maintained WP3's top-level `output_refs` as well as legacy result forms. Input and reference metadata do not confer output authority. Existing authentication, ownership, workflow namespace and read-only artifact-root checks still apply.

The verified local composition is the source-documented generator-to-renderer chain with a structured run configuration. This preserves its existing legacy connection path; it does not claim arbitrary JSON-labelled services are compatible. A second independently parameterised runtime and broader typed composition are still required for the generality milestone.

## Node/operator dependency

The matching WP3 development branch is `codex/native-control-configuration-20261118`, based on `d533219426af9ea6defaf0bc78956741201a5109`. Its runtime guide describes installation boundaries. The Portal continues on `codex/reusable-provider-onboarding-20261117`, after `4f6d75c3c4bda7451eade0c913ca0ef6a5ec8931`. Both source changes must be reviewed together; these are not instructions to bulk-install the inherited draft stack.

The Danish owner must still confirm the canonical operation identity/version, meanings, defaults, limits, resource suitability, deployed image and normal/invalid configuration tests. Existing source defaults differ between the configuration assistant and topology handler. Nothing in this increment turns those into provider-approved defaults. Only `allow_hx`, `allow_bypass` and `how_many` are mapped; other generator options need deliberate mapping/review.

The node operator must install the matching runtime and mount the exported contract read-only. File-based results require the actual shared data volume to be available read-only to the Portal artifact reader. Without the runtime/card match, readiness fails; without artifact access, consumed values are reported as inaccessible rather than verified. This source path does not establish safe multi-process TaskManager operation: the existing single-process in-memory service limitation remains. A runtime restart can make status inspection unavailable; saved Portal submissions are retained.

## Verification and remaining acceptance

Focused checks cover the ordinary API journey, source-backed enumerator consumption, renderer output, repeat runs, immutable history, stale/mismatched configuration, ownership, reference metadata, input identity and digest conflicts. Existing configuration/ControlClient regressions pass; frontend TypeScript checking and production build pass. The optional native verification dependency file is `apps/api/requirements-native-test.txt`; production dependency manifests and lockfiles are unchanged.

The exact tests are `apps/api/tests/test_native_control_execution.py`, `test_native_instance_evidence.py`, the parameter/onboarding/preview/result suites and WP3 `tests/test_native_control_parameters.py` plus existing orchestrator transport tests. The real execution test is opt-in with `WP3_SOURCE_ROOT` pointing to the matching isolated checkout. All native HTTP/Redis processes are cleaned up after the test. Core validator synchronization is checked with `deploy/aie18/sync_wp3_contract.py --wp3-root <checkout> --check`.

**Status:** source implemented; real local API execution and linked results verified. Normal browser walkthrough remains unverified in this environment. Independent human review, PostgreSQL/Docker/partner-hosted qualification, exact production source inventory and deployment remain unperformed. No production change, paid-provider call, new spending scope or modification of the retained Windows demo occurred. Chat-assisted editing and the second independently configurable family remain incomplete.

## WP3 publication handoff

The connected GitHub integration rejected direct WP3 source publication with `403 Resource not accessible by integration`. The local WP3 implementation is committed as `9e07ea4`; no upstream WP3 ref was changed. The [exact WP3 patch](../deploy/patches/wp3-native-control-configuration-20261118.patch) is retained with this Portal increment so a maintainer can publish the paired runtime change without reconstructing it.

The patch applies to base `d533219426af9ea6defaf0bc78956741201a5109`. A fresh isolated worktree at that base was created and `git am` completed successfully. Its resulting source tree exactly matches the verified implementation: `cd4fb05d4eae62a91ca8f9af1481b54736f2b16f`. Apply it only to a separate clean branch/worktree; preserve existing dirty and demonstration checkouts. Direct upstream WP3 write access is still needed to publish that branch. This limitation does not change the local execution findings or authorise deployment.
