# AIE-38 — Bounded conversational workflow composition

28 October 2026. **Offline structural milestone implemented and verified.**
Recommended status: **In Review for this milestone**. The whole conversational
composition task is not complete. AIE-18 remains **In Review**; production
compatibility is explicitly unverified. No tracker was updated.

## Supported behavior

A designer explicitly chooses **Compose a connected analyzer** from an
operator-enabled template with `structural_append_only=true`. This creates a
separate owned draft through the existing start/copy flow. It does not change the
source solution. `instance_settings_only` and structural scope are mutually
exclusive, and existing settings-only copies still reject structural edits.

The supported edit appends **one existing authorized analyzer** to the current
terminal service, binds its one required upstream input, and replaces the single
terminal workflow-output edge. This is reusable registry-driven behavior: no
Dutch service ID, operation name, slot name, schema or contract definition is
hard-coded in the mutation. The Dutch benchmark is the explicitly queued test
case. The target must have an active unique pinned `whole-output-v1` contract,
one input/output and no editable execution parameters. Existing settings remain
fixed. No new service is onboarded.

The main offline request was:

> Add a benchmark step after the grid generator and use the grid it produces. Keep the generator settings unchanged.

Pending review leaves the design at revision **0**. Explicit Apply produces
revision **1**. Undo restores the complete original design at revision **2**.
A second explicitly queued fixture, review and Apply produces revision **3**;
explicit Save, reload and Builder preserve the exact resulting graph. These
responses are provider-boundary fixtures, **not real-provider interpretation**.

## Exact design difference and preserved data

The disposable source is `aie38-one-step-source`, copied from saved AIE-37
solution `98eadd46-5b58-4517-b706-f2a7b9ed6bc4` using read-only source access and
normal owned-draft creation. Its baseline contains `input → generate-grid →
output`, with no benchmark service. Complete revision-0 designs are retained
privately; their canonical sorted-JSON SHA-256 is
`268d7394acb61dfb20f80504948667e8cd41c8f80be9464404befea52d96b4c5`.

For the saved desktop copy:

- Added instance: `c4b7cc19-cb51-455f-92e2-93b828a6cc8f`, catalogue service
  `aie37-benchmark`, operation `RunBenchmark`.
- Removed edge: `aie38-generator-output`, `generate-grid → output`.
- Added edge: `c4b7cc19-cb51-455f-92e2-93b828a6cc8f-input`,
  `generate-grid.captured_grid → c4b7cc19-cb51-455f-92e2-93b828a6cc8f.captured_grid`.
- Added edge: `c4b7cc19-cb51-455f-92e2-93b828a6cc8f-output`, new benchmark → `output`.
- The original input-to-generator edge is unchanged. All original node objects,
  positions, labels, service identity, seed **42**, configuration, contract pin,
  workflow input (**null**) and unrelated design fields are unchanged.

The original workflow-output node retains its source label, **Recorded benchmark**.
That is a design boundary label inherited from the source; it is not evidence of
a new benchmark run. The structural review explicitly shows both its removed
and added connection. No execution occurred for either copy.

| Instance | Operation contract | Version |
|---|---|---|
| Preserved `generate-grid` / `aie37-synth` | `921a87fc-329f-42b6-a546-ddf7d9c0ec26` | 1.0.0 |
| Added benchmark / `aie37-benchmark` | `441153b2-9b3b-48c1-81e4-649645f30143` | 1.0.0 |

Their identities remain `urn:aieffect:nl:configure-and-synthesize:capture` and
`urn:aieffect:nl:run-benchmark:capture`. The named binding requires identical
semantic concept, schema/version and data-reference representation, compatible
protocol/content types and cardinality one. The grid schema is
`urn:aieffect:nl:dutch-local-capture-v1:grid`, protocol `file`, content type
`application/json`. Shared JSON display labels cannot establish compatibility.
The existing AIE-37 validator/compiler remains authoritative.

## Proposal authority, review and mutation guarantees

`AssistantTurn` accepts the new edit kind `append_bound_operation`. Its `node_id`
must identify a current terminal instance. Its JSON value contains exactly
`local_ref`, `service_id`, `contract_id`, `contract_version`, `source_slot` and
`target_slot`. Extra fields, provider-supplied service metadata/definitions,
arbitrary new node IDs, projections and merge instructions are rejected.

`local_ref` is a bounded proposal-local alias. This single-add scope resolves
the target internally; it exposes no general cross-proposal graph-reference
language. The existing server UUID mechanism allocates a stable new instance ID
when the pending proposal is stored. Apply reuses that allocation. Alias/identity
collisions and targets outside the current draft are rejected.

Catalogue eligibility, caller authorization, active unique contract, explicit
slots and the complete resulting graph are checked before storing a proposal.
Review describes the added operation, named source, added and removed connections,
unchanged settings and the limits of design compatibility. It states **design
preparation only**, with runtime availability and production compatibility unchecked.

Apply uses the existing owner-scoped locked draft/revision/proposal checks.
It acquires catalogue/contract locks in deterministic service order, reconstructs
the candidate from registry authority, revalidates the complete graph and compares
the exact candidate plus catalogue/contract-definition fingerprints with review.
Changed definitions, eligibility, metadata or revision fail before draft mutation.
The transaction records one full-design Undo entry and increments one revision.
Concurrent/repeated Apply cannot add a duplicate. Existing analyzer identities
are also rejected as duplicate additions; an explicit fixture demonstrates the
correct no-edit explanation path when the analyzer already exists.

Undo restores the entire prior design, not only nodes or parameters. Save uses the
existing explicit authorized persistence path, reserved solution identity and
Builder fingerprint protection. No execution, readiness probe, runtime configuration
change, governance update or spending amendment is part of Apply/Undo/Save.

## Provider context and offline boundary

The focused context contains the authorized draft ID/revision, current instance
IDs/labels/operations/settings/pins, current connections, relevant compatible
catalogue candidates and slot definitions. The same validator determines candidate
eligibility. It excludes template payloads, workflow-input contents, unrelated
conversation history, credentials, environment files, artifact contents and private
runtime addresses. The existing redactor also protects metadata text. Catalogue
descriptions/notes are untrusted data, never instructions or authority.

The real provider remains the normal application's provider. No fixture or fallback
was installed there. The separate [offline harness](../deploy/aie38/README.md)
overrides its dependency, strictly parses explicitly queued single-use responses
and sends them through the real chat, MCP, backend validation, review, Apply and
persistence paths. Queueing binds the exact draft ID, revision, request and context.
SDK calls raise; missing/mismatched fixtures fail closed.

The harness explicitly rejects workflow submission, runtime preflight, deployment
and orchestrator routes with **403**. The unreachable orchestrator setting alone
is not relied upon. Only pure compilation is allowed. The final guard checks
exercised both workflow submission routes, runtime-preflight, deployments and an
orchestrator route; all returned 403 and created zero execution records.

## Verification

| Acceptance area | Evidence |
|---|---|
| Exact main edit and pending immutability | Provider-boundary tests; rendered desktop/narrow; complete design comparison at revision 0 |
| Ambiguous source | Valid fixture graph with two grid-producing instances; clarification returns no proposal or mutation |
| Unknown/unauthorized/ineligible operation | Strict candidate and before-Apply eligibility/authorization rejection tests |
| Wrong slots/schema/unresolved pin | Candidate tests, schema/contract drift tests and existing AIE-37 binding suite |
| Merge/projection/cycle/duplicate | Closed payload rejection and complete malformed-graph rejection tests |
| Stale revision/catalogue/contracts | Reconstructed candidate and fingerprint rejection; no partial mutation |
| Repeated/concurrent Apply | Portable repeated rejection; real PostgreSQL concurrent race has one winner |
| Full Undo | Exact baseline equality in portable, PostgreSQL and both rendered copies |
| Save/reload/Builder | Exact persisted nodes/edges; seed 42 and named binding visibly checked and design validated |
| Settings-only restrictions | Final targeted-instance regressions plus explicit structural rejection |
| Identity/cross-draft safety | Trusted UUID collision, local-alias collision, current-instance and other-owner rejection |
| Historical evidence | Immutable snapshot fixture; all five existing databases unchanged; four actual AIE-37 capture files rehashed |

- Full portable backend suite: **234 passed**, before three final additional
  structural cases. Final structural/settings-only focused suite: **44 passed**
  (28 structural plus 16 existing instance-edit cases).
- Final provider adapter/structural run: **36 passed**, one temporary-directory
  setup error. That single mocked-provider test then **passed** with an explicit
  writable disposable `--basetemp`; no product/provider failure was relabelled.
- PostgreSQL registry/input/artifact suite: **65 passed** in a fresh random
  `*_test` database. Persistence suite: **11 passed**, including structural
  concurrency. After lock ordering was tightened, the focused PostgreSQL structural
  race/persistence case passed again. Only suite-owned databases were removed.
- Existing UI utilities: **22 passed**. Final TypeScript and optimized Next
  **16.3.8 webpack build passed**. Existing deprecation/module warnings remain.
- Rendered desktop: normal login, separate-copy creation, request, readable review,
  Apply, Undo, re-propose, Apply, Save, reload and matching Builder inspected.
- Rendered narrow: the actual app in a labelled **390 × 844 CSS-pixel iframe**
  completed the same journey. Both review and Builder measured **367/367** client/
  scroll widths, without horizontal overflow. This is responsive-layout evidence,
  not physical-device interaction or independent usability testing.

The first PostgreSQL runner stalled before producing test output and was stopped;
the bounded diagnostic restart passed. A read-only ledger query initially used an
incorrect column name; it failed without writing and was corrected using the
actual schema. An early frontend encoding/library-copy issue was corrected before
the final build and screenshots. These diagnostics are not runtime/provider passes.

## Preservation, history and allowance

The before/after checkpoint compared **all tables of five existing databases**,
existing container/image identities, **156** private configuration/checkpoint/
evidence files and **195** original dirty source files. All comparisons matched.
This includes the qualification database's consumed execution permission, saved
seed-42 review solution, accounts, contracts and historical submission records.
All four raw capture files for `wf-45c1c8c84ed3` also matched their recorded SHA-256.
This does not claim a new exhaustive hash of every runtime volume.

The new profile contains zero deployments, execution submissions and local capture
records. It reused the PostgreSQL cluster and started only two host processes;
no new runtime/container stack, provider allowance or algorithm execution was created.

The original ledger is byte-for-byte unchanged, SHA-256
`c506929d99ae8b63de7e7d941d06aaac48ef27a4bea8eedc1a12fe407959b165`:
**12/12 calls**, ceiling **US$0.10**, accounted **US$0.003784750**, remaining
**US$0.096215250**, zero outstanding reservations or unsettled charges. New
provider attempts, tokens, charges, amendments and workflow executions: **zero**.
Earlier task checkpoints and exhausted states remain preserved.

## Local review and identifiers

| Copy | Draft | Saved solution | Revision |
|---|---|---|---|
| Desktop | `09e27e0b-5bfb-4de7-82b5-6c520bbf5ac9` | `ae5f2c0d-fda4-4868-9eb4-4650873f1130` | 3 |
| Narrow | `d4804225-f516-4e59-b4c0-786e2f153562` | `8910ff57-a03b-447e-b91c-c876574c3aab` | 3 |

1. Open the [desktop draft](http://localhost:23122/design-ai?draftId=09e27e0b-5bfb-4de7-82b5-6c520bbf5ac9).
   Confirm OFFLINE fixture labelling, revision 3 and Draft saved.
2. Open [its Builder](http://localhost:23122/builder?solutionId=ae5f2c0d-fda4-4868-9eb4-4650873f1130).
   Inspect generator seed 42, benchmark and the named data connection. Validate design.
3. Open the [narrow fixture](http://localhost:23122/api/offline-fixture/narrow?draft_id=d4804225-f516-4e59-b4c0-786e2f153562).
   Inspect the saved draft; follow its Builder link and check seed/binding.
4. Use a new normal copy plus an explicitly queued response to replay proposal
   review. Existing saved copies are completed evidence. Do not deploy or send
   real-provider requests. Private sign-in is in the new ignored profile only.

Screenshots: [desktop review](screenshots/aie38-review-desktop.png),
[narrow review](screenshots/aie38-review-narrow.png),
[desktop Builder](screenshots/aie38-builder-desktop.png),
[narrow Builder](screenshots/aie38-builder-narrow.png).
Exact IDs/diffs/checksums: [machine-readable evidence](AIE38_COMPOSITION_EVIDENCE.json).

## Review stack and remaining work

Separate branch/worktree: `codex/aie38-bounded-workflow-composition`,
`local-backups/aie38-portal`, based on AIE-37
`bd18c212e479084f3dc6b1f169f1163dc1631619`.
The draft PR is stacked on Portal [#10](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/10),
which depends on [#9](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/9)
and [#8](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/8).
Runtime qualification dependencies remain WP3
[#3](https://github.com/AI-EFFECT/ai-effect-wp3/pull/3) and
[#2](https://github.com/AI-EFFECT/ai-effect-wp3/pull/2); no WP3 source changed.
All five existing PR heads were rechecked and preserved.

There are no GitHub Actions workflows. Existing review branches have Vercel
Preview records; the newly observed Production record belongs to `main` at
`70168fd14bfe4fe64229b16e1d75dbc1e419457d` (a separate README update).
Publication targets only the new review branch; no existing head, production
branch, merge, force-push or deployment setting is changed.

Unsupported: arbitrary replacement/deletion, internal insertion, branching/loops,
multiple additions in one proposal, parameterized new analyzers, workflow-input
routing, multi-slot transport, conversions/projections/merges, onboarding and
general cross-proposal references. Runtime reachability, scientific/algorithm
validity, provider intent quality, independent usability and production acceptance
are separate gates. Earlier parameter-provider checks and earlier algorithm runs
are not evidence of conversational structural interpretation here.

Next bounded step: an independent human walkthrough of this offline review/Undo/
Save journey, followed by a separately authorized provider-interpretation plan if
needed. The exhausted shared allowance cannot be amended, replaced or bypassed by
this work. Production qualification and broader composition remain open.
