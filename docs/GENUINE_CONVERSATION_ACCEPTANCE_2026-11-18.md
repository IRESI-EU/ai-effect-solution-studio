# Genuine conversation acceptance — concrete proposal, awaiting separate approval

Status update, 2026-11-19: the user separately authorised one bounded exercise.
Its first genuine response failed the count-clarification objective; the scope
was closed after one request. No further dispatch is authorised under that scope.
See [the actual FAIL checkpoint](GENUINE_SAVED_SOLUTION_ACCEPTANCE_2026-11-19.md).
The remaining text records the original pre-exercise proposal and its status at
preparation time; it is not renewed spending authority.

Updated 2026-11-19, Europe/Dublin. No paid request, active grant, provider key or successful language-model response is claimed. The running 23127 workspace uses an explicitly labelled scripted provider double. Previous spending scopes stay closed.

## Provider, model and price

Selected provider: OpenAI Responses API, pinned snapshot `gpt-5.4-mini-2026-03-17`, reasoning `none`, Standard/default tier, text-only Structured Outputs. This is the bounded conversational acceptance candidate; scientific model selection and algorithm qualification are separate. The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini) lists that snapshot, Structured Outputs, and reasoning `none`. Account access has not been checked with a provider request. An unavailable model must fail without substitution.

Current prices checked 2026-11-19 from the [official pricing page](https://developers.openai.com/api/docs/pricing): USD 0.75 per million input tokens, USD 4.50 per million output tokens; cached input is USD 0.075 per million, but the budget assumes no discount. The implementation adds 10% price headroom, including the documented regional-processing uplift. Recheck price before approval/dispatch; a higher applicable price requires review of these constants, not an unrecorded model/tier fallback.

| Enforced control | Proposed value |
| --- | --- |
| Maximum input per request | 64,000 tokens, enforced before dispatch by conservative UTF-8 byte bound over context, system and response schema plus 8,192 framing allowance |
| Maximum output per request | 3,000 tokens through `max_output_tokens`; reasoning none |
| Lifetime requests | 6, including refusals/failures/reservations; no automatic retry |
| Reservation per request | USD 0.06765 = 64,000 × 0.825/1M + 3,000 × 4.95/1M |
| Six maximum reservations | USD 0.40590 |
| Total hard application budget | USD 0.45, no automatic top-up/reopen |
| Scope/expiry | One new local acceptance database, one active designer, one new saved solution, at most 24 hours |

USD values describe provider API usage, not a currency conversion or tax-inclusive purchase. No purchase, billing-account change or paid installation is included. The guard is application-side: it cannot bind other clients using the account or guarantee a provider obeys its declared token/accounting contract. A provider usage/model/tier overrun closes acceptance immediately; no further request follows.

## Enforceable implementation, inactive until approval

`apps/api/app/services/scoped_ai_acceptance.py` implements a separate durable SQLite ledger, exclusive creation and transaction-locked reservations. It rejects a missing/copied/moved ledger, changed policy, different database/account/solution, expired/closed scope, unresolved request, seventh request or over-budget request. Lifetime reservations are never refunded into extra calls. Unknown usage, cancellation, parser/refusal failure or application-validation failure stops the fresh scope. Usage, provider response identifiers and operator approval reference remain private. Numeric accounting and safe hashes can be published.

The application never initializes this ledger. After separate concrete approval, an operator may call `initialize()` with an exact `binding(settings,user_id,solution_id)`, approval reference, new absolute file and expiry within 24 hours. Configure only that file as `DESIGN_AI_SCOPED_ACCEPTANCE_FILE`, the pinned model, reasoning `none` and output 3000 in the new acceptance process. Do not set an old shared allowance, legacy task/budget file, local-pilot or restricted-beta profile. Existing guards reject combinations. Prepare a fresh loopback execution workspace for genuine acceptance; preserve 23124–23127.

Use a dedicated provider key authorised for this future scope, injected privately only after approval; no old experiment key/grant is revived. No key is requested or installed now. SDK endpoint is fixed to the official API, `store=false`, default tier, no hosted tools, arbitrary fetching, silent fallback or retries. Data selections, CSV contents, credentials and runtime addresses stay outside the model envelope. Only approved catalogue descriptions/contracts, bounded history, current logical graph/settings and explicit user text are sent. Use synthetic text and reviewed SOFTWARE FIXTURE catalogue entries.

## Six genuine turns on one saved solution

1. Start a fresh goal: “I want to compare district-heating network layouts and see drawings.” Send explicitly. Expect actual accessible catalogue discovery and a useful clarification when the comparison count is missing.
2. Reply: “Two options, using the development fixture data.” Expect a connected generator/drawing proposal with published pins, defaults/overrides and workflow boundaries. No graph mutation until reviewed Apply and save.
3. Before applying: “Explain what will run before I apply.” Expect an explanation retaining the pending proposal. Then apply through the normal UI; the same canonical solution must reopen in Builder.
4. After selecting separate fixture data and saving in Builder: “Change the topology limit to three.” Review/apply only the intended instance settings.
5. “Add a second compatible drawing view.” Review the compatible catalogue choice, slots and fan-out connection. Apply to this same solution.
6. “Replace the Second view with the alternative drawing service.” Review that instance’s replacement, retained identity/connections and defaults. Apply.

Record each response as actually returned. A refusal, poor clarification, incompatible edit or unavailable model is failed acceptance, never replaced by a successful double. Stop on the first failed live step; do not spend remaining calls on undisclosed recovery. Close the scope after the exercise regardless of outcome.

Validate/preflight and explicitly Confirm deployment through Builder if running the fixture design. This reuses the normal compiler/owned evidence path; chat/apply cannot execute. Compare a two-layout and three-layout run, with immutable snapshots, consumed algorithm arguments and output/drawing hashes per workflow/task. Preserve prior Portuguese runs and the first result. Local enumerator/render execution is free source execution, not an LLM call.

Offline browser evidence and source/API/component tests establish software behaviour only. Genuine conversation acceptance, partner scientific/data approval, production operations and release approval remain separate and pending.
