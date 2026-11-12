# Platform-controlled parameterisation proof — 12 November 2026

**Passed for the exact isolated qualified implementation below.** Two real local
workflows executed, exactly once each: seed 42 and seed 43. No provider request,
spending-policy change, partner deployment or production execution occurred.
This is a separate acceptance record; earlier failed observations are preserved.

## Meeting handoff

**Start:** http://127.0.0.1:23121/builder?solutionId=512fe7bc-691b-42c2-a9fa-7b8e45d4cb22

Use the existing email/password from the original checkout's private
local-backups/aie37-profile-20261028/reviewer.json record. Do not print, publish,
reset or copy its password into a runbook. The browser's existing designer session
is signed in. Both the starting Builder copy and results page are left open.

| Recorded seed | Completed results | Saved owned copy |
|---|---|---|
| 42 | http://127.0.0.1:23121/deployments/wf-3cc4e38fc14a#results | be7e21a3-5971-457f-b19f-d50e5f1b3c38 |
| 43 | http://127.0.0.1:23121/deployments/wf-386fded9b8bb#results | 512fe7bc-691b-42c2-a9fa-7b8e45d4cb22 |

Five-step browser sequence, requiring **no new execution**:

1. Open the starting Builder. Select generation; inspect saved seed 43 and the
   connection to the benchmark. This is a disposable, existing-designer-owned copy.
2. Return to its Design with AI draft using the normal link. Supported input
   settings can review a seed change without AI: Review → Apply → Save → reload.
   The agent already verified 43 → 42 and back to 43 through these browser controls.
   Leave the prepared seed 43 unchanged until the meeting, or deliberately edit
   only this disposable copy. Saving does not execute anything.
3. Open the seed-42 results link. Show both completed tasks and recorded seed 42.
   Its current disposable design was later changed and saved as 43; its immutable
   submitted/consumed settings and captures remain 42.
4. Open seed-43 results. Compare requested overrides, effective settings and
   separately verified generator consumption. Benchmark input verification is
   distinct from generator parameter consumption. Inspect the four download links.
5. Explain that these are completed historical captures. The existing no-op
   benchmark agent, unknown KPI units and lack of scientific/production
   qualification remain limitations. Do not request another run.

Provider is disconnected; execution grant path is empty again. Send remains
paused at the unchanged **13/13** provider allowance. Newly composed workflows
do not inherit execution permission or qualification.

## What is proven

| Boundary | Evidence |
|---|---|
| Individual instance settings | Focused duplicate-instance regression edits only second seed 42→43, Save/reloads, makes an independent owned copy and compiles [42,43]; node IDs and pins remain stable. Explicit test doubles/disposable database. |
| Actual browser persistence | Existing designer reviewed/applied/saved/reloaded 43→42→43 using supported local controls; normal routes and revision checks remained authoritative. Agent observation, not independent usability. |
| Copy and saved design | Two separate owned copies were created from the actual registered template, with its current server authority revision. The initial request without that revision was denied; no guard was bypassed. Source template and all old designs are unchanged. |
| Compilation/submission | Before each run, live readiness passed and the immutable server snapshot was inspected for exact seed, contract pin, logical instance ID, workflow chain, runtime destination and one-use authorization. |
| Real receive/consumption | Real InputConfigurator and PowerGridGenerator constructors observed 42/43; create_params and generate_grid returned before consumption observations were recorded. Actual algorithms, not constructor doubles, ran in these two cases. |
| Real negative boundary | Five invalid seed/type/unknown-setting requests were rejected by the actual local service before capture claim/generation. The maintained WP3 client's live capability handshake rejected a wrong contract version before dispatch. Focused tests additionally cover conflicting sources and no mutation. |
| Immutable exact-grid binding | Per-workflow/task immutable manifest digest and grid-file hash from producer match benchmark input and its captured association. No latest-cache lookup is accepted as proof. |
| Authorized results | Both tasks completed per workflow; four downloads per run returned 200 with matching SHA-256, private/no-store headers, and anonymous access returned 401. |
| Historical independence | Later Save of the disposable seed-42 design as 43 left both original submitted snapshot digests, consumed settings and all eight artifact hashes unchanged. Both results pages refreshed successfully. |

Task IDs are task_60e852c4 (generator) and task_e23bc51c (benchmark), scoped by
their distinct workflow IDs. Seed 42 produced a recorded 174-node/213-edge grid;
seed 43 recorded 169 nodes/206 edges. These counts are observations, not a
scientific quality or determinism guarantee. Each benchmark recorded one scenario,
one episode and 11 steps using the retained no-op agent. [Sanitized machine
evidence](PARAMETERISATION_PLATFORM_VERIFICATION_2026-11-12.json) contains snapshot,
manifest and artifact hashes; no raw capture payloads or private grants are published.

## Executable source and actual served identities

Review branch: codex/platform-parameterisation-verification, draft
[PR #18](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/18), stacked on
[PR #17](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/17) at c93848e.

| Checkpoint/component | Exact identity |
|---|---|
| 1 — executable instrumentation, provenance and tests | c75d134628736ee5f3991be7391f3a991d3cbd09 |
| 2 — integration/startup and offline source-layer packaging | cfc0a850548c58a39eb669455b60545c49f0f450 |
| Maintained WP3, unchanged PR #3 | 0221b7ecd4a2d5f072de640350ebc599df22131a |
| Generator image | sha256:591d9071764ff37770125c4c8c5b4476feec60974ff5f9edb3012f6e1c59a18d |
| Benchmark image | sha256:08eec9c82062b08e06b68f2c16574e7a698b8e999e021236f42b509438c5a8ab |
| WP3 API/worker image | sha256:edcac597f327dc817ff0c9b9c930dbf9b4cb62235d42f2ef1940845ca1820a21 |
| Retained API candidate reused | sha256:3717c012fed8d8cd4f04469335b8f93a42224708f54dfd08c3b6858aa4d74c19; app source 7165a398c1583daae567fb5cf48aabf35fe32a7b |
| Retained web candidate reused | sha256:fba983fef01d461e79db22444c34c76b9737df84365d200972085672a4052614; source 4ff3285bdaf6cd0951b946b1d1667212b197e74d; BUILD_ID XLX_batDPkRXN0X7avzOq |

The API/web application trees are unchanged by this milestone, so their existing
verified images are reused honestly at their original source labels. No UI
redesign, new application build or unrelated full suite occurred. WP3 has no new
source change/PR; packaging exports its exact maintained commit. Twenty-four
served Python files match committed source after explicit CRLF→LF normalization;
served/raw and canonical hashes are recorded separately. Windows git archive
applied checkout line endings; this is not hidden as byte-for-byte Git-blob parity.

The platform-owned deploy/aie37/runtime.py now observes both real algorithm
boundaries. It rejects invalid requests before CaptureStore claims/writes and
restores instrumented classes after execution. The previous topology consumption
field remains compatible, with algorithm_consumed_steps adding per-method
observations. Historical captures keep their original runtime pins and do not
need the added field. Existing local contracts and accepted [42,43] scope are
unchanged, not broadened to the partner patch's proposed bounds.

The partner parameter patch is **not** incorporated/deployed. The recorded
partner baseline ba598b2459f9986dac4e37dcc5d7d3298f25dc3a has no license file;
no new redistribution right or owner approval is inferred. This milestone
changes only previously maintained platform adapter code and reuses retained
local dependency images. It does not publish new partner images/source.
Underlying dependency commits remain those in the previous qualification:
powergrid_synth b36740438a95db60d30f3681daa72a26e1d2dd73 and the retained benchmark
dependency pins. Local reuse is not a partner/source licensing attestation.

## Tests and recovery record

**80 focused tests passed** on the runtime changes: validation, persistence,
compilation, evidence and qualified execution guards. Then the explicit
second-only edit regression passed, and the existing composed-execution-denial
regression passed separately: **82 distinct focused checks**, with fixture
algorithm/runtime/provider doubles clearly separate from the **two real runs**.
No complete backend inventory or unchanged-web typecheck/build was repeated.
Warnings remain visible in private logs.

Intermediate findings remain recorded: the first pytest path failed to create
fixtures; a shorter path passed. The new test initially looked for runtime
instance_id inside editable Builder configuration; its assertion was corrected
to the actual Builder node identity and compiler boundary. A legacy /_api URL
returned 404; the actual candidate web proxy is /api (not an incorrect-password
failure). An initial raw source check detected checkout line endings; canonical
comparison and raw hashes document them. No failed algorithm/submission was
retried: both actual workflows were submitted exactly once and passed.

The existing ai-effect-aie37 project was reused, with the same database, accounts,
contracts, evidence volumes, network and ports. No separate profile/port was
created. Required stopped services were restored after Redis inspection showed
zero queues and only the two existing completed workflows. Original database
container identity was retained. Runtime/orchestrator/API source layers were
updated locally; the verified web image replaced the positively identified native
port-23121 process. Its native build/startup records remain retained for rollback.

Before changes, pg_dump produced a consistent 39,621-byte backup, SHA-256
237fb36b66b18930c22af7ae05eae3eb9fabe41052c1e764e283becbdfeff527.
All **18** previous capture-file hashes and every snapshotted original solution,
service, contract, draft, submission and capture row are unchanged. The original
wf-1b6eb7caaf57 results remain accessible with recorded seed 43. Existing normal
login/session/audit metadata changes are not falsely called bitwise unchanged.
No production, partner, account/permission, tracker or merge operation occurred.

Provider accounting is byte-identical: 13/13, USD0.10 ceiling, USD0.004207375
conservative held usage, USD0.095792625 conservative remainder, zero outstanding;
new calls/spend **0 / USD0**. The two distinct normal one-use execution grants are
consumed, retained privately, and disconnected. No exhausted checkpoint reopened.

## Operation and storage

Maintained packaging/startup:
deploy/aie37/build_parameterisation.py and parameterisation.compose.yaml.
The builder uses tracked source only, retained exact bases, --network=none,
--pull=false, new tags and no dependency installation. Existing images remain.
The overlay combines only with the retained compose.yaml and demo.compose.yaml.
Provider key is empty and PARAMETER_GRANT_PATH must remain empty.

Private operational records under the original checkout:
local-backups/parameterisation-e2e-20261112/ — consistent backup, original container
inspection, source manifests, build logs, runtime.json, consumed grant files,
pre-submission snapshots, read-only verification, preservation and browser images.
None is uploaded wholesale. Current disk free space was **20.09 GiB** after
packaging; no cleanup was needed.

For a later operator-controlled restart, load the same private profile/allowance/
authorization directories as AIE37_PROFILE_DIR, DEMO_ALLOWANCE_DIR and
DEMO_AUTHORIZATION_DIR; set PARAMETER_RUNTIME_FILE to that record's runtime.json
and PARAMETER_SYNTH_IMAGE / PARAMETER_BENCHMARK_IMAGE / PARAMETER_WP3_IMAGE to the
exact IDs above. Keep PARAMETER_GRANT_PATH empty. Use:

~~~text
docker compose -p ai-effect-aie37 -f deploy/aie37/compose.yaml -f deploy/aie37/demo.compose.yaml -f deploy/aie37/parameterisation.compose.yaml up -d --no-deps --no-build --pull never api web seed-synth seed-benchmark seed-orchestrator
~~~

This command deliberately omits workers. A worker may start only after a fresh
read-only Redis queue/nonterminal-workflow audit; do not resume an old unapproved
job. Normal meeting inspection needs no worker dispatch. Never run down -v,
restore the old backup over new captures/designs, rebuild historical images or
reconnect a provider/grant merely to show this proof.

Recheck completed results without any execution:

~~~text
python deploy/aie37/inspect_parameterisation.py --original-checkout <original-checkout>
~~~

The helper uses normal existing-account login and authorized GETs only, verifies
both completed runs and eight protected downloads, and prints no credential.

## Limits and production blockers

This proves platform-controlled, local qualified setting delivery and immutable
recorded consumption for these two seeds on this exact implementation. It does
not qualify arbitrary composition, arbitrary settings, real AI interpretation,
partner-native transport/output behavior, scientific KPIs, concurrent physical
operation or independent human usability. The partner latest-cache implementation
is not used as association evidence and is not repaired by this work.

Production release still needs cumulative code review, normal existing production
sign-in/reviewer identification, responsible service-family/contract/licensing
decisions and the separate accounting transport/activation prerequisites. Dutch
owner involvement was not required for this platform-controlled local proof and
no owner confirmation was manufactured. AIE-18 remains In Review; broader
composition and production compatibility remain unverified.
