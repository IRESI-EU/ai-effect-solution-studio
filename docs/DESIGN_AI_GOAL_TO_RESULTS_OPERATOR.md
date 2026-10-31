# Local operator procedure — separate approval required

This is a **prepared procedure, not permission to run it**. The [owner runbook and acceptance criteria](DESIGN_AI_GOAL_TO_RESULTS.md) are fixed before seeing any model response. Current permission authorizes development/offline verification only. No new checkpoint, execution grant or amendment has been activated.

Use the existing qualification project and the integration review checkout. Never run `compose down`, recreate volumes/accounts, pull images, migrate the shared ledger, flush Redis or start unrelated profiles. No production command is involved. Keep passwords, provider keys and full environment values out of terminal output and screenshots.

## Preflight after attributable approval

1. Record the owner's approval reference and operator identity. It must explicitly authorize **12 → 13 only**, one provider attempt/US$0.005 and exactly one new local seed-43 workflow. Earlier execution permissions remain consumed.
2. Recheck source, build, catalogue/contract fingerprints and runtime image IDs against the machine evidence and existing `aie37-profile-20261028/runtime.json`. Verify the preserved source remains seed 42 with one named generator-to-benchmark binding. Confirm no active unrelated draft and no new attempt has been created. Read actual formatted provider context without sending it; the pre-request conservative token bound must be ≤32,000, output ≤2,000, configured context ≤16,000 characters.
3. Read the **existing** ledger read-only. Require 12 settled rows, 12/12, open policy, US$0.10 ceiling, US$0.003784750 held/accounted, US$0.096215250 remaining, no unsettled/unknown usage or outstanding reservation, and the unchanged prior 10-to-12 audit. Stop on any mismatch. Preserve the ledger and every previous checkpoint before/after; no reset or replacement.
4. Exclusively create `goal-to-results-provider-task-20261031.json` in the **existing** `local-backups/dutch-seed-runtime/acceptance` directory only after approval. It must contain exactly:

   ```json
   {
     "ledger": "luna-dutch-manual-20261018-04.sqlite3",
     "baseline_count": 12,
     "baseline_sha256": "c02e95bbbd2d2178d5117af9c16cd4095a66b063a41489079718a5f9caca8a5a",
     "max_calls": 1,
     "max_reserved_nano": 5000000
   }
   ```

   Recompute `baseline_sha256` from the current original 12 ordered request rows, with the existing Budget projection (`id, held, reserved, input_bound, usage, status, response_id`) and `sha256(json.dumps(rows, sort_keys=True).encode())`. It must equal the value above. Use exclusive creation; never overwrite a checkpoint. A mismatch requires stopping, not changing the expected outcome.

## Supported amendment — preview, then one apply

Run from this review checkout with the original Python environment. Resolve these local variables privately; do not export the whole environment:

```powershell
$demoOriginal = '<absolute original production-ui checkout>'
$demoPython = Join-Path $demoOriginal '.venv/Scripts/python.exe'
$demoAllowance = Join-Path $demoOriginal 'local-backups/dutch-seed-runtime/acceptance'
$demoOperator = '<attributable operator>'
$demoApproval = '<exact owner approval reference for this 12-to-13 amendment>'
$demoArgs = @(
  'deploy/dutch-seed/amend_demo_allowance.py',
  '--ledger', (Join-Path $demoAllowance 'luna-dutch-manual-20261018-04.sqlite3'),
  '--expected-ledger-sha256', 'c506929d99ae8b63de7e7d941d06aaac48ef27a4bea8eedc1a12fe407959b165',
  '--expected-limit', '12', '--new-limit', '13',
  '--amendment-id', 'goal-to-results-20261031-12-to-13',
  '--operator', $demoOperator,
  '--reason', 'One approved goal-to-results provider request only; no monetary increase',
  '--authorization-ref', $demoApproval,
  '--task-checkpoint', (Join-Path $demoAllowance 'goal-to-results-provider-task-20261031.json'),
  '--runtime-container', 'ai-effect-aie37-api-1'
)
& $demoPython @demoArgs
# Review the exact before/after audit before the separately authorized apply:
& $demoPython @demoArgs --apply
```

These commands have **not been run on the shared ledger**. The first is a read-only preview. The second atomically commits only count 12-to-13 plus attributable audit, preserving monetary policy and all 12 usage rows. It refuses other limits, closed/unknown usage, different ledger/hash, invalid/exhausted task checkpoints, conflicting/repeated amendments and wrong container/mount identity. Exact host-directory identities must match inspected Docker binds; the Linux aliases and image/container identities are recorded in the audit. No basename-only path exception or disabled validation is used. Record both returned policies/audits privately.

## One-execution grant and safe runtime readiness

Only after the execution approval, exclusively create
`<original-checkout>/local-backups/demo-acceptance-20261031/authorization/one-execution.json` with exactly these fields:

```json
{
  "id": "goal-to-results-20261031-one-execution",
  "profile": "qualified-dutch-goal-to-results",
  "owner_id": "aie37-designer",
  "seed": 43,
  "source_solution_id": "98eadd46-5b58-4517-b706-f2a7b9ed6bc4",
  "max_attempts": 1,
  "approved_by": "<owner/operator identity and approval reference>",
  "approved_at": "<actual ISO timestamp of approval>"
}
```

The grant is read and snapshotted by the server, never generated by the assistant. Its single dispatch claim is serialized across copies using the existing source solution lock. Do not issue a new grant to retry a failure or uncertain submission.

The old Redis data may contain pending work. **Do not start the worker first.** After authorization, start only existing `ai-effect-aie37-redis-1`; inspect every `queue:*` length and each top-level `workflow:*` record using read-only `SCAN`, `LLEN` and `GET`. The maintained `worker_daemon.py` scans all running workflows, and `task_queue.py` uses `queue:<workflow_id>`. If any nonempty queue, running/nonterminal old workflow or unresolved old task is present, **stop with the worker still stopped**. Preserve the data; do not clear, replay, repair or resume old work under the new permission.

Only after clean queue/state checks, start the **existing containers**, without pulling/rebuilding the algorithm/runtime images: `ai-effect-aie37-seed-orchestrator-1`, `ai-effect-aie37-seed-synth-1`, `ai-effect-aie37-seed-benchmark-1`, then `ai-effect-aie37-worker-1`. Verify their pinned image identities and advertised whole-output/parameter compatibility before any submission. No algorithms are to be invoked as health tests.

## Connect the genuine provider boundary

Use the existing private provider credential from `local-backups/design-ai-acceptance/acceptance.env`, reading **only** its `OPENAI_API_KEY` into the operator process without printing it. Do not import that file's old database, ports, budgets or other settings. A nonempty private key was found; it has not been sent or validated in this milestone. Credential validity is a live precondition, not an offline claim.

Resolve `AIE37_PROFILE_DIR`, `DEMO_ALLOWANCE_DIR`, `DEMO_AUTHORIZATION_DIR` to the exact existing directories described above. Only after the approved amendment/grant, combine the maintained base and overrides in this order:

```powershell
docker compose -p ai-effect-aie37 `
  -f deploy/aie37/compose.yaml `
  -f deploy/aie37/demo.compose.yaml `
  -f deploy/aie37/acceptance.compose.yaml `
  up -d --no-deps --no-build --pull never api
```

The prepared final override enables only the genuine server key, new one-call checkpoint, existing shared writable ledger and read-only one-execution grant. It does not install fixtures. Do not print `compose config`, Docker environment contents or credentials. Native web remains on port 23121 and routes to API 28185.

Before the sole request, check normal `/api/design-ai/config` and the approved catalogue projection: provider mode **real**, configured, **gpt-6-luna**, low reasoning, Standard `service_tier=default`, max output 2,000, `store=false`, SDK retries 0, no fallback, unchanged approved context, shared **12/13**, task **0/1**, US$0.005 reservation capacity and no outstanding holds. Any unavailable or mismatching gate stops before spending. The offline 23122 guard/profile must still match its preserved fingerprint.

## Observe once, preserve the outcome, lock down

Perform the [six owner-runbook steps](DESIGN_AI_GOAL_TO_RESULTS.md#short-demo-runbook--after-separate-authorization-only) using the exact one prompt. The structured seed/review/Apply/Undo/Save controls require no additional provider call. Do not use arbitrary chat, Retry or a second prompt. A clarification/refusal is an observed failure for this acceptance, not permission for another call.

Capture the actual safe visible response, recommendation fields and validation, draft/revision/saved-solution ID, immutable submission SHA, new workflow/service task IDs, task states, seed requested/effective/consumed, verified same-grid association, actual summary/benchmark values and four download hashes. Missing output, task failure or scientific limitations remain visible. Stop at any uncertain dispatch and reconcile the existing attempt read-only; never resubmit to obtain a cleaner result. No historical run may stand in for this new acceptance.

Settle the one reservation normally from actual response usage; retain unknown-usage holds until attributable reconciliation. Report input/output/cached/reasoning usage, conservative accounted charge versus any usage-price estimate, remaining allowance and outstanding reservations/unknown charges. Confirm **13/13**, task **1/1**, `can_request=false` using read-only availability; do not send another paid probe. Preserve the new immutable checkpoint and attributable audit alongside all old exhausted states.

When capture finishes or acceptance stops, remove the provider key from the operator environment and recreate **only API** with base `compose.yaml` + `demo.compose.yaml` (omit the live acceptance override). This blanks provider/grant settings and restores a read-only ledger; it does not delete grant/checkpoint/evidence files. Do not rerun `stage_demo.py` after a grant exists: it intentionally refuses that state. Stop the existing worker when no approved run is active; do not interrupt an uncertain active run without reconciliation. Leave the owner's web entry point and preserved results accessible. Record exactly which components remain running.

No follow-up provider call, additional grant, allowance increase, production operation, merge or tracker update is part of this procedure. Independent human acceptance and production qualification are separate work.
