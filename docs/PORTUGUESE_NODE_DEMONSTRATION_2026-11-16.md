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
| 3:45–4:30 | Show the exact model handoff, then click **Download generated CSV** on the completed results page. The owner-authorized historical download revalidates the recorded artifact; it never runs generation. Generic HTTP preview stays blocked. |
| 4:30–5:15 | Use the historical comparison table below: genuine10/20 outputs from the **same earlier standalone model**, trained1/4. Neither belongs to today's disposable design or the latest chained model. |
| 5:15–6:30 | Disposable tab: select GenerateData, show20, Saved, Checked successfully and no execution result. “This is newly configured, not executed.” A reviewer can use a fresh /builder, add the two chained entries, Use current defaults, select CSV, connect and Use published connection, edit settings, Save/refresh/Validate. Only edit disposable designs. |

### Verified generated CSV download

The completed run's model SHA256 starts e0cd2151c67a; producer-reference and
consumer hashes agree. Its generated CSV SHA256 is
553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540,
41,826 bytes. Existing local authenticated download:

    local-backups/pt-operational-live-20261116/GenerateData-authorized-output.csv

**Download generated CSV** is now available on the owner results page. The actual
browser file matched the41,826-byte recorded hash above, including after the final
API/web update. Authentication, exact workflow/task association and current byte
integrity are checked server-side; no token/path is exposed. Generic remote preview
remains blocked. The existing local handout is retained as historical evidence.

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
and [the original non-executing preparation](../deploy/portuguese_sandbox/demonstration-closeout-20261116.json)
are separate historical records. The later download/AI integration updated only
retained API/web and the reviewer-scoped design registration. All ten prior designs,
nine completed jobs, four closed authorizations and audit history remain preserved.
Workers remain stopped; provider/grants disabled; ledger unchanged25/25, zero outstanding.

## Next task and review dependencies

The bounded registered Portuguese Design with AI integration is now implemented
and verified offline: [saved AI design](http://127.0.0.1:23124/design-ai?draftId=91a37168-92af-47a8-b4d3-f28eb9476be8),
[its new unexecuted Builder design](http://127.0.0.1:23124/builder?solutionId=07c9449a-48f5-4da4-b06c-b1bc9f765ba8).
To demonstrate controls, choose the registered workflow, select the sandbox CSV,
review a supported change, Apply/Undo/reapply, then Save and open Builder. Use only
disposable copies. No chat messages are needed while AI is disconnected. The actual
agent path passed Save/refresh/Validate at2/4/20 with no execution. Recommendation
interpretation was tested only with isolated deterministic doubles; no genuine
provider or independent usability pass is claimed. [Current evidence and later
provider prerequisites](PORTUGUESE_DESIGN_AI_INTEGRATION_2026-11-16.md).

Review the cumulative stack: [Portal PR21](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/21)
beneath PR22; [maintained WP3 PR3](https://github.com/AI-EFFECT/ai-effect-wp3/pull/3)
beneath PR4. Authentication/ownership/artifact boundaries, active0.2.0 contracts,
canonical validation, immutable submission/journal and one-shot closure policy
remain prerequisites. Original ML is unchanged. Normal review/checks remain;
no merge, broad composer change or production approval.
