# Portuguese chained workflow — 2026-11-13

Starting review heads: Portal PR #22 c6e97b3e7ec1c9f7e2255123c5058a56e3a8472b;
maintained WP3 PR #4 4f349c2e39c885633b38c6a961070514dd7b4497.

## Preserved owner failure

Owner solution 0fe46709-e564-4a82-b9f2-a7d6d94a8483 remains unchanged.
Actual processing edge is GenerateData → TrainModel; it has no selected slot
binding and no separate operation-contract pins. Its parameter configurations
pin pt-sandbox-generate-v1 / pt-sandbox-train-v1, both 0.1.0. Generation count is
20; training settings are epochs 2 and requested batch_size 6.

The old frontend reports the actual reverse direction as a catalogue-label
mismatch. Its summary instead says TrainModel is connected to GenerateData,
naming the receiver first. That wording is ambiguous even though it describes
the same saved edge. More seriously, normal compile and runtime-preflight both
returned 200 for this unqualified legacy edge. This is not compatibility proof.
The complete responses, saved graph and rendered failed validation were retained
privately before edits. No Save, training or generation occurred on this design.

TrainModel needs an authorized dataset_ref workflow input and emits model_ref.
GenerateData emits CSV sequences; it cannot supply the required dataset_ref.
The 0.1 contracts do not declare a cross-operation binding. Matching/reversing
labels cannot fix that missing runtime delivery.

## Source checkpoint: explicit model handoff

New separate experimental registrations/contracts use 0.2.0. The original 0.1
definitions, registrations, historical references, three completed jobs and
original Portuguese APIs/images remain unchanged.

Workflow input → TrainModel → GenerateData → Workflow output:
- TrainModel accepts a separate inline authorized dataset_ref.
- Its model_ref output is an HTTP JSON reference, forwarded unchanged through
  the existing whole-output-v1 binding to GenerateData.model_ref.
- The generator does not fetch arbitrary URLs. It resolves that exact local
  producer-reference URI against the guarded journal, same owner/workflow/task,
  authorization, model identity and artifact digest.
- Models use workflow/task-derived identities; no bootstrap-model substitution.
- A separate read-only observer reuses the retained original ML dependencies
  and model volume read-only to inspect the saved model configuration/hash.
  It does not change the original API or run an algorithm.
- Four capability entries distinguish historical 0.1 and chained 0.2 operation
  versions. Runtime binding negotiation checks the exact version and normalized
  I/O contract digest with private server-owned control authorization.
- Unknown, cross-owner/workflow, stale, corrupt and unrelated references fail.
- Versioned signed terminal captures correlate both tasks and their model/output
  hashes. Portal reads only bounded, derived paths through read-only volumes,
  validates ownership and immutable submissions, authenticates capture records
  and rehashes artifacts. Historical inspection does not require live runtime.
  Old 0.1 settings/results remain readable without fabricated consumption claims.

The journal adds authorization, audit, scoped-job and run-specific model tables.
No old row, limit, checkpoint or model mapping is replaced. An explicit operator
creates a new attributable one-workflow/one-training/one-generation authorization,
binds its exact frozen snapshot to the returned workflow once, and closes it.
The worker CLI processes only that workflow and uses its private service key;
the daemon and owner-created jobs must remain stopped. No automatic retry.

Builder uses explicit source → target summaries, explains workflow-only inputs
and required model_ref bindings, declines unsupported published directions,
retains bindings during setting edits, and counts processing operations
separately from structural input/output nodes. Legacy label checks remain for
unqualified connections; pinned connections use authoritative contract checks.

## Offline verification

- 52 WP3 experimental protocol/journal/observer tests passed, with upstream and
  saved-model-loader doubles. No scientific execution in these tests.
- 51 focused Portal chain, evidence, ownership, binding and standalone tests passed.
  SQLite fixtures do not establish PostgreSQL concurrency.
- 20 focused browser-helper tests passed; typecheck passed.
- Batch-clamp tests distinguish requested/validated 6 from observed model batch 4
  with four training sequences. The new real phase requests batch 4.
- Invalid directions, missing bindings, representations/version drift, model
  provenance, corruption, runtime outage, uncertainty, duplicate dispatch and
  immutable Save/copy/settings behavior are covered.
- The observer's initial legacy validator import stalled Windows test collection.
  It was changed to strict modern Pydantic APIs supported by the verified retained
  ML environment (2.10.6); its two focused checks then passed. No real job failed.

## Activation boundary

No new real job at this source checkpoint. The authorized new phase is exactly
one combined submission, training epochs 2/requested batch 4, generation count 10,
fixed sequence length 100/CSV, existing CPU 2/RAM 3 GiB ML limits and synthetic
dataset. Old authorization remains exhausted. Publish integration/configuration
before dispatch, inspect queues, freeze inputs/pins/resources and use a new
audited journal authorization. Failure or uncertain submission ends the attempt;
no retry, repaired-result pass, replacement workflow or substitute model.

Provider disconnected; shared LLM allowance remains 25/25. No original service,
production, merge, partner-repository or tracker changes.
