# Bounded genuine conversation acceptance — prepared, not authorised

Current status: no paid call, no active provider credential/model, no new grant.
Offline tests exercise the shared saved-solution writer with explicit provider
doubles. The browser shows AI disconnected. Earlier spending scopes remain closed.

Proposed acceptance, requiring separate concrete approval of provider/model and
its current price: one new isolated grant, at most two model requests, at most
1,000 output tokens per request, no automatic retry, and a proposed total hard
ceiling of EUR 0.50. This is a proposed ceiling, not an estimate or permission to
spend. The selected model, price/token budget and enforceable worst-case reservation
must fit that ceiling before any call; otherwise stop without dispatch. No old grant
or credential is reused. No paid service purchase or installation is included.

Use only the existing development fixture designer and saved solution
`aef401a4-80f7-427e-8ebe-75a52a1d33cc`, its synthetic catalogue and current generic
execution path. The new grant must be bound to that account/workspace/scope and
record actual request IDs, usage and charges. Keep keys and operator accounting
details ignored/private. Publish only sanitised content/results and hashed evidence.

1. Genuine first message: “Explain what this saved solution does and which settings
   affect the number of generated rows. Do not change or run it.” Expect a truthful
   explanation grounded in the selected catalogue versions. Record the actual reply;
   a failure or refusal is not replaced with a scripted successful response.
2. Genuine follow-up: “Propose epochs 1 and number_of_examples 2. Keep batch_size 16,
   sequence_len 4, the selected CSV and all connections unchanged. Do not run it.”
   Inspect the concrete proposal diff. It must contain only those allowed instance
   edits, expected solution version/revision and the same solution identity.
3. Review/apply through the normal saved-solution assistant UI. Builder must reload
   that same solution. Check selected file/settings without repeating unrelated
   draft-only persistence demonstrations. No execution is triggered by chat/apply.
4. Optionally one explicit local-model Run, after normal validation/preflight and
   on-screen confirmation, may demonstrate that this applied design uses the same
   execution path. No further paid request is allowed. Inspect its own requested,
   delivered and current-run observed settings and hashes; preserve earlier results.

Verify the provider envelope excludes CSV contents and filename, credentials and
private runtime/observation keys. Cross-owner edits, stale revisions, malformed or
unsupported proposals, provider failure and over-budget requests must preserve the
saved solution and existing outputs. Normal provider contract review/ownership
guards still apply. Close the fresh grant after the bounded acceptance regardless
of success; record genuine failures and remaining gaps.

This plan supplies concrete reviewable prompts, effects and stop limits. Provider/model
selection, current pricing and this new spend authorisation are the remaining paid
acceptance inputs; none is inferred from prior approvals for free local development.
