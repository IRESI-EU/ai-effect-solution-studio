# Portuguese Builder and supervised boundary — 2026-11-16

Later authorized recovery investigation:
[demonstrated settings-save/rename blocker and required operator observation](PORTUGUESE_RECOVERY_BLOCKER_2026-11-16.md).
Packaging and new browser acceptance remain blocked; historical results below
have not been reclassified as fresh observations.

**Source/tests prepared; retained application update and fresh browser acceptance
blocked by unavailable Docker engine. Execution remains disabled.** No new
authorization, workflow, training, generation or provider request occurred.

## Preserved checkpoint and actual availability

Both isolated review worktrees were clean and matched the recorded remote draft
heads: Portal PR #22 `643999dd46196f216c0524203d9da846d9092ad9` and maintained
WP3 PR #4 `1a6a792aa3effbfaeb979aaeaa03a7535e53e4bd`. The original checkout's
uncommitted/untracked work was left untouched. C: had 67.34 GiB free initially.
Applicable web AGENTS.md and installed Next client-component guidance were read.

The retained compose still pins Portal API/web serving source
`002686f04fb584d5bea2f1556d8e994405f1db45` and experimental runtime source
`30e1ac403c7434149f3ff3568843f2cc75702413`. Last verified image IDs:

| Component | Retained image |
| --- | --- |
| API | `sha256:22c4994a05dce43bde2472a20f73ee27605a955a28ae6085742364ad32d672be` |
| Web | `sha256:ced615705bfc07ad59fd6489491959d9b0a3ff18a54421ad9a6df6aa37d477f6` |
| Adapter | `sha256:1305664435c30980c2649defc1a798fc2262e9ca835f8348ecbe2c43ae89034f` |
| Targeted worker | `sha256:985d157eb09413f52fda426d98a567cad7ffe805fdd9aeb2a34447953ed100cf` |

There is **no currently verified serving source**: the engine connection fails
at `npipe:////./pipe/dockerDesktopLinuxEngine` with “The system cannot find the
file specified.” One normal Desktop launch did not restore that pipe. No settings
repair, reset, repeated startup, forced termination or alternative stack was used.
Ports 23124 and 28188 were not listening. Actual browser navigation to
`http://127.0.0.1:23124/builder` returned **ERR_CONNECTION_REFUSED**. This is the
fresh browser acceptance result: **blocked**, not a passed synthetic rehearsal.

Consequently current container identities, stopped workers, queues, journal and
artifact bytes cannot be freshly inspected. The unchanged 14 November record
remains the last live verification: wf-375a888b8976 completed; immutable submission
`eae852db-3af3-42a0-9bf6-e7e12a126744`, SHA
`0b8817eff18d6e1c8eb67706d4f6cdd968c62f7630a682a3a913cb5e672ec95c`;
effective/observed epochs 1 and batch 4; same-workflow model handoff; generation
10 × 100 = 1000 rows; seven completed journal jobs; both additive scopes closed,
three workers stopped and queues empty. This pass does not recast those historical
facts as new observations. See [original recovery](PORTUGUESE_OWNER_RECOVERY_2026-11-14.md).

The private preservation record is still present, SHA
`0897a1e76b2acdf1c9404ecebc695433dc2bbc573458dd722c1b8b200811a570`.
The provider ledger was checked read-only **now**: byte-identical SHA
`cf9fa12e87633b9e260d3983a3dd9e5c51df346c04237b3babd255ee66cd7d2b`,
25/25 calls, zero outstanding. Private configuration still has no supervised-mode
activation, provider key or execution grant. No profile/configuration was rewritten.

## Focused implementation

Portal source/test checkpoint: `4b4d1922ade0d9f1624b39b5465509c7904da969`.
Builder revision integration: `722a3c36c3fcc666d6384ff5c4746dea0c3337a1`.
Maintained WP3 source/test checkpoint: `183b533ed23de7c77fb9e5a4712033e72f1ce6a5`.
Final admission/transport source: Portal
`1354a141a0d76ee90ed6eb5ae1ce1b6d5242608b`, maintained WP3
`822c05cf1cac09c9448f423a1359369b6fc61aac`.

Inspection-only is still the default for this exact database/owner profile.
Three explicit server settings select a future supervised mode, existing
authorization ID and private adapter URL. They do not create authority. Other
profiles keep their current paths. Legacy placeholder submission stays denied.

The existing worker_cli can only process an already allocated workflow ID. It has
no pre-submission consumer readiness signal. A process/container health check
therefore cannot solve admission. The new experimental one-shot standby reuses
the maintained Worker/WorkflowEngine/Redis queue and existing authorization
journal. It waits for **one authorization**, probes Redis, the actual ML OpenAPI,
read-only observer and authenticated adapter capability response, and refreshes
a six-second waiting lease. It checks for unrelated unresolved workflows/queues.
Readiness does not pop tasks, bind a workflow, reserve a job or call an algorithm.
An additive journal table records the one processor identity/lease; it never
resets historical grants or jobs. A dead/consumed processor is not replaced.

Server readiness requires the configured active reviewer, owned current saved
design, exact input/settings/pins/binding, canonical compile/transport checks,
prepared matching journal authority, unchanged test dataset and fresh waiting
processor lease. Submission rechecks scope/lease and the reviewed policy hash.
A reviewer-row lock serializes admission across saved designs; the existing
ExecutionSubmission records a durable dispatching attempt **before** the HTTP
submission. Repeated identical confirmation returns the existing identity, while
conflicts or uncertain attempts cannot dispatch again.
The sandbox's normal submission transport also refuses redirects and environment
proxy fallback; other profiles retain their original transport behavior.

The returned workflow identity is persisted before its exact authority is bound.
The waiting processor can then claim only that workflow once. Loss of processing
or response is retained as an uncertain attempt/queued workflow, never retried or
marked complete. Existing adapter task reservations still precede algorithm
dispatch. The earlier task-fact queued/claimed status correction is retained.
This is not a distributed exactly-once guarantee; reconciliation is required on
any uncertainty. PostgreSQL lock behavior has not been integration-tested here.

Builder now explains which Portuguese entries are chained versus retained
standalone history. Training CSV explains the original uploaded-CSV API and this
sandbox's one synthetic input. Settings distinguish sandbox limits, references,
validated defaults and actual consumption, including batch-size clamping. Results
continue using the existing independent per-task model/output/consumption evidence;
no new success inference or reconstruction from the editable design was added.

For future supervised preparation, an unchanged saved design is no longer saved
again by Prepare: otherwise updated_at would invalidate the exact frozen request.
This change is confined to explicit supervised mode. Inspection and other profiles
retain their existing behavior.

## Checks and integration boundary

- Focused Portal set: **75 passed**; after final integration, **16 admission tests
  passed** separately. Existing evidence/ownership, fresh input persistence,
  missing/unauthorized input, invalid binding/parameters, queued-versus-claimed,
  historical inspection and other-profile regressions are included in that set.
- Focused WP3 experimental set: **64 passed**, including 12 new standby/journal
  checks, concurrent bind/processor claim, lease expiry, failed dependencies,
  default-disabled routes, private auth, policy drift and no readiness consumption.
- Frontend helper checks: **23 passed**. Typecheck passed.
- Initial test import error was fixed; sandbox test-directory access errors were
  resolved by running the same isolated tests with normal host file access.
  These interruptions are retained in private logs, not counted as passing runs.
- All execution boundaries used doubles/disposable databases and disabled external
  networking. No fresh scientific or real execution evidence is claimed. SQLite
  tests do not establish PostgreSQL concurrency.
- Staged secret scans passed before publication. No unrelated full suite was run;
  older unrelated baseline failures remain recorded in their original reports.
- API/web/worker image builds, retained-profile update, current live preservation
  checks and fresh UI Save → refresh → Validate are **not completed**, because the
  retained engine/database are unavailable. No rollback image/build was replaced.

Private records: original checkout `local-backups/portuguese-supervised-20261116`.
Credentials remain only in the existing
`local-backups/portuguese-sandbox-20261112/profile/credentials.json`; use the
`email` and `password` fields locally. No account or password was changed.

## Browser steps after retained review recovery and packaging

These steps are **pending**, not something the current unavailable URL can do now:

1. Open `http://127.0.0.1:23124/builder`, sign in with the existing credential file,
   and start an empty design. Add **chained TrainModel**, then **chained GenerateData**.
2. Connect Input → TrainModel → GenerateData → Output on the canvas. In Data
   connections choose **Use published connection** for model_ref and **Training
   CSV → Sandbox test dataset**.
3. Select each instance and set epochs **2**, batch **4**, generated sequences **10**.
   Save and refresh the new saved URL. Do not use a helper/API write to assemble it.
4. Validate design. Verify settings, dataset, both 0.2.0 pins and published binding
   survived. The default **INSPECTION ONLY** boundary must remain visible.
5. Inspect existing completed results without executing; no Prepare/Confirm or
   new job is authorized in this pass. Record agent and human observations separately.

No new review-design URL exists yet. The previous genuine manual UI acceptance
is preserved at solution e0814ad1-3d96-453b-96e7-ae0124bb43b4; it is not substituted
for this pass. Independent usability and hosted/node readiness remain unverified.

## Concrete next supervised acceptance proposal — NOT AUTHORIZED / NOT ACTIVATED

After engine recovery, package the reviewed source offline, preserve rollback
pins/consistent database backup, update only necessary retained review components,
and complete the fresh UI acceptance above with execution disabled. See the
[supervised runbook](../deploy/portuguese_sandbox/SUPERVISED_RUNBOOK.md).
Freeze that exact owned saved design/request revision before seeking execution
approval. No authority should be created while these prerequisites are incomplete.

Proposed scope: **one new workflow, at most one TrainModel and one GenerateData**;
no retries, replacement scope or general worker. Train epochs **2**, batch size
**4**; GenerateData **10** sequences; fixed existing sequence length **100**.
Pins: `pt-chain-train-v2` / `pt-chain-generate-v2`, both **0.2.0**, published
model_ref → model_ref binding. Input `pt-approved-synthetic-data`, SHA
`36c7721e9254d1abd24cf6999bb693fc6d3ccf28e377431c0562a32d6efe17a8`.
Retain CPU 2 / RAM 3 GiB. The 400-row CSV yields four training sequences, so
expected observed batch size is 4; record requested/effective/observed separately.

Expected proof: new workflow/task identities; one newly trained model with saved
epochs 2/batch 4; signed producer and consumer association to that model's actual
hash; exactly ten sequence markers, each 100 observations, 1000 CSV rows; authorized
downloads matching recorded hashes. Hashes for new outputs cannot be predicted.

Only after separate explicit authorization: use the existing create operator for
one new attributable frozen policy; start one named standby for that scope; enable
only this retained sandbox's supervised flags; obtain read-only readiness; make
one visible confirmation. Any drift, lost lease, unknown response, failure or
missing proof stops acceptance without retry. After terminal reconciliation, stop
the one-shot processor, close that scope, disable both supervised flags, check
all queues and old evidence, and verify the exhausted 25/25 ledger unchanged.
Do not run this proposal or ask for execution approval until the blocked design
and packaging prerequisites are complete. No partner-native/node-ready claim.
