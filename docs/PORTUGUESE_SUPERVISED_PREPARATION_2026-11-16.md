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


## 16 November recovery / packaging checkpoint (non-executing)

Starting reviews: Portal 54dd3f09e75d2c8e21bb79f4ead9c1c8066e811c,
maintained WP3 17f32be413fe64532373f70d8b862002c3427a8c.
The owner reported Engine running after a normal Windows Start launch and a
successful disposable AppData create/write/rename test in normal PowerShell
outside Codex. Docker CLI subsequently responds inside Codex (server 29.9.2).
These observations do not establish the original rename failure's root cause.
No further Desktop repair, settings/ACL change or restart was performed.

No retained containers started automatically. Only this profile's retained
PostgreSQL, Redis, ML, orchestrator, adapter, observer, API and web were started.
All three workers remain stopped; supervision is disabled and provider is
 disconnected. Before packaging, authenticated read-only checks confirmed the
owner workflow Completed, unchanged immutable submission, seven completed
journal jobs and rehashed outputs, old designs/models, closed scopes, empty
queues and unchanged ledger SHA/count 25/25 with zero outstanding reservations.
A new consistent pg_dump and exact private compose/container rollback snapshot
are retained under original-checkout local-backups/pt-accept-20261116.

The original packager stopped on missing dependency image
8a998103f1ea42cb1a8fd461e8e3fbf32c992d98b60c3147917f9cac95a758e1.
Its older staging web dependency image is also absent. Instead of downloading
or changing dependencies, the packager now pins the retained current verified
API/web 002686f04fb5 images by exact IDs. All 48 installed Python requirements
match requirements.lock (CPython 3.12.14); web pnpm-lock.yaml and package.json
hashes match exactly (Node 24.15.0). Existing lock comparisons, pip check,
no-network build, source-only context and tag-drift checks remain mandatory.
No historical image is relabelled or overwritten. This is a build-input repair,
not a runtime dependency upgrade. Actual build/test/browser results are appended
separately after they finish; this checkpoint alone is not acceptance.


## Later 16 November checkpoint: recovery, packaging and fresh UI acceptance passed

This supersedes only the earlier availability/preparation status. Original failed
observations above remain historical; their root cause is not established.
No further Docker repair, settings/ACL change or restart occurred.

Portal serving source **75ccb8fd09be477d5517bea26c139011f9436ad6**, maintained adapter/worker
packaged source **17f32be413fe64532373f70d8b862002c3427a8c**. Exact images, build contexts,
retained dependency inputs and checks: [sanitized verification](../deploy/portuguese_sandbox/recovery-browser-verification-20261116.json).
Only API/web/adapter were replaced. All **53** retained container names remain;
other identities/images/mounts are unchanged, including original ML. Desktop
normalized the adapter read-only Windows bind source to its Linux host path;
credentials/policy/token hashes match the exact host files. Journal volume
unchanged, all three workers stopped, supervision/provider disabled. Other
profiles remain stopped. No live scope was created.

Four actual PostgreSQL concurrency cases **passed** (1.70s, 50 existing
deprecation warnings): real reviewer-row blocking for concurrent confirmations
of same/different designs and uncertain dispatch. HTTP/dispatch were doubles;
only suite-created random test databases were used and removed, no algorithms.
Frontend helpers **23 passed**; packaged frontend checks **18 passed**; Next
production compilation, TypeScript and build passed. API all 48 exact Python pins
and pip check passed. Adapter/standby imports passed with networking disabled;
worker main was never invoked. The API no-network/default-PG import initially
failed because postgres could not resolve; a separate disposable SQLite startup/
import passed, then the retained actual PostgreSQL application started normally.
No unrelated full test inventory or dependency download/upgrade was performed.

### Fresh manual browser acceptance (agent, not independent usability)

[New saved design](http://127.0.0.1:23124/builder?solutionId=b4e48556-c3a5-4a73-903d-c2a2618756fd) began from empty `/builder`, not a
copied/prepared design. Palette added chained TrainModel and chained GenerateData;
Training CSV selected **Sandbox test dataset**; canvas edges were drawn and
**Use published connection** selected. Epochs 2, batch 4 and generation count 10
were reviewed. Save created the new owned URL; refresh retained dataset,
settings, both instance identities, 0.2.0 pins and model_ref binding.
**Validate design: Checked successfully.** No preparation/API design write.

Raw saved overrides contain epochs 2 only; batch 4 and count 10 are omitted
pinned defaults. Refreshed controls and normal compilation both resolve 2/4/10.
These are validated settings, not new algorithm-consumption evidence. Browser
shows INSPECTION ONLY, runtime unchecked and execution unavailable; preflight of
the exact normal browser request returns **409 / inspection_only**. No live
submission was used to test denial.

![Fresh saved, refreshed and validated design](evidence/portuguese-20261116-builder.png)
![Saved binding and exact contract pins](evidence/portuguese-20261116-connection.png)

[Historical owner results](http://127.0.0.1:23124/deployments/wf-375a888b8976#results) still show
Completed, recorded consumed 1/4 training, same-producer model SHA, and 10 x 100 =
1000 output rows with workers stopped. Immutable snapshot equals the prior
record. Seven journal jobs/output hashes, earlier models/designs, closed scopes,
terminal workflow records and empty queues all rechecked. Ledger byte-identical,
**25/25**, zero outstanding. New training/generation/provider requests: **0**.

![Historical evidence with workers stopped](evidence/portuguese-20261116-historical.png)

### Backup and rollback

Original-checkout `local-backups/pt-accept-20261116/database-before.dump` is a new
consistent pg_dump; pg_restore TOC verified, SHA
`03237dde2c6bdc2d8c1b9769fbbc8a655fab7db309fd9004863a9d6117d7c0ec`.
Private compose-before/container-before records and old API/web/adapter images
are retained. No migration. Rollback stops only those three roles, restores only
their old image pins from compose-before and uses the existing no-deps/no-build/
pull-never up command. Do not restore the older database over new designs or
evidence, start workers, rerun bootstrap or modify another profile.

### Exact later execution proposal: NOT AUTHORIZED

[Frozen normal browser request, contracts, resources and closure checks](../deploy/portuguese_sandbox/proposed-supervised-acceptance-20261116.json).
Saved revision **`2026-11-16T11:26:14.691950`**.
Request SHA256 **`96f346d9e87f5c68bc45b5e35d7c62ad671591a012711d53ef383c50addca00b`** using json.dumps(request, sort_keys=True),
verified through the serving schema. It includes every normal Builder node
field; the earlier provisional minimal operator-helper hash is not authority.
No live policy/scope was created. Both supervision flags remain disabled.

Proposed limit: one workflow, one TrainModel (2 epochs/batch 4), one GenerateData
(10 sequences), existing 400-row dataset/hash, sequence length 100; ML CPU 2/RAM
3 GiB; named targeted standby CPU 1/RAM 384 MiB, no restart, wait <=300 seconds,
six-second lease; zero retries/replacement. Exact candidate/serving images and
all component limits are frozen. The current adapter image and retained
historical registry image are separately identified; no registration/contract
was changed and no new execution qualification is claimed.

Only after separate explicit approval: recheck revision/request/contracts/data/
images/resources and empty queues, create one new attributable scope through the
supported operator, enable only this profile's flags, start one named standby,
require normal readiness and confirm once through Builder. Stop on drift, lost
lease, failure, uncertainty or missing proof. Reconcile without retry. Verify new
model settings/hash, signed same-model handoff, ten sequences/1000 rows and
hashed authorized downloads. Then stop worker, close scope, disable both flags,
inspect queues and old evidence/ledger. No production/partner-native claim.

Operator check: open new URL; inspect CSV and step settings; inspect connection
Technical details; refresh and Validate; confirm INSPECTION ONLY. Existing
sign-in: original-checkout
`local-backups/portuguese-sandbox-20261112/profile/credentials.json`, identifier
`pt-sandbox-designer@example.test`. Never reproduce the password. Independent
human usability, scientific suitability and production compatibility remain
unverified. C: headroom after packaging: 63.78 GiB.
