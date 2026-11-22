# Setting-validation guidance correction - 22 November 2026

**The focused correction passed 76 offline checks and a fresh browser invalid-request -> accurate guidance -> valid choice -> review -> Apply/save -> Solutions -> reopen journey. No new genuine-model acceptance is claimed.** New paid calls, cost, spending scopes and workflow submissions: zero. Historical D remains FAIL_STOP, E/F remain NOT_ATTEMPTED and every old scope remains CLOSED.

[Sanitised observed evidence](verification/setting-guidance-offline-20261122.json) includes all 76 test names, actual browser messages, complete saved/candidate hash, screenshot hashes and preservation checks. [Previous execution report](SETTING_CHOICE_EXECUTION_2026-11-21.md) and its exact failed D response are unchanged.

## Starting point and focused implementation

Parent execution checkpoint: `f4674e48eda79f740a2ae9e80cf67572ce38099f`. Isolated development branch: `codex/setting-guidance-20261122`. Implemented/serving source: `d270a250ee4c4f55666428d97617a81aaaec5d89`; the later publication adds the captured-A/B regression and this evidence, without changing product behaviour.

D's historical response was structurally valid clarification prose. It identified the maximum of 4 but asked whether to set 99; the application displayed that question without invoking parameter validation. Exact historical validated-response SHA-256: `5dfc7e25e904619816ebd858701c03c02584dc6995229a161e6c0472c1897b27`. It was not applied and is not retroactively marked PASS.

The correction keeps the existing saved-solution, ownership, target-choice, candidate validation and explicit Apply/save path:

- `SavedSolutionResponse` adds one small `setting_guidance` outcome with `setting_diagnostic`: only the interpreted scoped target and supplied name/value pairs, bound to the current saved/pending base. No model-written limits, correction question, prose, assumptions or edit can accompany it. Extra fields, duplicate names and malformed values are rejected by the strict contract. A diagnostic is never adapted into an edit, even when its values are valid.
- The application resolves current published execution parameter definitions from the owned validated design. It derives supported names, types, minimum/maximum and enumerated choices, then renders its own guidance/question. The portable shared validator checks each supplied property independently through `parameter_issues`, so an unsupported name does not hide another range/type error. Omitted properties are not filled or treated as missing from this partial request.
- Untyped clarification/unsupported prose is withheld and replaced with neutral current published choices. The exact old D response therefore cannot offer its forbidden value. No phrase matching or numerical/name special case identifies it. Answer-only prose in an explicit Builder-setting-target or existing guidance context receives the same fallback.
- Guidance explicitly says the assistant did not produce a validated edit; its structured interpretation is `NOT_VERIFIED`. It does not pretend to have correctly interpreted an unstructured response. Malformed/provider-response failures remain errors (502) with useful application-derived choices; invalid setting actions remain rejected (422) with published guidance. No fallback provider, retry, clamping, invented setting or substituted value is introduced.
- Diagnostics must match the current solution/review and scoped reference. Stale or conflicting bases/targets are rejected, including a diagnostic that ignores an authenticated Builder selection. Saved content and exact earlier pending work remain intact. Only a subsequent valid setting action can produce a normal reviewed candidate.

The existing provider prompt now requests this small diagnostic for invalid names, values or types instead of model-written correction advice. Model/configuration selection, accounting and runtime guards are unchanged. The new schema was converted offline using the existing SDK strict-schema helper. The [official OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs) describes schema-constrained responses; application checks still supply the domain facts and current authority. No provider request was made to test the new prompt/schema.

No root AGENTS.md exists; the existing web AGENTS.md was read. No frontend source or dependency was changed. The browser fixture reuses the existing offline copy/authentication/source starter with only a supplied two-response replay and separate profile/ports, not another general evaluation framework. Its script is never imported by normal production startup.

## Observed offline checks

The focused suite passed 75 cases, followed by one additional captured-A/B regression: **76 passes, zero failures**. Existing Starlette/httpx, Pydantic config and UTC datetime deprecation warnings remain; no dependency was installed.

| Verification | Observed result |
| --- | --- |
| Exact captured D clarification | Unsafe message/question withheld; current published choices rendered, interpretation explicitly unverified; saved design and exact earlier pending review retained. |
| Out-of-range, unknown name, wrong type | Shared validator diagnoses maximum/minimum/type errors and unsupported names. Supported choices contain only published names. Multiple invalid fields are checked independently. |
| Malformed/forged diagnostic | Invented limits/prose, null or duplicate assignments, stale base, foreign reference and conflicting selected target cannot replace existing work. Useful error guidance remains available. |
| Subsequent valid choice | Correct reviewed partial change; earlier pending title, other instance settings, input and raw connections retained; normal Apply/save succeeds. |
| Historical genuine A/B actions, OFFLINE replay | Only current scoped target/base rebound to the software fixture. A's North guess is contained with exact earlier review retained; authenticated South choice allows B's South-only action, preserving North and unrelated fields. This is regression evidence, not a new genuine interpretation result. |
| Existing paths | Single-instance numerical/boolean edits, no-change, saved-setting edits, ordinary owned-solution review/save/undo, target-choice/stale-state checks and provider strict parsing continue to pass offline. |

## Actual offline browser demonstration

The new source starter reported READY; real UI and API health checks returned 200. [Open the completed offline demonstration](http://127.0.0.1:23139/builder?solutionId=d4bb671d-d14c-4052-b13c-6b71b7bc2cc3). API: [28273/health](http://127.0.0.1:28273/health).

The serving source is `d270a250ee4c4f55666428d97617a81aaaec5d89`, using existing host Python/Node dependencies and Next 16.3.8, with a separate database/cookie and no provider key, spending ledger, worker or ML runtime. No Docker image/container was started or changed. Workflow submission/runtime verification remain blocked. Both page banner and assistant explicitly identify **OFFLINE / SCRIPTED RESPONSES / NO MODEL / NO RUN**.

Normal designer sign-in -> Solutions -> Edit in Builder -> select Generator North -> enter the exact D request. The fixture supplies D's exact historical response, not a newly successful interpretation. The application displays published `allow_hx`/`allow_bypass` booleans and `how_many` integer range 1-4; it does not display the model's unsafe correction question or invent another option. The saved graph and earlier pending title review remain byte-for-byte equivalent to the pre-request snapshot.

The designer then enters the documented valid choice of 2. A second explicitly scripted response supplies the setting action. The application independently displays the actual 4->2 diff and full candidate, retaining the earlier title and all other fields. Browser **Apply and save reviewed changes -> Solutions -> Edit in Builder** reopens the SAME solution `d4bb671d-d14c-4052-b13c-6b71b7bc2cc3`, now titled `OFFLINE guidance - earlier pending title` (the UI uses an em dash). The inspector shows maximum **2**, heat exchangers **true**, bypasses **true**. No direct API Apply/Control request substituted for the browser actions.

Complete raw saved-content hash equals the full reviewed candidate after Apply and after reopening:

`7b97399b952d2dad8dc46c7fb1a05c19e1602afd422cb395b861091766a0bf1f`

Fresh evidence: [invalid request and preserved prior review](verification/offline-setting-guidance-invalid-20261122.png), [accurate published-choice guidance](verification/offline-setting-guidance-published-20261122.png), [valid reviewed change](verification/offline-setting-guidance-review-20261122.png), [reopened saved value and flags](verification/offline-setting-guidance-reopened-20261122.png). Raw owned snapshots and accessibility values supplement screenshots; full-page capture can omit offscreen conversation text. Automatic approval review rejected an attempted focus click on the numeric stepper because it could edit the value. Read-only capture and the already visible value completed verification, with no approval-dependent action left blocked.

## Preservation and limits of the result

All **77 historical evidence/demo/accounting hashes** remained byte-identical, including both older baselines, exact failed D evidence, four closed current-case provider ledgers and the genuine A/B saved database. The original checkout stays on `feature/design-with-ai-pilot`, `12aae82dd47b078ba077aca40b0712c375b9d7f3`, with 150 dirty entries preserved. Retained login endpoints 23124, 23125 and 23134-23138 remain healthy, alongside new 23139. Containers, model/state/evidence volumes and old spending grants were untouched.

The [successful genuine South-only demonstration](http://127.0.0.1:23138/builder?solutionId=f84b2e36-7b5c-4f03-8214-f27a59e69dce) still serves its previous approved build. Its old accounting remains four attempts, conservative USD 0.032472, uncertain USD 0 and remaining authority zero. E/F are historical NOT_ATTEMPTED cases, not silently completed by these offline tests.

The new application behaviour is demonstrated offline. Genuine interpretation of the new diagnostic contract/prompt is **unverified**. Untyped clarification/unsupported replies now receive neutral published-choice guidance rather than their original model question. This is a safe fallback, not proof of understanding arbitrary workflow questions; unselected general answer prose and broader workflow conversation are not newly qualified here. Scientific/provider-owner, runtime, shared-user pilot and production acceptance remain separate.

**Smallest next genuine check: two requests in fresh isolated state** with an earlier pending review. First send the D invalid-name/out-of-range request, inspect the actual structured diagnostic or honest application fallback, and require truthful supported guidance with no work lost. Then send one valid explicit setting choice in that SAME actual conversation, requiring the correct partial reviewed change; conditional browser Apply/save/reopen adds zero model calls. Freeze the new source/prompt/schema and expected content before dispatch, use separate concrete approval and new bounded accounting, make no retries/fallback and stop on failure. Do not reopen this or any previous scope. E/F remain unattempted historical behaviours for subsequent qualification; this pass requests no spending approval.
