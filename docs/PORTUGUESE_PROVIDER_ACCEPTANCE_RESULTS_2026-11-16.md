# Portuguese genuine-provider acceptance results

<!-- CURRENT-STATUS-START -->
**PARTIAL overall: all three frozen behavioral cases PASS; wire evidence incomplete.**
Exactly three genuine calls, no retries/follow-ups/fallback. New scope closed,
provider disconnected, native authority stopped, original internal-only API
networking/configuration restored. Execution stayed disabled; no algorithms,
workflows or execution scopes were created. This is agent-operated acceptance,
not independent usability or Portuguese-hosted/production qualification.
<!-- CURRENT-STATUS-END -->

The owner approved Portal `32f7820e08aa6c0ca7a68bfca121dbdfa4b8a4d6` and
[the frozen proposal](../deploy/portuguese_sandbox/proposed-provider-acceptance-20261116.json),
canonical SHA-256 `ba38c26b4987518abd524e4e187c20b90df56b76e2c0c6be4771ef60b0a0726b`.
The proposal, cases and previous preparation evidence are unchanged. Actual
responses, structured B proposal, real usage, response IDs, hashes and closure
checks are in [sanitized verification](../deploy/portuguese_sandbox/provider-acceptance-results-20261116.json).

## Genuine cases, unchanged rubric

| Case | Outcome | Actual observation |
| --- | --- | --- |
| A recommendation | PASS, one call | Recommended only the registered Portuguese chain, explained separate Sandbox test dataset selection and defaults1/4/10, same-model generation and no execution availability. Recommendation itself created nothing. Explicit Create then allocated the fresh B draft. |
| B configuration and persistence | PASS, one call | At revision1 after explicit CSV-only Apply, genuine proposal changed epochs1→2 and sequences10→20, preserving batch4, CSV and model_ref. Explicit Apply → Save → refresh → Advanced Builder → Validate showed Checked successfully. Independent IDs, dataset, settings, both0.2.0 pins and connection survived. No deployments/results. |
| C ambiguity and missing input | PASS, one call | Separate fresh revision0 draft, defaults1/4/10, no CSV or history. Model asked which size meant, proposed no edit. Full server draft was identical before/after. Missing-CSV instruction stayed visible. No reply, Apply, Save or CSV selection. |

Exact C response as rendered:

> “Size” could mean the number of generated sequences or the training batch size. Which one should I change?

The model's clarification is distinct from the application's retained instruction:
**Select a training CSV before validating.** Both were observed independently.
No response was manually repaired and no expected outcome changed after viewing it.

B's stored structured AssistantTurn retains its genuine message and two exact
instance parameter edits. The existing parameter compiler/review/authorization
routes remained authoritative. CSV selection was an explicit input-only controls
proposal before B, not a model-invented dataset or an additional provider turn.
The actual A conversation was carried by the normal UI into B.

New saved design:
http://127.0.0.1:23124/builder?solutionId=28f62cd4-27c4-4e8d-a933-489e66530389

New AI draft:
http://127.0.0.1:23124/design-ai?draftId=ba0370ca-381a-4cf2-a9bc-6a4724ac5eb0

Unanswered C draft (unsaved):
http://127.0.0.1:23124/design-ai?draftId=b2e9a2b4-95f7-4a79-9a55-b27679ed99d3

B's TrainModel instance is `b8a39153-8c21-421f-ade8-668c33797af8`, GenerateData
`7bb2fb0b-3685-4bd0-a4eb-a735528f86ea`. Both are independent of every prior saved
design. Pins remain `pt-chain-train-v2`/`pt-chain-generate-v2`, version0.2.0;
`model_ref`→`model_ref`, whole-output-v1, matching published model-reference schema.
The opaque approved CSV reference remains `pt-approved-synthetic-data`.

## Metering and limits

The genuine path used the retained OpenAI Responses provider, requested
`gpt-6-luna`, low reasoning, `service_tier=default` (Standard), explicit30-minute
cache TTL, output<=2,000 including reasoning, zero retries/fallback. Before
activation, [official pricing](https://developers.openai.com/api/docs/pricing)
and [model controls](https://developers.openai.com/api/docs/models/gpt-6-luna)
matched the frozen proposal. No metered connectivity test occurred.

| Case / ledger row | Authoritative framed input bound | Actual input | Cached reads | 30m writes | Output (reasoning included) | Conservative ledger charge | Usage-priced estimate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A /26 | 30,558 | 4,941 | 0 | 4,938 | 331 (55 reasoning) | $0.000783125 | $0.000783050 |
| B /27 | 24,831 | 3,315 | 2,274 | 1,038 | 308 (82 reasoning) | $0.000568375 | $0.000306790 |
| C /28 | 23,450 | 3,060 | 2,274 | 783 | 200 (130 reasoning) | $0.000482500 | $0.000220915 |
| Total | | 11,316 | 4,548 | 6,759 | 839 (267 reasoning) | **$0.001834000** | **$0.001310755** |

All usage settled and acknowledged normally before interpretation/persistence.
Reasoning is included once in output. The ledger conservatively prices every
input token at the30m-write rate. The estimate uses genuine cached/write counters
and frozen rates; an invoice was not independently inspected. Nine input tokens
were ordinary uncached input. No12-hour writes or unknown usage occurred.

Every request's complete serialized context, including B's original carried
conversation, was measured in the genuine provider path before reservation;
the exact bounds above are retained in the authoritative ledger. The separate
read-only operator projection used rendered B history and measured24,808; Markdown
serialization explains its23-byte difference from the actual24,831. It is not
claimed as the wire-exact context hash. No live history was replaced or edited.

Lifetime reservations: **$0.015**, exactly3×$0.005, fully consumed as permits.
Global usage **28/28**, scope **3/3**, global ceiling unchanged**$0.10**;
global conservative accounted charge**$0.012437500**, remaining**$0.087562500**.
Outstanding reservations: **0**. After C, authenticated status denied further calls
with `call_limit`; no fourth reservation/provider request was attempted. The
supported attributable stop then permanently closed the new scope/global batch.
No unused money or calls were transferred to a replacement scope.

## Transport, timing and restoration

Preflight verified exact clean source, serving images, registration revision,
active contracts, dataset hash, reviewer, all prior designs, ledger/audit and
empty unresolved queues. The same frozen certificate remained valid through
18November21:42:28Z; it was not replaced. Only API received the documented additional
bridge and read-only public CA mount. All other services retained their identities,
images, mounts and state; existing private network stayed internal.

With provider empty, actual API DNS, verified TLS and nonce connectivity passed
against **127.0.0.1:29489**. No LAN listener, TLS bypass, host-route substitution or
published port was added. Attributable approval and supported operator dry-run
preceded the exact25→28 amendment on the original canonical ledger. Authenticated
status then showed global25/28, new scope0/3 and no unresolved reservation before
key connection. No parallel/copy ledger or old checkpoint was used.

Activation: **22:44:53.731591Z**. Scope stopped after**630.124 seconds**; native
authority exited gracefully at**22:55:24.461363Z**, inside the30-minute limit.
Provider disconnected before closure. Original compose bytes restored exactly;
API has only `ai-effect-pt-parameters_private`, still internal. Session network
and CA mount/settings removed; authority listener absent. Private certificate,
approval, before/after records and evidence remain retained locally.

All11 protected saved designs and the earlier accepted AI draft remain unchanged;
the sole new saved design brings the count to12. C remains a separate unsaved AI
draft. Nine completed journal jobs, four closed execution scopes, queues and all
56 containers/images/mounts remain. Only API was recreated for the documented
temporary settings; the other55 container identities are unchanged. All execution
workers remain stopped; API/adapter supervision OFF, grants absent. Historical
wf-717110fb8d5e remains Completed with available validated evidence.

The prior25 usage rows, prior audit prefix and historical accounting scopes
are unchanged. The real ledger retains three new settled records plus attributable
activation/stop audit events. Final ledger/audit hashes are in the verification.

## Evidence limitation and interpretation

**Overall PARTIAL is intentional.** All frozen behavior and accounting/closure
checks passed, but the full raw provider wire payload and returned model metadata
were not retained. A/C retain actual rendered message text and screenshots; B
also retains the application's SDK-validated structured AssistantTurn. Exact
requested model/settings, durable response IDs and real numeric usage are verified;
the response's returned model identifier cannot be independently reported. Do
not reconstruct it, describe rendered text as raw Markdown, or infer an invoice.
No additional provider request or replay was made to fill this audit gap.

This establishes genuine interpretation and canonical design persistence for
this approved local Portuguese registration. It does not establish algorithm
consumption for the new design, independent usability, Portuguese-node access,
partner approval, scientific suitability or production compatibility.
No feature implementation, build or repeated test suite was needed in this pass.

## Rendered evidence

- [A genuine recommendation](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-a-recommendation.jpg).
- [B genuine proposal](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-proposal.jpg),
  [saved/refreshed](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-saved-refreshed.jpg),
  [Builder validation](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-builder-validated.jpg).
- [Persisted training](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-training-persisted.jpg),
  [generation](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-generation-persisted.jpg),
  [model binding/pins](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-b-binding-pins.jpg).
- [C clarification and exhausted ceiling](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-c-clarification-paused.jpg),
  [retained clarification after disconnection](../deploy/portuguese_sandbox/evidence/provider-acceptance-20261116/case-c-closed-disconnected.jpg).
