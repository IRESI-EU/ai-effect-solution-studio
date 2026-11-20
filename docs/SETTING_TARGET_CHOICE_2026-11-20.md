# Ambiguous setting target correction — 20 November 2026

**Offline correction and browser demonstration passed. No genuine-model retest was made.**

Development branch: `codex/setting-target-choice-20261120`, based on published execution checkpoint `32f099c15545e3223f3f3980e6056f5f1366827e`. Serving implementation: `7c3f4b752e520cb4e504316118e7a4dcaa396a2f`. Later commits add evidence only. No WP3 changes, dependency installation, production deployment, merge or workflow Run.

[Sanitised observed outcome](verification/setting-target-choice-20261120.json) · [Unresolved choice with earlier pending work](verification/target-choice-question-20261120.png) · [South-only review](verification/target-choice-review-20261120.png) · [Reopened South value](verification/target-choice-south-value-20261120.png) · [North unchanged](verification/target-choice-north-value-20261120.png) · [Complete reopened view](verification/target-choice-reopened-final-20261120.png).

## Historical evidence remains historical

The [genuine execution report](SETTING_INTERPRETATION_EXECUTION_2026-11-20.md) and its exact [case-5 response/evidence](verification/setting-interpretation-executed-20261120.json) are unchanged. Genuine cases 1–4 passed. Case 1 also passed browser review → Apply/save → Solutions → reopen. Case 5 remains **FAIL_STOP**: the model guessed Generator North although North and South were eligible. Its saved design was unchanged and its proposal was never applied. Cases 6–10 remain **NOT_ATTEMPTED**. This repair does not retrospectively upgrade those results.

The genuine evaluation remains CLOSED: five attempts, conservative accounted cost USD 0.035761275, zero uncertain reservations, zero remaining authorised requests or dollars. This pass made **zero metered calls**, read no paid API key and created/activated no spending scope. Provider prompt and spending implementation Git blobs are identical to the execution checkpoint. The model response schema is unchanged; the new choice is authenticated application-request input, not model output.

The earlier [scripted setting edit demonstration](DAILY_DELIVERY_2026-11-20_TRUSTWORTHY_SETTING_EDIT.md) remains available on 23135; the genuine case-1 demonstration remains on 23136. The 23124 demo, 23125 review workspace and 23134 historical workspace also responded after this work. No retained process or container was stopped. Forty-nine original database, evidence and ledger files checked at the start/end of the repair were byte-identical. The original checkout remained on `feature/design-with-ai-pilot`, SHA `12aae82dd47b078ba077aca40b0712c375b9d7f3`, with its 150 dirty entries preserved.

## Existing mechanisms inspected and reused

Builder already records an explicit selected instance when the designer clicks a processing step or canvas node; pane/edge selection clears it. Its settings inspector uses that same selection. The saved-solution conversation already stores a pending clarification alongside its messages and pending review, preserves it through explanation turns, and clears it when a proposal resolves it.

The correction passes Builder's existing selected instance to the assistant. When no explicit selection resolves an ambiguous setting edit, the application uses the existing clarification state to display a focused choice among the eligible current instances. No second editable workflow, selection database or general evaluation framework was introduced.

## Application-enforced boundary

* The server offers scoped target references for the current owned solution and its validated preferred pending candidate, or saved graph when there is no pending review. A stale pending candidate never falls back silently to the saved graph.
* Each user choice includes solution identity, exact saved/pending base and conversation revision, full workflow hash and catalogue authority hash. It must identify one currently offered instance. The application checks it before dispatch and again after the response. Stale, foreign or conflicting choices return 409 without changing saved or pending work; stale pre-dispatch choices make no provider request.
* Eligible alternatives come from the currently published setting names. A valid model target reference establishes eligibility only. If several existing instances advertise the requested names, model prose, a guessed reference or a claim of prior user confirmation cannot establish user choice. This deliberately conservative policy can also ask for a click when prose names an instance; it does not add phrase-matching heuristics.
* Before any pending replacement, the normal candidate editor validates the action. An unresolved multi-instance setting action becomes an application-authored choice question. The entire candidate containing that guess is withheld, including mixed legacy edits. Saved content and the exact earlier pending proposal are retained.
* Clicking a displayed choice re-sends the original request with that explicit current choice. The model receives a separate application fact identifying it. The new action must target the chosen instance. The application does not silently retarget the old guessed action. A model response cannot include the request-only `target_choice` field; schema validation rejects it.
* A single eligible instance requires no extra choice. Parameter types/limits, factual before/after summaries, review, explicit Apply/save, ownership, canonical writer and separate explicit Run remain the existing path.

Choice validity includes all workflow content and catalogue authority, not just visible labels. Explanatory turns preserve the question but advance the request revision; old payloads still fail. Changed workflow questions hide their old choices. No node/service identifier, registered workflow exception or exact user phrase is used in the production guard.

## Offline checks and actual browser observation

Focused API checks: **35 passed**, including the new 15 target-choice cases and existing 20 trustworthy-setting cases. Compatibility checks: **66 passed**. Actual assistant component checks: **8 passed**. Next.js 16.3.8 build and type check passed using existing dependencies. No tests were skipped. These are application/component checks, not genuine interpretation or runtime execution acceptance.

The focused cases cover: no selection with two similar instances; preservation of an earlier pending rename; South-only edit and exact Apply/reopen content; explicit Builder selection without an extra clarification round trip; stale saved version, conversation, pending proposal and contract authority; foreign references/solutions; conflicting model targeting; attempted model-created confirmation; single-instance numerical and boolean actions; captured case-5 action replay; and clarification surviving explanation while rejecting workflow drift.

The test response for the captured failure preserves its operation, value and response structure, rebinding only identity/base to the isolated fixture. The original recorded response hash remains `84f50cc63893166b19ca4ea960017fbd5b70ac77cab370a8315e3b4b391f1e48`.

In the actual browser, a normal independent designer signed in at 23137 and opened the two-instance fixture through Solutions → Edit in Builder. No step was selected. Before the walkthrough, only this fresh copied fixture was restored to the pre-failure conversation and given a clearly labelled earlier pending title review. The original failed case database/evidence were read-only sources and were never changed.

1. The designer submitted the original ambiguous request. The **explicit offline response replay** supplied the captured guessed North action with only current identity/base binding. The application displayed North/South choice buttons. The saved content, prior pending ID and prior candidate hash were unchanged; both maxima stayed 4.
2. The designer clicked **Use Generator South**. A second clearly scripted response used that authenticated selection. The review showed South 4 → 2, North 4, both boolean settings true, the original connection and selected input, and the earlier pending title. The earlier work was included in the revised proposal.
3. The designer clicked **Apply and save reviewed changes**, went to **Solutions**, and reopened the same solution, `5270b6f1-62c5-4c02-a590-dfcab2e14698`, in Builder. South's inspector showed 2; North's showed 4. Both boolean controls remained checked. No pending review remained. The entire saved content exactly matched the reviewed candidate hash:

   `ba3badd18e35440a52598c816632a7534877435719295abe8cfbb76f7392e374`

There were exactly two offline response supplies and zero execution submissions. These are observed browser/application results with labelled doubles, **not genuine-model proof**. No direct chat/Apply API calls replaced the browser journey. Read-only database inspection verified the resulting exact content and preserved fields.

Initial offline development runs exposed test-fixture assumptions about implicit target choice; those fixtures now declare an explicit fixture-user selection. A component assertion initially omitted HTML markup and was corrected. The first harness preparation used the wrong nested offline profile and stopped before starting anything; a fresh directory was used for the successful preparation. An evidence comparison initially compared checkout CRLF bytes with Git LF bytes; normalised Git blob checks confirmed unchanged provider/spending source. These tooling corrections made no metered call and changed no retained workspace.

## Working local demonstration

* New OFFLINE UI: <http://127.0.0.1:23137/builder?solutionId=5270b6f1-62c5-4c02-a590-dfcab2e14698>.
* New loopback API health: <http://127.0.0.1:28271/health>.
* Preserved genuine case-1 UI: <http://127.0.0.1:23136/builder?solutionId=fae22335-cfd3-4fc4-bbc6-941bbd45dec3>.
* Preserved earlier OFFLINE UI: <http://127.0.0.1:23135/login>.

23137/28271 serve isolated source copies of `7c3f4b752e520cb4e504316118e7a4dcaa396a2f` through the existing host Node/Python dependencies. There is no new image, worker, ML runtime or Docker stack. The new database and cookie are distinct. The opt-in `deploy/setting_edit_walkthrough/target_choice.py` harness clears paid-provider configuration, supplies only documented offline responses and blocks execution routes; production does not import it. Operator details, credentials and diagnostics remain in ignored private local files. The source copies, original demos, data/model/state/evidence volumes and spending scopes were preserved.

## Smallest subsequent genuine retest

The first meaningful genuine check is two calls in one conversation: the original ambiguous request must reach an application choice without replacing earlier work, followed by an actual click on South and a new model action that targets only South. Record whether the model itself clarifies or still guesses; successful application containment does not turn a model guess into successful interpretation. For a correct reviewed action, repeat review → Apply/save → Solutions → reopen.

The smallest complete continuation covering the failed case and every previously unattempted behaviour is **six genuine calls**: case 5 ambiguity, case 6 clarification follow-up with explicit South choice, case 7 already-satisfied value, case 8 unsupported/invalid setting, case 9 original-request repeat and case 10 paraphrase repeat. Freeze those inputs/expected results before any later execution, isolate unrelated cases and preserve the same stop-on-failure/accounting rules. The existing scope remains closed; no new execution authority is requested or assumed in this offline repair.

The remaining product question is whether the genuine model follows an explicit current target choice reliably and handles no-op/invalid/follow-up requests honestly. Scientific owner/runtime approval, new node onboarding, workflow creation and execution are outside this focused correction.
