# Genuine setting interpretation — stopped at ambiguity — 20 November 2026

**Four reviewed genuine interpretation cases passed; case5 failed; evaluation CLOSED.** Cases6–10 are NOT_ATTEMPTED. The successful first edit was demonstrated in the local browser through review → Apply and save → Solutions → reopen the same solution. This is genuine model interpretation followed by browser persistence evidence for that small edit, not a completed or generally reliable conversation journey.

Approved checkpoint **`ab94246c58015a340709e31f8f8bc79f512cc55f`**, branch `codex/setting-interpretation-eval-20261120`; evaluator implementation **`af7f1341d60d866fa6a9202987197423f82a30d0`**. Model, prompt, exact SDK wire schema, cases, expected values and frozen source were unchanged during all five requests. Later commits add execution evidence only. [Full sanitised attempt/accounting record](verification/setting-interpretation-executed-20261120.json) · [frozen preparation](SETTING_INTERPRETATION_ACCEPTANCE_2026-11-20.md).

## Authority and initial inspection

The user's subsequent message explicitly authorised execution of the existing frozen ten-case set and conditional browser proof: maximum10 attempts, USD0.6765 total, no retry/fallback/replacement scope, no workflow Run/production action, stop at first failure. Inspection found **zero previous attempts, case ledgers or provider audits**, and the frozen manifest matched `279cb8a6194279b4c3300d9bf19b521b4a7bc07f24ece29b90da206d84561005`. The existing project-local ignored credential was verified privately; no key value was printed or committed. Pricing was rechecked against [official OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and remained USD0.75/4.50 per million input/output tokens.

The approved parent scope was activated once at22:25UTC with expiry21November01:25UTC. Every dispatched case used its own existing frozen database/owned solution and a newly created **one-request** provider ledger under this parent. These case ledgers are the approved ten-case design, not replacement scopes after failure. All four earlier historical spending scopes remained closed and byte-identical.

Fixed configuration: `gpt-5.4-mini-2026-03-17`, reasoning `none`, Standard/default tier, Responses, `store=false`, no tools, timeout60s, `max_retries=0`, no fallback;64,000 input/3,000 output ceiling. All five responses returned the exact snapshot/default tier and completed strict SDK parsing. Configuration digest was identical across attempts: `5d1f2e65cb16d2c651e75c69345c51b615263d495dc460a66ab97e996a6ea0e5`.

Prompt SHA-256: `3e5c65e3dc25e7d7149fe0cc5e4e55a9dc4bed9e53069af4a2fec1b52d7291d8`. Exact wire-schema SHA-256: `be5c2f476b825e4ddf105d654f17f65b49b70a442354a7d1ad6eb62bdd09ba93`.

## Every case and verdict

| Case | Result | Observed interpretation / reason |
| --- | --- | --- |
| 1 Original pending4→2 | PASS after review | Exact pending North target/base; maximum2 with explicitly preserved true flags; complete candidate hash and factual application diff matched; saved graph unchanged before Apply. |
| 2 Paraphrase | PASS after review | Pending North maximum2 only; earlier pending title, flags, drawing, connections and input preserved. |
| 3 Saved-setting edit | PASS after review | Saved North maximum2 only; complete expected graph matched; truthful proposed summary. |
| 4 Boolean change | PASS after review | North bypasses false as a boolean; maximum4 and heat exchangers true preserved. |
| 5 Ambiguous target | **FAIL_STOP** | Asked to set “the generator” to2 with North and South both eligible. Model guessed North rather than asking which instance. A valid but unwanted proposal was stored; it was not applied. |
| 6 Clarification follow-up | NOT_ATTEMPTED | Stopped at5. |
| 7 Already-satisfied value | NOT_ATTEMPTED | Stopped at5. |
| 8 Unsupported/invalid setting | NOT_ATTEMPTED | Stopped at5. |
| 9 Repeat original | NOT_ATTEMPTED | Stopped at5. |
| 10 Repeat paraphrase | NOT_ATTEMPTED | Stopped at5. |

Cases1–4 initially returned `REVIEW_REQUIRED`, not PASS. Their actual structured responses, proposed diffs, complete expected-candidate hashes and preserved saved content were inspected before concrete semantic review was recorded and the next case dispatched. No repeated, repaired or discarded model response exists. The full record includes every attempt, exact visible/validated response, usage, request/response identifiers, request/configuration/schema hashes, application observations and each review reason.

Case5 request: “Set the generator's maximum candidate layouts to two. Keep the other settings unchanged.” Both instances had maximum4, heat exchangers true and bypasses true. The model returned `setting_edit` on the scoped North reference with `how_many=2`, `message=null`, `clarification=null`. The application correctly described that candidate as proposed North4→2; South stayed4. The failure is **target interpretation**, not parsing, provider transport or a factual-summary defect. Existing application validation confirms ownership, current references, permitted values and candidate integrity; it did not establish that the model had resolved this ambiguous natural-language target. Saved North and South remained4. There was no false applied/saved claim and no lost saved work.

The evaluator stopped immediately at5 and closed the parent. No case6 request, repair request, retry, fallback, prompt/schema change or replacement allowance was made. The failed review remains available as unapplied evidence. No failed result was reclassified as PASS.

## Spending after each attempt

All numbers below are USD. Conservative accounting uses the existing10% margin and assumes no cache discount. Actual usage reported zero cached/cache-write/reasoning tokens. List-price estimate is separately reported and is not an independently reconciled invoice.

| After case | Input / output tokens | Case conservative cost | Cumulative conservative cost | Lifetime reservations | Remaining unused reservations | Authorised future attempts |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 8,712 / 200 | 0.008177400 | 0.008177400 | 0.06765 | 0.60885 | 9 |
| 2 | 8,683 / 178 | 0.008044575 | 0.016221975 | 0.13530 | 0.54120 | 8 |
| 3 | 6,622 / 125 | 0.006081900 | 0.022303875 | 0.20295 | 0.47355 | 7 |
| 4 | 6,625 / 125 | 0.006084375 | 0.028388250 | 0.27060 | 0.40590 | 6 |
| 5 | 8,181 / 126 | 0.007373025 | **0.035761275** | **0.33825** | 0.33825, CLOSED | **0** |

Totals: **38,823 input +754 output =39,577 tokens**, five requests, base list-price estimate **USD0.03251025**, conservative accounted **USD0.035761275**. Every request settled; **zero uncertain/unsettled reservations**. All five one-case ledgers and the parent are CLOSED. Five unused requests/USD0.33825 unused lifetime-reservation capacity confer **no remaining authority**. No reservations were reset, refunded for reuse or reopened.

## Actual genuine browser proof

Case1's same owned database was exposed for review only, with no key, additional model requests or workflow execution enabled. UI **http://127.0.0.1:23136**, API **http://127.0.0.1:28270/health**. Serving source identity remains **`ab94246c58015a340709e31f8f8bc79f512cc55f`**. This is a host Python API plus the existing Node/Next dependencies; no new container image or model/runtime stack was installed.

The frozen review starter initially hit **WinError267, directory name invalid**: its confirmed existing frontend cwd was262characters long and an independent no-op cwd probe failed identically. No READY or working UI claim preceded that failure. The reversible operator fix built the same unchanged frontend with the same helper in a shorter fresh ignored directory, using the exact same frozen API, case1 database, cookie, ports and review/execution guards. It did not modify frozen source, spending state or invoke a model. Source verification still passed, the build completed, starter READY was observed, and actual browser/login/API health returned200. Both the failed startup diagnostics and final serving details remain private and retained.

Observed normal browser journey:

1. Sign in as the ordinary isolated fixture designer; open case1 through **Solutions → Edit in Builder**.
2. Review the actual genuine-derived proposal: North maximum4→2, heat exchangers/bypasses true, Drawing A/connection and earlier pending title retained. Chat says proposed; Apply remains explicit.
3. Click **Apply and save reviewed changes**. The server confirms applied and saved; no additional Save appears for the clean saved design. Run remains separate and disabled by this review environment.
4. Leave through **Solutions**, then reopen **the same solution**. Inspector shows maximum2, both flags enabled, same title, Drawing A and connection. No model request was sent from this browser proof.

Current example: [open the genuinely edited solution](http://127.0.0.1:23136/builder?solutionId=fae22335-cfd3-4fc4-bbc6-941bbd45dec3). Whole persisted graph SHA-256 after Apply and after reopening is **`22e0595bf6f0612714ab25862324d4b5dc71626f5de53041dd5f44640d8dd4c7`**, exactly the candidate hash fixed before the model ran. Complete stored graphs and owned API solution responses are equal across Apply/reopen. Selected **fixture** input metadata remains preserved; it is not executed data qualification. Submission count remains0.

[Actual proposal screenshot](verification/genuine-setting-review-20261120.png) · [Reopened saved inspector and fitted workflow screenshot](verification/genuine-setting-reopened-fit-20261120.png) · [Initial reopened viewport](verification/genuine-setting-reopened-20261120.png).

## Preserved state and next specific problem

The retained23135 offline demonstration database and all four old closed spending ledgers are byte-identical to their pre-execution hashes. Retained23124,23125,23134,23135 and the new23136 endpoints return200. The original checkout remains `12aae82dd47b078ba077aca40b0712c375b9d7f3` with150 dirty entries. The old J2 negative response fixture remains SHA-256 `174512a02f45808eb4f54cb53117058af88ae3c4959b89901d0b006c543979a8`. Original branches, historical designs/results, old WP3/model/state/evidence volumes and closed scopes were not changed. No Docker/runtime/node integration, production deployment or workflow Run occurred.

Private operator paths, credentials, approval file, database copies, raw diagnostics and ledgers remain ignored. The published record contains sanitised execution output and screenshots. The failed Windows startup is recorded separately from the genuine interpretation failure and was resolved before continuing case2. The frozen model evaluation itself had no infrastructure, parsing or application-validation failure.

Next specific problem: **make an underspecified target produce clarification before any setting proposal when two similar instances exist**. Preserve this actual case5 output as the regression evidence, implement/test the correction offline in a later development increment, and obtain separate authority for any subsequent genuine acceptance. This CLOSED scope and its five unused cases must not be resumed. No broader creation/integration/execution journey is justified by these four successes.
