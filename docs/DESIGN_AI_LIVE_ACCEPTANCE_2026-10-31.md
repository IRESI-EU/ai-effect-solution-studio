# Bounded live Design with AI acceptance — 31 October 2026

**The provider, controls, new execution and captured-artifact checks passed. A UI evidence-display inconsistency remains, so the complete coherent demonstration is not marked accepted/Done.**

Exact authorized/tested application source: PR #13 head `97abc34c8bfd8168dd7738ef5f090d6516c5a031`. No application source, commit, push, merge, production setting or tracker changed during this acceptance. The original criteria were retained; no model response, workflow or capture was retried or manually repaired.

**[This new run's results](http://localhost:23121/deployments/wf-1b6eb7caaf57#results)** remains accessible after cleanup.

| Acceptance check | Outcome |
|---|---|
| Authorized head, pins, context and clean Redis preflight | **PASS** |
| One genuine provider recommendation, seed 43, registered workflow | **PASS** |
| Explicit Create / Apply / Undo / Apply / Save | **PASS** |
| New workflow, both tasks completed, consumed seed 43 | **PASS** |
| Same-grid association and four protected downloads | **PASS** |
| Provider/grant disconnected; 13/13 and task 1/1 block further calls | **PASS** |
| Consistent consumption evidence across all UI panels | **FAIL** |

The generic **Recorded instance settings** section says “Algorithm consumed: Unverified — no validated algorithm evidence available” and “Data input: Unverified — associated input evidence is unavailable.” The qualified **Experiment results** section and validated files independently record algorithm-consumed seed 43 and the exact same-grid benchmark association. Preserve this visible disagreement as a failure/follow-up; it was not patched or waived during acceptance. The underlying qualified capture is available and passes integrity/association checks; there was no failed task or missing/mismatched qualified capture.

## Actual provider response and controls

The exact prompt was sent once through the normal signed-in Design with AI application:

> Create a sample electricity grid using seed 43 and benchmark it.

Genuine `OpenAIProvider`, gpt-6-luna, low reasoning, requested Standard (`service_tier=default`), output ceiling 2,000, `store=false`, zero retries, no fallback or fixture override. The pre-request shared allowance was 12/13, new task 0/1, with no holds. Context was 6,636 characters / conservative input bound 20,653 of 32,000; source revision `8ee273139c84fb104d06fb2b4edc7189286b51e1ae29f501500e7bfbf5ca1e1d`. Pinned runtime/registry compatibility and clean Redis work were confirmed before spending.

Actual visible response:

> I recommend the existing registered Dutch workflow—not arbitrary composition. It creates a sample grid using seed 43, then benchmarks that exact grid. After successful explicit execution and capture, the result view can show the recorded seed, task states, grid summary, and recorded benchmark values. Optional downloads are Configuration JSON, Grid JSON, Pandapower graph JSON, and Benchmark JSON. This workflow uses a synthetic grid and a no-op benchmark agent; KPI units and scientific validity are not established, and production compatibility is unverified. This recommendation does not create a draft or run anything. To make a copy, use the separate “Create this experiment” action.

This is a successful recommendation of an existing registered workflow, not proof of arbitrary graph synthesis or structural composition.

Explicit Create made draft `7e8361c8-0870-47cf-a670-b6ec03a09324`, owned by `aie37-designer`, at revision 0 with only pending seed 42→43. Apply produced revision 1/seed 43. Undo produced revision 2 and restored the **complete** original design hash `6c84aedef6672870ea7e37fa57cebaa99086c24f9dc5a80d4ca44eb8c06ab879`. The supported seed control proposed 43 again without a second AI call. Apply produced revision 3; explicit Save created owned solution `ef10cde8-15d4-4f6d-82dd-0525a16de4fd`. No workflow ran from Create/Apply/Undo/Save.

## Exact new execution and protected captures

Readiness on that exact saved copy returned **Ready**. Start execution opened the separate confirmation; **Confirm and start execution** was selected once.

- Durable submission: `a78745cf-db77-4fa9-abd4-5b201d816083`.
- Immutable submitted SHA-256: `3a8d8713362b9fcf9f62360ec78f7b380871fad7d599d2913c6756df0c5997b9`.
- New workflow: `wf-1b6eb7caaf57`, completed; no historical workflow was substituted.
- Grid-generation and benchmark tasks both **completed**. Requested/effective seed is 43; configuration capture explicitly records `algorithm_consumed={"seed":43}`.
- Grid: **169 nodes, 206 edges**, seed 43. Runtime output/input references, workflow/task IDs, capture-manifest digest and grid digest establish that the benchmark consumed this execution's grid.
- Benchmark: one scenario, one episode, **11 steps**, 0 recorded overload violations; runtime_seconds `0.3183396150016051`, terminated true; backend `grid2evaluate`. Metric units/scientific validity were not established.
- Browser navigation reached this exact new run automatically. Server-owned history and one consumed grant remain durable. No live duplicate dispatch/uncertainty experiment or later draft edit was attempted; those failure/immutability paths retain their earlier offline tests.

Each file was downloaded through the normal authenticated application route using the existing designer, compared with the captured SHA-256/size, and denied with HTTP 401 when unsigned. Attachment, private/no-store, nosniff and sandbox headers were checked.

| Artifact | Bytes | SHA-256 | Authenticated / unsigned HTTP |
|---|---:|---|---|
| configuration | 1441 | `24f9e01c17119611c6c8315e5415d95cf1843cbb3993b70c1187f3cd0bc8e301` | 200 / 401 |
| grid | 148660 | `c7f41cf987de793ac92cad894393188df4918ff8028b8cd05a674188d0199d16` | 200 / 401 |
| network | 129851 | `a521315934294f2850d03b713e4cc29f0f0710f84b02ee95625f5dbc6f0f0462` | 200 / 401 |
| benchmark | 855 | `4e88e9b2bf9e71c94548498b31d635b889a3b5b6b39bd39ed5a35422ee79b1f0` | 200 / 401 |

## Amendment and exact accounting

The supported operator preview then one apply changed only **12→13** on the original ledger. Attributable amendment ID: `goal-to-results-20261031-12-to-13`; authorization was the owner's direct approval of the exact PR head in this chat. Prior 12 records, original 10→12 audit, old checkpoints and US$0.10 ceiling were preserved. The new immutable checkpoint is one call / US$0.005; the separate grant permits one seed-43 execution and has exactly one consumed claim.

| Item | Actual |
|---|---:|
| Provider attempts | **1** |
| Input / output / total tokens | **2,745 / 159 / 2,904** |
| Input cache writes / cached reads / reasoning tokens | **2,742 / 0 / 0** |
| Lifetime reservation | **US$0.005** |
| Conservative amount accounted by the guard | **US$0.000422625** |
| Usage-price estimate from reported cache-write details | **US$0.000422550** |
| Shared accounted total | **US$0.004207375** |
| Shared remaining | **US$0.095792625** |
| Outstanding reservations / unknown usage holds | **0 / US$0** |
| Final shared count / new task | **13/13 / 1/1** |

The 75 nanoUSD accounting difference conservatively prices all input at the cache-write rate. These are local accounting/usage-price figures, not an invoice claim. Shared `blocked_reason=call_limit` and new-task exhaustion were verified read-only; no additional provider probe was sent.

## Cleanup, preservation and remaining work

Provider key and execution-grant setting are blank; the existing API was recreated using the documented staged override, with the ledger mounted read-only. The grant/checkpoint/audits remain immutable and retained, not deleted or reopened. The worker is stopped. Native web, API, database, Redis, orchestrator and two existing runtime services remain available for recorded results. Results were checked again after disconnection.

All pre-existing engineering rows (including original accounts, source solution, catalogue, contracts, draft histories and earlier captures) are unchanged. The port-23122 fixture database and all 54 old non-ledger protected files remain unchanged. Only one new draft, saved solution, execution submission, deployment and local capture were added in the qualification database. Normal sign-in audit/session records are excluded from engineering-state hashes. The ledger changed only by its authorized amendment and normal one-request reservation/settlement.

Current task recommendations remain: **AIE-18 In Review**; AIE-37 bounded qualification In Review; AIE-38 bounded structural milestone In Review and broader composition incomplete; AIE-40 integration In Review with the generic evidence-panel gap; AIE-41 In Review with that consistency follow-up and independent human acceptance pending. No tracker was updated. This one registered-workflow live result does not verify structural AI composition, independent usability or production compatibility. The pre-existing backend package-import test failure remains visible.

[Sanitized evidence](DESIGN_AI_LIVE_ACCEPTANCE_2026-10-31.json) records the response, IDs, usage, hashes and observed failure. Private raw evidence/downloads/screenshots/operator audits are retained under `<original-checkout>/local-backups/demo-acceptance-20261031/live-acceptance/`. No passwords, provider key or environment contents are included.
