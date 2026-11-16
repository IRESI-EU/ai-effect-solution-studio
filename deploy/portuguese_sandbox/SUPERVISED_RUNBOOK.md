## Latest actual session — PASS and CLOSED, no further execution

The exact operational proposal at Portal c58fff86fc8085d3edacaf157c4e6a9d54d525e1
was separately approved and consumed once. Scope pt-supervised-operational-20261116-01
is CLOSED; its named processor exited0 and stays stopped. Workflow wf-717110fb8d5e
completed one TrainModel2/4 and one GenerateData10x100 with exact new-model handoff,
saved-model/artifact hashes and protected output downloads verified. All five
workers stopped, all four scopes closed, flags OFF/config restored, queues empty
of unresolved work, historical evidence/designs and 25/25 ledger unchanged.

[Actual evidence/closure](operational-acceptance-20261116-verification.json).
The proposal is a preserved frozen approval input, not reusable authority.
Do not run activate, reopen this scope or restart its consumed processor.
The procedure below describes mechanisms for a future separately approved session,
not permission for another run. No provider/node/production authority.

---

# Current operator procedure — corrected activation, execution disabled

Use `supervised_session.py` for future sessions on this retained profile. It
does not create authority. The older procedures below are historical evidence;
their closed scopes and consumed processors must never be reused.

1. With API admission disabled, run `check --profile <retained-profile>
   --proposal <reviewed-proposal.json> --records <new-private-directory>` using
   the original checkout's Python environment. This validates saved revision,
   request/settings/contracts/dataset, actual images/resources, closed historical
   scopes, stopped old workers and the unchanged provider ledger. Its real
   dependency check has no journal mount, workflow creation or job reservation.
2. Only after approval of the completed proposal, use the existing
   `experimental.portuguese_parameters.authorization create --file <policy>
   --actor <attributable-actor>` operator against the retained journal. Never
   create authority as part of a probe. Freeze the policy's task inputs and
   resources from that proposal; do not edit the saved design.
3. Run `supervised_session.py activate --profile <retained-profile>
   --proposal <reviewed-proposal.json> --authority-file <exact-policy.json>
   --worker-name <unique-approved-name> --records <new-private-directory>`.
   The helper checks the separately created, unused authority; configures and
   stabilizes the adapter with API admission OFF; starts one named standby;
   waits for a fresh lease; then enables/recreates ONLY the API. It checks the
   adapter identity and fresh lease again. No replacement standby is permitted.
4. Obtain readiness and confirm once through the normal Builder. The standby
   retries only transient read-only DNS/connection/startup probes within the
   first 30 seconds. Probe budget is 3 seconds, HTTP/Redis operation timeouts
   at most 1 second, healthy polling 1 second and lease 6 seconds. A failed probe
   revokes the lease. Authentication/capability/policy failures are permanent.
   Standby lifetime is at most 300 seconds. Binding/claim/algorithm processing
   are single-attempt; uncertainty requires reconciliation, never redispatch.
5. Reconcile terminal submission/task/journal/model/output evidence; stop only
   the named processor, close the scope with the supported attributable
   operator, then run `restore-review --profile <retained-profile> --records
   <activation-record-directory>`. This refuses a running worker/unclosed scope
   or unrelated configuration drift, restores the backed-up configuration and
   recreates only API/adapter. Preserve databases, journal and all evidence.
   Recheck flags OFF, old workers stopped, queues and 25/25 provider ledger.

No live scope, standby or algorithm is authorized by this document. The current
candidate and non-executing verification are recorded in
[the current-status report](../../docs/PORTUGUESE_SUPERVISED_PREPARATION_2026-11-16.md).
The single synthetic CSV and bounds are sandbox choices; the original service
accepts uploaded CSV data. Design with AI remains disconnected: its native-only
new-pair composer excludes this sidecar and external-input routing.

---

# Historical preparation and failed attempt

This is preparation for the existing ai-effect-pt-parameters profile only.
No command below authorizes a new algorithm. The 2026-11-16 report records the
engine outage and **blocked** retained update/browser acceptance. Historical
closed scopes stay closed. Never rerun bootstrap, prior authorize/submit helpers,
or start the general daemon.

## Recovery / packaging prerequisites (no execution)

1. Restore Docker's existing Linux engine in a separate bounded recovery task.
   Current blocker: missing `dockerDesktopLinuxEngine` pipe after one normal
   startup. No settings repair or further restart belongs to this milestone.
2. Follow CHAIN_RUNBOOK.md to inspect retained identities/volumes, then start only
   postgres/redis and required review services. Keep all three workers stopped.
   Revalidate wf-375a888b8976, immutable snapshot, seven jobs/artifact hashes,
   scopes/queues and original designs against the private 14 November record.
3. Obtain a consistent pg_dump using the established private backup procedure.
   Preserve current compose and API/web/adapter/worker images as rollback pins.
   No PostgreSQL migration is needed. Never restore an older journal/database
   over new evidence.
4. Use the retained offline packagers, with new private records directories:

   ```powershell
   # Portal review worktree, existing original-checkout Python environment:
   & ../../.venv/Scripts/python.exe deploy/restricted-beta/build_candidate.py --roles api web --records ../portuguese-supervised-20261116/build
   # Maintained WP3 review worktree; substitute its verified source SHA:
   & ../../.venv/Scripts/python.exe experimental/portuguese_parameters/build_images.py --role adapter --revision <verified-WP3-source> --records ../portuguese-supervised-20261116/build
   & ../../.venv/Scripts/python.exe experimental/portuguese_parameters/build_images.py --role wp3 --revision <verified-WP3-source> --records ../portuguese-supervised-20261116/build
   ```

   These use retained inputs, no downloads/pulls, linux/amd64 and new tags.
   The WP3 image packages the experimental standby beside the maintained CLI;
   its runtime imports/dependencies must be smoke-checked without starting work.
   An unavailable build input is a blocker, not permission to install/upgrade it.
5. With flags still absent/false, propose/review exact new private compose pins,
   then replace only needed API/web/adapter components using the existing
   no-deps/no-build/pull-never procedure. Leave orchestrator, ML and all workers
   unchanged. Keep the newly built worker image stopped for later approval.
6. Complete fresh manual Builder/browser acceptance with no submission. Record
   its actual saved ID, revision, parameters, pins, binding and input through
   normal authorized GET/compile routes; no helper/API prepopulation.

## Later explicit execution authorization only

The existing operator's `create` / `close` commands remain authoritative. Freeze
the exact normal Builder request (SHA256 of json.dumps(request, sort_keys=True))
and compiled task configurations/inputs with its existing
`pt-chain-authorization-v1` policy. Do not reuse the closed November 13/14 scopes.
The new private policy must include exact reviewed image/resource identities,
one TrainModel and one GenerateData and the existing dataset hash. Freeze the
actual new UI-built solution revision before requesting approval.

Only after approval, stage a private compose update for these exact changes:

- API: PORTUGUESE_SUPERVISED_MODE=true,
  PORTUGUESE_SUPERVISED_AUTHORIZATION_ID=<new approved ID>,
  PORTUGUESE_SUPERVISED_ADAPTER_URL=http://pt-adapter:8080.
- Adapter: PT_SANDBOX_SUPERVISED=1. Keep its policy, token, state and all other
  existing settings/mounts unchanged. Restart only with no in-flight job.
- Existing chain-worker role: new verified WP3 image; same retained Redis
  URL/private network; add the adapter's exact existing PT_SANDBOX_* environment
  values, read-only policy/token binds and the **same existing adapter volume**
  at /state. Never invent/copy a replacement journal. Set
  PT_SANDBOX_SUPERVISED=1 for this explicitly named one-shot process only.
- Keep the chain-worker role's default refusal command. An explicit one-time
  override runs `python -m experimental.portuguese_parameters.supervised_worker
  <new approved authorization ID>` in one unique named container. Do not use
  `up` to start a worker or permit a restart policy. Bound its wait to 300 seconds.

Create the policy using the existing supported operator after the private
configuration is reviewed. The standby registers a one-shot identity in the
same journal, checks actual dependencies and unrelated queued/nonterminal work,
and renews a six-second readiness lease. Only read-only readiness may then show
ready. Prepare preserves the saved revision for an unchanged supervised design.
Explicit browser confirmation rechecks everything before accepting one workflow.
Do not manually bind the returned ID: the authenticated admission path binds
the exact frozen request/policy only after recording the returned identity.

## Stop / reconciliation / closure

- A denied readiness creates no attempt. Inspect the reason; never fake a lease.
- A consumed or expired processor cannot be automatically replaced. Preserve the
  journal; no new scope or retry without a new decision.
- Once submission is dispatching, an unknown response is consumed. Inspect the
  existing ExecutionSubmission, Redis workflow/task/queue facts and journal.
  Do not confirm again to produce another workflow. A repeated identical accepted
  confirmation only returns its existing ID.
- Accepted plus pending tasks means queued, not active algorithms. A claimed task
  is distinct from verified consumption/completion. The adapter still reserves
  each task before its one upstream call; do not use missing artifacts as proof
  that nothing started.
- After terminal reconciliation, stop only the named standby if necessary,
  inspect no in-flight adapter dispatch, then use supported `close` with an
  attributable actor. Set API mode=false and adapter PT_SANDBOX_SUPERVISED=0;
  retain scope/attempt/events/container logs and every model/capture/output.
- Recheck all workflow queues without flushing; preserve unrelated entries and
  stop if any unresolved work exists. Verify previous designs/evidence/ledger
  unchanged, then inspect historical results with workers stopped.

Rollback: stop only changed review components; restore their previous compose
pins/configuration and restart safe review services with the same volumes.
Never downgrade/overwrite the journal or database. No original Portuguese source,
image, API semantics, provider authority or spending limit changes are involved.


## Later 16 November checkpoint: review restored, execution disabled

Docker responds after the owner's Windows Start launch; original settings rename
root cause remains undetermined. No further Desktop repair/restart. Portal
source 75ccb8fd09be477d5517bea26c139011f9436ad6; adapter/worker package source
17f32be413fe64532373f70d8b862002c3427a8c. Only API/web/adapter updated offline; original ML,
PG/Redis/orchestrator/observer/volumes retained, all workers stopped.
Fresh UI Save -> refresh -> Validate passed:
http://127.0.0.1:23124/builder?solutionId=b4e48556-c3a5-4a73-903d-c2a2618756fd
See [completed report](../../docs/PORTUGUESE_SUPERVISED_PREPARATION_2026-11-16.md)
and recovery-browser-verification-20261116.json. Exact normal browser request:
proposed-supervised-acceptance-20261116.json; SHA 96f346d9e87f5c68bc45b5e35d7c62ad671591a012711d53ef383c50addca00b.
This is a proposal, not a live journal policy. No create/bind/worker/execution
step is authorized yet. Keep both supervision flags disabled.
Rollback: stop only api/web/pt-adapter, restore their three previous image pins
from private local-backups/pt-accept-20261116/compose-before.private.json and use
`up -d --no-deps --no-build --pull never api web pt-adapter`. Preserve current
DB/journal/evidence/designs. Never restore an older DB, bootstrap or start workers.


## Terminal failed supervised attempt, 16 November

Scope `pt-supervised-browser-20261116-01` was explicitly authorized, created and
is now **closed/unbound**, with zero workflow submissions and zero algorithm calls.
One named standby exited 1 during its first read-only adapter capability probe:
adapter recreation while enabling supervision removed the DNS target. Builder
readiness was denied, Confirm was not clicked, no retry/replacement occurred.
All flags/configuration restored to before; workers stopped; seven old jobs,
eight designs, queues and 25/25 ledger preserved. Keep its container and logs.
See supervised-acceptance-20261116-verification.json and the appended report.

**Do not rerun the preceding execution instructions for this scope.** A later
attempt needs separate explicit authorization after a reviewed startup-order fix.
Proposed safe sequencing for review: create exact authority; enable/stabilize only
the adapter while API stays inspection-only; launch the one named standby; verify
its fresh lease; enable only API (do not recreate adapter again); normal Builder
readiness and one confirmation. Do not add automatic processor replacement,
algorithm retries or bypass the lease. This correction has not been exercised.
