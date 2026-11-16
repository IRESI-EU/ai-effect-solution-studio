# Portuguese-node review demonstration — local Builder milestone

**Local inspection demonstration, 6½ minutes.** This uses the retained local
application for a Portuguese-node audience; it is not Portuguese-hosted execution.
The completed Builder milestone is closed. No new algorithm, grant or provider
request is needed for this meeting.

## Prepare the browser

Use the existing reviewer, pt-sandbox-designer@example.test. Read the password
locally from original-checkout
local-backups/portuguese-sandbox-20261112/profile/credentials.json; never project
or publish that file. The application remains at http://127.0.0.1:23124.
Follow [CHAIN_RUNBOOK](../deploy/portuguese_sandbox/CHAIN_RUNBOOK.md) for retained
review-service availability. Keep workers stopped and supervision/provider OFF;
do not run activation, authorization, bootstrap or submission commands.

Open three tabs:

- [Executed saved workflow](http://127.0.0.1:23124/builder?solutionId=b4e48556-c3a5-4a73-903d-c2a2618756fd).
- [Completed results](http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results).
- [Disposable settings demonstration](http://127.0.0.1:23124/builder?solutionId=e26923cd-0c19-4c53-92d5-b5384a86ac2b),
  labelled **DEMO — Portuguese 20 sequences — NOT EXECUTED**.

Do not edit the executed source. The separate demonstration was built from empty
Builder because no whole-workflow copy control exists. The agent saved its default
count10, changed GenerateData to20 through the UI, then Save → refresh → Validate
passed. The CSV, identities, both 0.2.0 pins and model_ref binding survived.
It has **zero deployments and no observed settings/results**.

## Meeting sequence

| Time | Show and say |
| --- | --- |
| 0:00–0:45 | Saved workflow: selected **Sandbox test dataset**, ordered chained TrainModel → GenerateData, INSPECTION ONLY. “Training data is separate from operation settings and the trained-model connection.” |
| 0:45–1:45 | Select each step. Training epochs2/batch4; generation10. Open Setting help: declared sandbox ranges are epochs1–2, batch2–16 and generation1–20. Defaults are1/4/10; the library can clamp batch size to available training sequences. These are sandbox limits, not Portuguese scientific requirements. |
| 1:45–2:30 | Data connections → Technical details: model_ref → model_ref, whole-output-v1, pt-chain-train-v2 and pt-chain-generate-v2, both0.2.0. “Generation uses the model produced by this training task.” |
| 2:30–3:45 | Results: Completed. Raw overrides are epochs2 and omitted generation; validated defaults resolve2/4/10; observed consumption separately verifies2/4/10. Show model association/hash and10×100=1,000 CSV rows. |
| 3:45–4:30 | Show the exact model handoff and the already authenticated-downloaded CSV below. Explain the current browser-download limitation rather than clicking the blocked generic HTTP preview. |
| 4:30–5:15 | Use the historical comparison table below: genuine10/20 outputs from the **same earlier standalone model**, trained1/4. Neither belongs to today's disposable design or the latest chained model. |
| 5:15–6:30 | Disposable tab: select GenerateData, show20, Saved, Checked successfully and no execution result. “This is newly configured, not executed.” A reviewer can use a fresh /builder, add the two chained entries, Use current defaults, select CSV, connect and Use published connection, edit settings, Save/refresh/Validate. Only edit disposable designs. |

### Verified output handout and honest limitation

The completed run's model SHA256 starts e0cd2151c67a; producer-reference and
consumer hashes agree. Its generated CSV SHA256 is
553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540,
41,826 bytes. Existing local authenticated download:

    local-backups/pt-operational-live-20261116/GenerateData-authorized-output.csv

**A complete browser-only download step is not available:** Portuguese results
currently have no Download control. The protected adapter /control/data route
was authenticated and hash-verified; generic remote previews remain blocked.
Open the existing local CSV for this meeting. Do not expose the control token,
place credentials in a URL, publish CSV/model files or create an unauthenticated
file server. This presentation gap remains a separate narrow follow-up; no
download implementation was added in this documentation pass.

### Earlier genuine size comparison

| Actual run | Generation | Training/model context |
| --- | --- | --- |
| [wf-5d9b6ad6aa23](http://127.0.0.1:23124/deployments/wf-5d9b6ad6aa23#results) | 10×100 =1,000 rows | Standalone v0.1, approved earlier test model |
| [wf-956d17cb477d](http://127.0.0.1:23124/deployments/wf-956d17cb477d#results) | 20×100 =2,000 rows | Same standalone model; no additional training for this generation |

Both use model_3cfaf2a8fe78eac9f48f67af3beebc17, trained by
wf-dc54e79834df at epochs1/batch4. Current model bytes/configuration were rechecked:
SHA256 9d7af5049b4e59daf14aca1e74d50419a88c10a71ca4076a347407932ca63f22.
Opaque input was pt-approved-test-model. Their v0.1 generic consumption panels
honestly lack v2 capture support; correlated legacy captures, current model
configuration and artifact bytes establish this comparison, not those panels.
Existing original-checkout handouts generate10.csv and generate20.csv under
local-backups/portuguese-sandbox-20261112 were rehashed, not regenerated.

## Capability and limits, in plain language

Settings belong to each operation instance; each execution records an immutable
snapshot. Saving settings does not prove an algorithm used them. Signed captures,
saved-model configuration, current hashes and producer/consumer associations
provide separate consumption evidence. The platform-controlled sidecar translates
validated settings into the **unchanged original Portuguese APIs/algorithms**.
CSV data, numeric settings and model connections are separate. The one synthetic
CSV and conservative bounds are choices for this sandbox.

| Availability | Meaning |
| --- | --- |
| Local demonstration | Available now for inspection, design editing and validation |
| New supervised execution | Requires a new separately approved bounded session; all existing scopes stay closed |
| Portuguese-hosted execution | Needs owner-confirmed endpoint/auth, service/contracts, data permission/resources and deployment-specific qualification |
| Production | Availability/compatibility not established; neither scientific quality nor independent usability has been established |

[Actual local acceptance/closure](../deploy/portuguese_sandbox/operational-acceptance-20261116-verification.json)
and [this non-executing preparation](../deploy/portuguese_sandbox/demonstration-closeout-20261116.json)
are separate records. Nine prior designs, nine completed jobs, all four closed
authorizations and their audit history were preserved. Workers remain stopped;
provider/grants disabled; ledger unchanged25/25, zero outstanding. Serving images
remain the verified candidates; this pass made no code/build/deployment change.

## Next task and review dependencies

Proposed only: recommend/configure **one approved registered Portuguese workflow**,
show declared instance parameters and required authorized CSV selection, then
Create/Apply/Undo/Save into the same validated Builder. No provider reconnection
or implementation in this pass. [Extension points and acceptance criteria](PORTUGUESE_SUPERVISED_PREPARATION_2026-11-16.md#smallest-next-design-with-ai-task--proposed-not-implemented).

Review the cumulative stack: [Portal PR21](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/21)
beneath PR22; [maintained WP3 PR3](https://github.com/AI-EFFECT/ai-effect-wp3/pull/3)
beneath PR4. Authentication/ownership/artifact boundaries, active0.2.0 contracts,
canonical validation, immutable submission/journal and one-shot closure policy
remain prerequisites. Original ML is unchanged. Normal review/checks remain;
no merge, broad composer change or production approval.
