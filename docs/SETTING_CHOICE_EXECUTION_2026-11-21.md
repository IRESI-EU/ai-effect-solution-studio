# Genuine target-choice execution - 21 November 2026

**The genuine South-only conversation and browser Apply/save/reopen passed. The six-request evaluation stopped at D's semantic failure: four requests attempted, E/F NOT_ATTEMPTED, scope CLOSED.** No retries, fallback, workflow Runs or production deployment occurred. No product, prompt, schema, model or evaluator source was changed during execution.

[Complete sanitised execution record](verification/setting-choice-executed-20261121.json) includes every attempted structured response, machine screening result, semantic verdict, per-attempt accounting and fresh browser evidence hashes. [Frozen preparation](SETTING_CHOICE_ACCEPTANCE_2026-11-21.md) remains historical; its NOT_ATTEMPTED status describes preparation, not this execution.

## Exact approved and executed identity

- Approved publication: `33b4231d04b00c2eac9da625278fa2f69d310085`, branch `codex/setting-choice-acceptance-20261121`.
- Frozen manifest SHA-256: `63181bd68495454934874a2088fb9c39bca8041c03d7264ca3832012f60bbd0a`.
- Evaluator source: `20821d2af5bd9b9a395db29fdb3edacd79aef3ed`; corrected product source: `439e078d46c5128f3a75d7cbe233bcb4f4d4dda4`.
- Model: `gpt-5.4-mini-2026-03-17`, reasoning `none`, Standard/default tier, Responses, `store=false`, no tools, `max_retries=0`, no fallback, 60-second timeout. Maximum 64,000 input / 3,000 output tokens per request.
- Configuration SHA-256: `5d1f2e65cb16d2c651e75c69345c51b615263d495dc460a66ab97e996a6ea0e5`.
- Prompt SHA-256: `3e5c65e3dc25e7d7149fe0cc5e4e55a9dc4bed9e53069af4a2fec1b52d7291d8`.
- Wire schema SHA-256: `be5c2f476b825e4ddf105d654f17f65b49b70a442354a7d1ad6eb62bdd09ba93`.

The user's separate approval covered at most six attempts and USD 0.4059, including conditional browser verification with zero extra model calls. Frozen checks and existing accounting gates were honoured before each dispatch. Credentials were privately loaded only after authorisation and reservation. No previous scope was reopened.

## All six requests and observed outcomes

| Case | Genuine model behaviour | Application behaviour and reviewed result |
| --- | --- | --- |
| A: ambiguous original request | Guessed Generator North, maximum 2; did not ask which instance. | **PASS user-facing boundary: model guessed; application contained it.** The application displayed its own current North/South choice, stored no guessed proposal, and preserved the exact earlier pending review and saved graph. This is not successful model clarification. |
| B: explicitly select South in A's SAME actual conversation, then original request | Returned the current South setting action, maximum 2 only. | **PASS.** Explicit authenticated application choice was honoured. Complete candidate equalled the frozen oracle; North stayed 4, both generators' flags stayed true, and earlier pending title, input, Drawing A and connections were preserved. The genuine proposal subsequently passed browser Apply/save/reopen. |
| C: isolated already-satisfied maximum 2 | Returned the correct singleton setting action at 2. | **PASS.** Application independently established no change, displayed factual no-change text and created no redundant proposal or saved mutation. |
| D: isolated maximum 99 plus unpublished turbo_mode | Identified the unpublished setting and published maximum 4, but offered to set 99. | **FAIL_STOP after semantic review.** No action, proposal or saved mutation occurred, but the clarification failed to request a valid supported value. Provider transport, schema parsing and application processing succeeded. |
| E: isolated exact single-target original repeat | **NOT_ATTEMPTED** | Stopped at D; no provider request or case spending ledger. |
| F: isolated single-target paraphrase repeat | **NOT_ATTEMPTED** | Stopped at D; no provider request or case spending ledger. |

Every attempted machine screen returned `REVIEW_REQUIRED`; none was treated as PASS automatically. Concrete inspection established A/B/C PASS and D FAIL_STOP before any next dispatch. C and D used independent state. A/B shared the same physical database, owned solution and actual conversation; B continued A's actual application clarification, with no fabricated prior reply. B's explicit choice used the existing authenticated application selection path; the later browser journey reviewed and applied that real proposal.

D's critical text was: **"Should I set how_many to 99 (noting the published maximum is 4)"**. Recognising a limit while offering to exceed it does not satisfy the frozen requirement for refusal or clarification toward a valid supported choice. The application displayed this misleading question without creating an actionable edit. This is a model interpretation/semantic failure, not a parsing failure or a failed provider request. Stop and closure followed immediately; the failed response is retained in full in the sanitised record.

One manual B comparison initially compared rotating review-scoped connection references. A subsequent read-only comparison verified the actual raw connections and complete materialised candidate matched the frozen oracle. No request was repeated and no state was repaired.

## Spending after every attempt

[Official model pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini), rechecked before activation on 21 November 2026, was USD 0.75 input / 4.50 output per million tokens. The existing accounting adds 10% conservative headroom and reserves USD 0.06765 per attempt. Actual usage reported no cached or reasoning tokens.

| Case | Input / output tokens | Conservative estimated USD | Cumulative USD | Uncertain USD | Remaining authorised calls / reservation USD after review |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 10,988 / 186 | 0.009985800 | 0.009985800 | 0 | 5 / 0.33825 |
| B | 11,355 / 187 | 0.010293525 | 0.020279325 | 0 | 4 / 0.27060 |
| C | 6,616 / 124 | 0.006072000 | 0.026351325 | 0 | 3 / 0.20295 |
| D | 6,645 / 129 | 0.006120675 | **0.032472000** | **0** | **0 / 0 - CLOSED** |

Four total requests used 35,604 input and 626 output tokens (36,230 total). Base list-price estimate: USD 0.02952; conservative accounted estimate: **USD 0.032472**. Lifetime reservations totalled USD 0.2706, all four child ledgers settled and closed, with zero uncertain reservations. Unused two-call reservation capacity of USD 0.1353 supplies no authority after closure. The parent is CLOSED and next dispatch is forbidden. Actual account balance and invoice were not observed.

## Fresh genuine browser proof

The existing guarded starter reported READY, then actual UI/API health checks returned 200. Working local UI: [genuine settings demonstration](http://127.0.0.1:23138/builder?solutionId=f84b2e36-7b5c-4f03-8214-f27a59e69dce); API health: [28272/health](http://127.0.0.1:28272/health).

Serving publication is `33b4231d04b00c2eac9da625278fa2f69d310085`, product `439e078d46c5128f3a75d7cbe233bcb4f4d4dda4`, evaluator `20821d2af5bd9b9a395db29fdb3edacd79aef3ed`. This is the existing local Python/Node source starter and Next 16.3.8 build, not a new Docker image. No dependencies, full stack or ML runtime were installed. The review server has no provider key, blocks further chat and workflow Runs, and exposes the same A/B fixture database for review.

Observed browser actions: normal independent fixture-designer sign-in; Solutions; Edit in Builder; inspect the actual South-only proposal and complete candidate; **Apply and save reviewed changes**; observe saved confirmation; **Solutions**; reopen the SAME solution; inspect South 2 and North 4 with both flags checked. No direct Control or Apply POST substituted for these browser actions. Browser verification made zero extra model calls and zero workflow submissions.

Solution `f84b2e36-7b5c-4f03-8214-f27a59e69dce`, titled `FIXTURE earlier pending review A-ambiguous`, is still available. Complete saved-content SHA-256 equals the reviewed candidate and frozen oracle:

`36bac69425d599102f59eda3d21161941c77c20a2ee31f2997b3b25b0246ce16`

The exact earlier pending title was incorporated; all unrelated content, flags, input and raw connections were preserved, and the applied pending review was cleared normally. Read-only post-Apply and post-reopen snapshots confirm the entire design, beyond the two visible numbers.

Fresh evidence: [genuine proposal review](verification/genuine-choice-review-20261121.png), [South value 2 after reopen](verification/genuine-choice-south-value-20261121.png), [North inspector](verification/genuine-choice-north-value-20261121.png), [reopened South inspector](verification/genuine-choice-reopened-south-20261121.png), [final reopened solution](verification/genuine-choice-reopened-final-20261121.png). Some full-page inspector images clip the numeric control; the dedicated South viewport capture and actual accessibility/complete-content checks establish the values. These are new genuine-run images, not recycled offline screenshots.

## Preservation, inference and next problem

The original checkout remains on `feature/design-with-ai-pilot` at `12aae82dd47b078ba077aca40b0712c375b9d7f3`, with all 150 dirty entries preserved. Both historical hash baselines (49 and 23 files) remain byte-identical, including successful demonstrations, exact earlier failures and closed accounting. Retained login endpoints 23124, 23125 and 23134-23137 still returned 200, alongside new 23138. No retained server, container, saved design/result, model/state volume or old spending scope was stopped, reset or reused for this evaluation.

The evidence supports a narrow conclusion: the corrected application contains this real ambiguous guess; explicit South selection leads to the right genuine South-only proposal; the normal browser review/save/reopen persists that complete design; and application no-op handling works for C. It does not establish reliable model clarification or general settings interpretation. D demonstrates that a model can describe a validation limit yet still invite an invalid action. Earlier genuine boolean/saved-edit successes remain historical, not current-version qualification; E/F remain untested here. No runtime/model execution, scientific provider approval or platform production acceptance is claimed.

**Next specific problem:** repair invalid-setting conversation handling offline so a known out-of-range request leads to refusal or a useful valid supported choice, without offering the forbidden value. Preserve this exact D evidence and the working A/B demonstration. No repair or new metered retest was performed in this frozen acceptance run.

A restricted shared settings-editor pilot remains gated on that correction and bounded genuine evidence for the previously unattempted original/paraphrase behaviours; current-version boolean, saved-edit, ownership and stale/conflicting-edit coverage; a named approved participating group and service parameter contracts; durable shared key/budget/expiry/concurrency controls; per-user/solution accounting, audit and rollback; and continued explicit review/Apply with execution kept behind Run. Partner scientific approval and production security/operations remain separate requirements. This evaluation does not make the platform production-ready.
