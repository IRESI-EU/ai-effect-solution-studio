# Portuguese local milestone: human and code review handoff

Local parameterisation and bounded Design with AI behavior verified; provider audit evidence remains partial; independent usability and code review remain outstanding.

[Colleague guide](PORTUGUESE_HUMAN_WALKTHROUGH_2026-11-17.md) and
[blank observations](PORTUGUESE_HUMAN_OBSERVATIONS_2026-11-17.md): **READY, NOT YET PERFORMED**.
No colleague has been contacted or observed. The earlier
[genuine-provider acceptance](PORTUGUESE_PROVIDER_ACCEPTANCE_RESULTS_2026-11-16.md)
remains **PARTIAL**, with all three behavioral cases PASS. Missing historical
returned metadata has not been reconstructed. This pass made no provider request,
algorithm call, new scope, saved-design mutation or serving-component update.

## Future provider evidence: source-only change

Published implementation checkpoint: `b1fcd8e80d9d045357aa3fa0788251ebaabd8112`
([focused diff](https://github.com/IRESI-EU/ai-effect-solution-studio/commit/b1fcd8e80d9d045357aa3fa0788251ebaabd8112)).

The existing opt-in `design_ai.provider.audit` FileHandler is reused. Format3
captures requested and returned model/tier separately, provider response ID,
available `x-request-id` (or SDK request ID), allowlisted nonnegative integer usage,
available cache-write/read and reasoning counters, and the SDK-schema-validated
AssistantTurn after parsing. Absent/invalid metadata is null with explicit
`unavailable_fields`; requested values never substitute for returned values.
This follows the [official Responses reference](https://developers.openai.com/api/reference/resources/responses/methods/create):
the returned processing tier can differ from the requested tier.

SHA-256 hashes use sorted compact UTF-8 JSON, rejecting nonfinite numbers:
- `configuration_sha256`: allowlisted model/store/tier/output/reasoning/cache options,
  fixed Responses transport, timeout/zero retries and AssistantTurn JSON schema.
- `request_sha256`: that configuration and schema plus the exact SDK input arguments
  (system text and serialized complete model context). This is an **SDK-argument
  hash**, not a claim to hash HTTP framing or hidden SDK-generated schema names.
- `validated_response_sha256`: the schema-validated turn before evidence redaction.

An async-local scope correlates the actual owned draft/server-read revision and
optional browser discovery-conversation UUID with the existing accounting permit,
scope, consumer and environment. It resets on exceptions and isolates concurrent
tasks. Browser conversation IDs confer no authority and never enter model context.
Legacy clients can omit them; unavailable correlation stays null. Focused draft
conversations remain correlated by draft ID even without a discovery UUID.

Usage still settles/acknowledges **before parsing**; the same reservation survives
malformed output, timeout or uncertainty. Capture happens in the existing attempt's
finally path. It neither retries nor changes provider kwargs, canonical proposal
validation, ownership checks, duplicate protection or failure responses. Captured
structured content is untrusted data, not an executable proposal/replay authority.
SDK schema validation is explicitly distinguished from later canonical registry,
revision and authorization checks.

No prompt/history, complete raw payload, credential/header collection, dataset
bytes, private filesystem paths or hidden reasoning text is required. Evidence
uses numeric allowlisting, key redaction, serialized-edit redaction and omission
of path-bearing/CSV text fields; sanitized content can differ from the validated
turn, whose digest is separately retained. Optional logging/serialization failures
cannot change settlement or returned behavior. They do not create a second audit
store, ledger or fallback.

The retained application is **not repackaged or changed**: review does not need
this future capture code installed. Before any separately authorized future
session, package the reviewed changed API/web sources, enable the existing private
FileHandler configuration (`deploy/restricted-beta/provider-audit.json`) only in
that authorized session, and verify its writable private sink with offline doubles.
Ordinary app logs must not be the capture destination. Do not reactivate the closed
28/28 batch to test capture. No live success is claimed for this new capture code.

## Focused validation and agent inspection

- 45 focused backend checks: evidence/provider adapter/authority protocol, using
  disposable synthetic accounting and SDK/HTTP doubles. Cover success, genuinely
  absent returned model/tier/IDs, malformed output after settlement, redaction,
  logger failure, complete hashes, exact permit correlation, task isolation,
  stale revision, unavailable accounting and no dispatch/fallback on denial.
- Seven rendered-page tests pass with network mocked, including forwarding the
  existing conversation UUID while preserving history/clarification. TypeScript
  `npm run typecheck` passes. Existing deprecation warnings remain. No unrelated
  full suite, algorithm, dependency download or image build was repeated.

- Actual existing-account browser sign-in, genuine A recommendation, saved
  training2/batch4 and generation20/selected CSV/model connection, unanswered C,
  and historical completed results were inspected read-only. Download through
  the actual results link matches the preserved41,826-byte CSV hash above.
- Read-only preservation verifier confirms all12 saved designs (11 prior plus
  acceptance B), protected prior AI draft, unchanged C draft, nine completed
  journal jobs/four closed execution scopes, queues and56 containers/images/mounts.
  Provider disconnected; authority listener absent; internal-only original API
  configuration byte-identical. Workers stopped; API/adapter supervision/grants OFF.
  Ledger28/28 closed, scope3/3 closed, zero outstanding, prior accounting retained.

Reproduce from `apps/api` with the original installed Python environment and
`PYTHONPATH` set to that API directory:
`python -m pytest tests/test_provider_evidence.py tests/test_design_ai_provider.py tests/test_allowance_authority_protocol.py -q`.
From `apps/web`: `node --test app/design-ai/page.test.cjs` and `npm run typecheck`.
These tests supply only offline provider fixtures and disposable databases.

Agent screenshots (not human usability evidence):
[saved count20](../deploy/portuguese_sandbox/evidence/human-review-20261117/saved-generation-20.jpg),
[historical count10](../deploy/portuguese_sandbox/evidence/human-review-20261117/historical-count-10-results.jpg),
[unanswered C](../deploy/portuguese_sandbox/evidence/human-review-20261117/unanswered-clarification.jpg).
Private verifier output is in original-checkout
`local-backups/pt-human-review-20261116/checkpoint-readonly.json`; credentials remain
only in the retained profile credential record. No private contents are published.

## Actual serving identities and rollback

These serving identities are unchanged by this review pass, distinct from new
source-only audit commits. The same images and current database remain retained.

| Component | Serving source | Image SHA-256 |
| --- | --- | --- |
| Portal API | `25dda8b1e9bfda78790dbe27e1b1ab38e7556c2b` | `802fb23b14152d5043659b8e7c254926c87b5c26cbeade1cdced7acb3440ea6e` |
| Portal web | `4296ec484542ce9dfa4d1b45e3ce9a897793edc3` | `a7ca1100fb5364ca876117a176b351f411bb330f5baa8dfe6a4f09de49d635ed` |
| Sidecar | `c98b454b1a9ce9b9a154ad82ef104678ba78b443` | `7709b05cb41329a2ef55a05816c82e2d9371cdde131ee92e2c0a31fc8247a8c6` |

Stopped worker candidate remains
`sha256:75dc18e23e464b3b1ad6c4368f965dcf8185d163a20dd0d92276f6408f217bdb`.
Original ML remains `sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f`.
No rollback is needed for this source-only pass. Current original private compose:
`local-backups/portuguese-sandbox-20261112/profile/compose.private.json`, identical
to retained `local-backups/pt-provider-acceptance-20261116/compose-before.private.json`.
Before a later approved API/web installation retain these exact image IDs/pins.
If that installation needs rollback, restore **only** API/web image references
from that verified configuration, preserve provider/supervision OFF, and use
`docker --context desktop-linux compose -f $cfg up -d --no-deps --no-build --pull never api web`.
Never restore an older database/journal over completed evidence, bootstrap, run
old authorization scripts or start a worker. Inspection restart/shutdown procedure:
[CHAIN_RUNBOOK](../deploy/portuguese_sandbox/CHAIN_RUNBOOK.md).

## Review order, sensitive boundaries and remaining actions

1. Review/merge prerequisites in their existing stacks first: Portal PR21
   (`codex/conversation-context-repair`, base SHA4faa2c9dcf30f725aa890d027052277e5760f871)
   before [Portal PR22](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/22);
   maintained WP3 PR3 (`codex/review-instance-configuration`,
   SHA0221b7ecd4a2d5f072de640350ebc599df22131a) before
   [WP3 PR4](https://github.com/AI-EFFECT/ai-effect-wp3/pull/4).
   Review both dependent runtime/protocol and Portal changes together before any
   future execution deployment; this is an order for review, not approval to merge.
2. Portal reviewers: strict parameter compiler/pins, profile-scoped CSV selection
   and backend authorization, fresh null-metadata/input persistence and dirty state,
   model_ref binding retention, owned immutable-submission/download evidence,
   inspection-only admission and uncertain/duplicate dispatch handling. Generic
   arbitrary artifact preview stays blocked; the owner-bound CSV route is separate.
   Also review the small new audit formatter, redaction, UUID correlation and
   before-parse settlement ordering. Generic pair composition still excludes
   sidecars/external inputs; only the explicit reviewer registration is enabled.
3. WP3 reviewers: canonical http-parameters-v1 version validation; unchanged
   original API argument mapping; opaque owner/workflow/producer-scoped model
   references and artifact hashes; additive journal authority, bounded standby
   leases, no retries after uncertainty and closed-scope preservation.
4. Human colleague: perform the blank-sheet walkthrough. Responsible owner/code
   reviewers: review the current draft diffs and existing check requirements;
   no self-approval, reviewer request or merge occurred. No newly demonstrated
   defect remains in this focused audit scope; historical missing wire/model
   metadata is irrecoverable and the overall acceptance remains PARTIAL.
5. Portuguese-hosted access still needs the responsible service owner's chosen
   deployment/family, endpoint/auth/data permission, contract/seed-independent
   parameter semantics/resource envelope confirmation and deployment-specific
   qualification. Scientific suitability and production compatibility remain
   unverified. Future provider/execution work needs its own applicable prerequisites;
   this handoff creates no allowance or execution authority.
