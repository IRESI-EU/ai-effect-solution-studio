# Portuguese genuine-provider acceptance preparation

<!-- CURRENT-STATUS-START -->
**Prepared; blocked on local accounting transport and new session authorization.**
Offline context/proposal/accounting checks PASS. Genuine-provider interpretation
is **UNTESTED**. This preparation made zero provider/algorithm calls, no spending
activation, no new live drafts/designs and no runtime/configuration change.
Historical allowance remains **25/25**, USD0.10 ceiling, USD0.010603500 held/accounted,
USD0.089396500 conservative remainder, zero outstanding reservations.
<!-- CURRENT-STATUS-END -->

Starting clean/remote-verified reviews: Portal
`cafca7d35eb3b3c957e5763ddf2dfaa9e4d5bd12`, maintained WP3
`6107d4ba02ddbdca500750b349b7af2c41920bda`. The new host-side operator/case source
is `5f87c4c` (full identity in the machine proposal). No application feature,
web asset, original ML code/image or adapter changed, so no new API/web package
or repetition of completed Builder/algorithm acceptance was needed.

## Frozen session and cases

- [Exact session proposal](../deploy/portuguese_sandbox/proposed-provider-acceptance-20261116.json).
- [Prompts, initial states and structured criteria](../deploy/portuguese_sandbox/provider-acceptance-cases-20261116.json).
- [Read-only preflight and test evidence](../deploy/portuguese_sandbox/provider-preparation-verification-20261116.json).

Hashes use UTF-8 compact sorted-key JSON, no newline, `ensure_ascii=false` and
`allow_nan=false`, so Windows newline conversion does not change identity:

| Item | SHA-256 |
| --- | --- |
| Proposal | `ba38c26b4987518abd524e4e187c20b90df56b76e2c0c6be4771ef60b0a0726b` |
| Cases | `267eee3f1f8108494c804ac7ab34c6984b173eb5b1228eef519f20371e1f6a36` |
| Relevant configuration | `dfc1da6e9abfc31954adf7e97d84a2a429ac7a1a7b7e8772246ed2c671ecbc58` |

| Case | Exact prompt | Calls | Frozen judgment |
| --- | --- | --- | --- |
| A | Recommend a workflow that trains a Portuguese synthetic-data model and then generates data using that same model. Explain the required training CSV selection and the declared default settings. Do not execute anything. | 1 | Only the authorized registered chain; explains explicit CSV selection and defaults 1/4/10; no execution claim/authority. Recommendation alone creates nothing. |
| B | Set training to 2 epochs with batch size 4, and generate 20 sequences using that model. Keep the selected training CSV and the existing model connection. Do not execute anything. | 1 | Canonical instance proposal for 2/4/20; CSV and model_ref retained. Explicit Apply → Save → refresh → Builder → Validate; independent IDs/pins persist; zero results/deployments. |
| C | Change the size to 2. | 1 | Separate fresh default draft, no CSV. Ask which declared size/setting is intended; no edits or arbitrary choice. Application separately exposes missing CSV; unchanged revision/design/pending state. Do not answer. |

Maximum **three provider attempts total**, no follow-ups, no retries/fallback.
Stop the session on the first failed/uncertain case. Do not change the rubric,
manually repair a response, fabricate history or report a deterministic response
as a genuine-provider pass. Prose need not match a script. For C, a model that
merely asks for CSV without clarifying size fails interpretation even if backend
guards prevent mutation. Epochs, batch size and sequence count all accept 2.

A starts in a new visible conversation. After a valid recommendation, explicit
Create allocates the fresh B draft; record its UUIDs. Select **Sandbox test dataset**
through visible controls, Review configuration changes and Apply that input-only
proposal at revision0. B starts at revision1, defaults1/4/10, selected CSV, no
pending proposal. Normal UI carries the real A conversation into B: do not erase
it or replace it with an invented history. Input-only controls require no model
call and add no fabricated assistant interpretation. Before B dispatch, include
that actual history in the 32,000-token conservative framed input bound; stop
before reserve if it does not fit. C uses a separate new visible conversation
and approved-workflow card, creating another fresh draft at revision0. Do not
reuse the accepted draft91a37168 or Builder07c9449a. No helper/API writes may
prepopulate the acceptance state. Only B is saved; C's clarification stays open.

## Model, prices and accounting

Verified 16 November from the [official model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [official pricing](https://developers.openai.com/api/docs/pricing): exact request
identifier **gpt-6-luna**, Responses API, supported low reasoning and structured
output. Standard processing is API `service_tier=default`. Current short-context
prices per million tokens: input USD0.10, cached reads0.01, 30-minute writes0.125,
12-hour writes0.25, output0.50. This proposal explicitly pins 30-minute writes;
12-hour caching and regional/Fast/Batch endpoints are prohibited. Recheck before
activation; different pricing requires a revised proposal. Model entitlement and
key validity cannot be established from local key presence; they remain untested.
No metered connectivity probe or model-list request was made.

Per call: framed input <=32,000, output <=2,000 **including reasoning**, timeout40s,
store=false, no hosted tools, zero SDK retries. Total <=96,000 input /6,000 output.
All input conservatively costs125 USD nanos/token, all output500 nanos/token;
cache discounts are unnecessary. Reasoning included in output is not charged a
second time. Each durable reservation is USD0.005; lifetime reservations and spend
for the whole session <=**USD0.015**, inside the original USD0.10 global ceiling.
Actual usage, cached read/write counters, reasoning, returned model ID/tier,
response ID and conservative versus billing-estimated cost must be recorded.

The earlier acceptance/beta spending authorizations are exhausted; they do not
authorize this additional Portuguese scope. The narrow new host-operator phase
`portuguese_acceptance` proposes **25→28** calls on the **same canonical authority**,
new scope `pt-provider-acceptance-20261116`, 0/3. There is no second ledger,
historical reset, checkpoint reopening or added money. It requires the frozen
proposal hash, original ledger file/fingerprint/audit, fully settled prior beta,
one exact PostgreSQL/reviewer environment and a new private binding credential.
It cannot reopen a globally stopped policy. The real supported operator dry-run
passed with the ledger byte-identical; **apply was not run**.

Use the existing [accounting runbook](../deploy/restricted-beta/ACCOUNTING.md).
Prepare-only private artifacts are under the original checkout:
`local-backups/pt-provider-preparation-20261116/`:
`operator-request.private.json`, `operator-dry-run.private.json`,
`authority-token.private.json`, `authority-ca.pem`, `authority-key.private.pem`.
The request authorization reference explicitly remains PENDING. A later approval
must be recorded attributably before supported `--apply`; dry-run cannot spend.
Do not publish these private records. The native authority must use the reviewed
new source; no injection into the application container is needed.

Reserve → single fresh dispatch → settle numeric real usage before parsing →
verify receipt → acknowledge. Crash, timeout, cancellation or uncertain transport
stops the session; the full unresolved hold remains and blocks all further calls.
Lookup/reconcile the same permit from genuine usage, never repeat the provider.
An uncertain response is a failure/partial result even if a later receipt settles.
Disconnect the key after the session, reconcile terminal accounting and stop the
new scope through the supported attributable operator. Unused permits close;
none are refunded/reallocated. Stop the native authority and restore API
inspection-only networking/configuration. Execution remains disabled throughout.

## Actual local blocker and proposed configuration delta

The retained API is attached only to `ai-effect-pt-parameters_private`, confirmed
`internal=true`. A single bounded verified-TLS nonce probe from that API to a
temporary Windows **127.0.0.1:29489** listener failed with
`socket.gaierror [Errno -3] Temporary failure in name resolution` for
`host.docker.internal`. No ledger was opened by the probe. The temporary listener
was shut down. No firewall, hosts file, network or container was changed.

The old acceptance certificate had expired. A separate private certificate is
prepared (public CA hash/expiry recorded in the proposal), without installing OS
trust or replacing historical files. It expires **18 November 2026 21:42:28 UTC**;
an expired or changed certificate is a stop condition requiring updated review.
The retained provider key exists privately, was not printed/copied into serving
configuration, and was not authenticated. Its account/model access is unverified.

Proposed later delta, subject to explicit session approval: attach **only API** to
a second bridge `ai-effect-pt-parameters_provider-egress`, `internal=false`, while
retaining its existing private network. Keep web, databases, Redis, adapter, ML,
orchestrator and workers on their existing networks. Add no published port or
LAN listener. Mount only this session's **public** CA into API read-only at
`/run/pt-accounting/authority-ca.pem`; keep the private TLS key on Windows. Reuse
the current API image with no build/pull, retaining IDs/data/mounts for every
other component. Rollback restores the recorded private compose and removes
only this additional API attachment/CA/session settings after closure.

Set `DESIGN_AI_BUDGET_AUTHORITY_URL=https://host.docker.internal:29489`,
`DESIGN_AI_BUDGET_AUTHORITY_CA_FILE=/run/pt-accounting/authority-ca.pem`,
`DESIGN_AI_BUDGET_AUTHORITY_ID=original-shared-local-20261112`,
`DESIGN_AI_BUDGET_SCOPE=pt-provider-acceptance-20261116`,
`DESIGN_AI_BUDGET_CONSUMER=pt-registered-design-review`,
`DESIGN_AI_BUDGET_ENVIRONMENT=portuguese-sandbox-local`. Token comes from the new
private record; legacy local budget/task files and authority socket stay empty.
Keep restricted beta enabled and reviewer IDs exactly
`5cc4b476-b97d-41b0-8d75-e381b3dbe581`.
Set model/reasoning/output to the frozen values above. Keep the provider key empty
until the non-provider hostname/TLS probe passes, the audited operator dry-run
passes, the separately approved amendment is applied and authenticated status
reports global25/28, scope0/3, zero outstanding. Never disable TLS, widen the
listener, substitute a database identity or spend while transport is unresolved.

This change is **proposed, not applied**. It is a concrete local deployment
prerequisite, not a new service profile or permission to run algorithms.

## Offline results and preservation

The normal authorized read-only MCP discovery exposes the exact candidate and
all declared defaults/settings. The focused MCP context exposes the instances,
schemas, IDs and `training_input.selected`; no CSV bytes, file path, runtime
endpoint, token or key is included. Genuine provider code always uses
`https://api.openai.com/v1`, strict AssistantTurn parsing and canonical proposal
validation. Source inspection and three new deterministic tests cover A selection,
B actual revision/instance edits and invalid-setting rejection, and C's unchanged
state/missing-input enforcement. A test double clarifying ambiguity is **not**
evidence that a real model will do so.

Actual discovery framed bound was30,558 tokens (conservative UTF-8-byte estimate,
system/schema/framing included). Focused default-state bases were23,606 and23,450;
B's eventual A history is additional and must be measured before dispatch. UUIDs
are allocated only in the later UI session; representative focused hashes are
not claimed as exact future request hashes. The authority independently rejects
input above32,000 before a provider client is constructed.

Focused run: **75 passed** across provider preparation, allocation, existing
shared-authority and protocol tests. Final ten changed cases rerun **10 passed**
after aligning B's carried history and improving typed test data; these overlap
the75. Initial local runs failed on Python import/fixture/temp-directory setup;
corrected targeted runs passed, with existing dependency deprecation warnings.
No complete suite, frontend build, PostgreSQL concurrency or algorithm inventory
was repeated. No new PostgreSQL concurrency or scientific-quality claim.

Read-only inspection preserved11 saved solutions, the accepted AI draft, nine
completed journal jobs, four closed execution scopes, unchanged Redis state and
historical wf-717110fb8d5e available/completed. Execution workers remain stopped,
API/adapter supervision OFF, provider disconnected and exhausted ledger byte-identical:
`cf9fa12e87633b9e260d3983a3dd9e5c51df346c04237b3babd255ee66cd7d2b`.
No worker, scope, workflow or replacement design was created in preparation.

| Serving component | Source commit | Image |
| --- | --- | --- |
| API | `25dda8b1e9bfda78790dbe27e1b1ab38e7556c2b` | `sha256:802fb23b14152d5043659b8e7c254926c87b5c26cbeade1cdced7acb3440ea6e` |
| Web | `4296ec484542ce9dfa4d1b45e3ce9a897793edc3` | `sha256:a7ca1100fb5364ca876117a176b351f411bb330f5baa8dfe6a4f09de49d635ed` |
| Adapter | `c98b454b1a9ce9b9a154ad82ef104678ba78b443` | `sha256:7709b05cb41329a2ef55a05816c82e2d9371cdde131ee92e2c0a31fc8247a8c6` |

Registration `pt-reviewer-chain-v2-20261116`; candidate
`workflow-ac621480df1df1b05633230f`; recommendation revision
`3494d028405b95bb938e6eb9297bcf559f01426fc4fc84003f43f9f81c2ec8a0`.
Source design digest `0ed2580e2174c62e1241a20fc781af2d471c028950cc35277448955dc0ee7281`.
Both pins remain0.2.0; dataset hash, contract definition hashes, original ML image
and exact PostgreSQL scope fingerprint are recorded in the proposal. Historical
catalogue image and current compatible adapter mapping remain distinct; neither
was rewritten. This remains platform-controlled local sidecar work, without
Portuguese-owner hosted qualification, production availability or independent
human usability evidence.

Local entry: http://127.0.0.1:23124/design-ai. Use the existing reviewer sign-in;
credentials remain privately in the original checkout at
`local-backups/portuguese-sandbox-20261112/profile/credentials.json`.
The completed results remain http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results.

## One proposed later approval

Authorize this exact frozen proposal, canonical SHA-256
`ba38c26b4987518abd524e4e187c20b90df56b76e2c0c6be4771ef60b0a0726b`:
the API-only network/CA setup above and one supervised30-minute **design-only**
session, supported original-ledger25→28 amendment and new0/3 scope,
gpt-6-luna/low/Standard, <=32,000 input and2,000 output per attempt,
<=USD0.015 aggregate, zero retries/fallback/follow-ups. All transport, accounting,
source/catalogue/ownership and execution-denial preflights must pass before
connecting the provider or spending; stop on drift/failure/uncertainty and preserve
the outcome. No algorithm, execution authority or provider call is authorized by
this preparation document itself.
