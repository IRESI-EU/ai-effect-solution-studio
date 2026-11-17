# Portuguese local review: ten-minute colleague walkthrough

**READY, NOT YET PERFORMED.** This is a human observation plan, not a usability pass.
Use the retained local reviewer browser on this computer. Provider and execution
are disabled. Do not Create, Apply, Undo, Save, send chat or run an experiment.

Sign in at http://127.0.0.1:23124/login as `pt-sandbox-designer@example.test`.
Read the existing password privately from the original checkout's
`local-backups/portuguese-sandbox-20261112/profile/credentials.json`.
Do not copy it into notes, screenshots or chat. Sign-in may remove a URL's query;
after sign-in reopen the exact link below. No new account or permission is needed.

Give the colleague these tasks without explaining the expected answers. The
observer records help and misunderstandings on the [blank observation sheet](PORTUGUESE_HUMAN_OBSERVATIONS_2026-11-17.md).

| Time | Colleague task and exact page |
| --- | --- |
| 0–2 min | [Read the genuine recommendation](http://127.0.0.1:23124/design-ai?conversationId=146618a1-7c78-43d0-87e4-824bd59fa045). Explain what is offered, what input is required and whether anything has been created or executed by that recommendation. Do not click Create. |
| 2–4 min | [Inspect the saved design](http://127.0.0.1:23124/builder?solutionId=28f62cd4-27c4-4e8d-a933-489e66530389). Find the selected Training CSV and inspect each processing step's settings. Explain what the settings mean. Do not change them. |
| 4–5 min | On the same Builder page, find Data connections. Explain how the generated model reaches GenerateData. Open Technical details for the connection if needed. Distinguish training data, instance parameters and the model connection. |
| 5–7 min | [Inspect historical completed results](http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results). Explain requested overrides, validated effective settings and observed algorithm consumption. Which design/run produced these results? Do they belong to the new count-20 design? |
| 7–8 min | On that results page select **Download generated CSV**. Explain what was downloaded and its generation size. No new algorithm runs when downloading historical output. |
| 8–10 min | [Inspect the unanswered ambiguity](http://127.0.0.1:23124/design-ai?draftId=b2e9a2b4-95f7-4a79-9a55-b27679ed99d3). Explain what “size” leaves unclear and what the assistant needs clarified. Identify the independent missing-CSV instruction. Leave the clarification unanswered. |

Conversation text is retained in this reviewer's browser storage; draft/designs
are server-owned. A different browser/device may not have the historical chat.
If text is missing, record that inspection limitation and read the genuine text
in the [unchanged acceptance evidence](PORTUGUESE_PROVIDER_ACCEPTANCE_RESULTS_2026-11-16.md)
and its [sanitized actual responses](../deploy/portuguese_sandbox/provider-acceptance-results-20261116.json).
Do not re-send requests or reconstruct the conversation. On this retained browser,
the genuine recommendation and unanswered question were inspected successfully.

## Observer reference — consult after the colleague answers

The new saved design has epochs **2**, batch size **4**, generated sequences **20**,
Sandbox test dataset selected, and `model_ref` → `model_ref`, whole-output-v1.
Pins are `pt-chain-train-v2` / `pt-chain-generate-v2`, version **0.2.0**.
It has **no execution or results**. The genuine recommendation originally described
defaults **1/4/10**; the later genuine B proposal configured the saved **2/4/20**.

Historical **wf-717110fb8d5e** belongs to executed source solution
`b4e48556-c3a5-4a73-903d-c2a2618756fd`, not the new saved design. It completed one
training at **2/4** and one generation of **10 × 100 = 1,000 CSV data rows**.
Requested overrides are epochs2 and no generation override; batch4/count10 are
validated defaults. Separate capture/model-file evidence verifies actual consumption.
Producer TrainModel `task_030152d9` and consumer GenerateData `task_f6c5c14e`
are qualified by this workflow. Both share model SHA-256
`e0cd2151c67a247856bb360fb1aea1525091da26a9a8b002fd66ee0b1d0a7b4d`.
Downloaded CSV is **41,826 bytes**, SHA-256
`553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540`.

The unanswered question distinguishes generated sequence count from training
batch size. No proposal or draft mutation followed it. CSV selection is a
separate requirement. Local controls and conservative bounds are sandbox choices;
the sidecar maps validated settings into unchanged original Portuguese APIs.
Saved settings alone do not prove algorithm consumption. New executions need a
separately bounded authorized session. Portuguese-hosted and production operation
are unqualified.

Agent inspection, code changes, source/image identities, rollback and review order:
[review handoff](PORTUGUESE_REVIEW_HANDOFF_2026-11-17.md). Agent checks are not
colleague observations.
