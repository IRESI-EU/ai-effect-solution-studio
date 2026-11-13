# Portuguese parameter sandbox — 2026-11-12

Based on Portal PR #21 `4faa2c9dcf30f725aa890d027052277e5760f871` and maintained WP3 PR #3 `0221b7ecd4a2d5f072de640350ebc599df22131a`.

## Source checkpoint
The platform-controlled experimental sidecar lives in maintained AI-EFFECT/ai-effect-wp3, branch `codex/portuguese-parameter-sandbox`; initial source checkpoint `3e13a919dcd0c9a24f5a203013d24966a7a4c286`. Original Portuguese source, image and registrations remain unchanged. This is not partner approval or partner-native support.

Portal adds only an optional server-owned per-workflow control credential, injected into the private orchestrator wire copy. Compiled/browser payloads and immutable submission snapshots remain secret-free. The empty default preserves other profiles. Existing generic parameter registry/Builder/compiler/submission routes remain authoritative; no Dutch guard changes.

GenerateData exposes strict integer number_of_examples, default 10, sandbox range 1–20. Each example is a 100-observation sequence, not a CSV row. CSV format and sequence length remain fixed. TrainModel exposes epochs default 1, range 1–2, and batch_size default 4, range 2–16. These are conservative sandbox limits, not API-wide or scientific bounds. Upstream clamps batch size to available training sequences. ApplyFunction remains unavailable pending pinned function/kwargs schema qualification.

Retained integrated image: `sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f`. Source inspection confirms synchronous POST /train, multipart uploaded_file, user_id, model_name, epochs, batch_size, sequence_len; GET /generate takes user_id, model_name, number_of_examples, return_csv. The old wrapper's username/max_epochs/output_format mapping and asynchronous assumption do not match this image. The experimental sidecar translates explicitly without editing the original.

Portable validator SHA256: `1861736c1bd9c8a1e4d3aa86b1a2f58ef27bf5e272d682a619062cfb8b7171aa`. Canonical bytes and digest are reused; no second validator.

## Focused verification
- WP3: 30 HTTP/protocol tests passed with disabled-network upstream doubles; no real algorithm execution.
- Portal: 32 focused tests passed (219+ dependency warnings) covering existing parameter compatibility plus private service authority, actual Save/reload/copy/compile, independent duplicate instances, ownership and immutable submission.
- An earlier fixture incorrectly serialized optional enum as null. It was corrected to use the actual registry's exclude_none definition normalization. Canonical validation was unchanged.
- Initial attempts encountered Windows sandbox temporary-directory ACL errors; a fresh private directory under normal permissions passed. Those setup failures are retained in private logs.

## Activation boundary
No real training or generation has occurred at this source checkpoint. Publish isolated integration/configuration before dispatch. The entire separate journal is capped at one training and two generation jobs. Failure/uncertainty stops further dispatch, with no retry. Provider disconnected, shared allowance exhausted 25/25, no budget ledger attached. No original profile changes.

Integration, actual outcomes and exact demonstration instructions will be appended separately, preserving this source-only observation.

## Genuine execution checkpoint — appended after bounded verification

All three genuine local workflows completed on 2026-11-12. These are real
retained-API training/generation results, separate from the upstream-double
protocol tests. No provider or full Portuguese pipeline was invoked.

| Case | Workflow | Requested / validated | Verified outcome |
| --- | --- | --- | --- |
| Sole model bootstrap | wf-dc54e79834df | epochs 1, batch_size 4 | Saved model config epochs 1, batch_size 4, max_sequence_len 100, sample_len 1; one epoch/one batch logged |
| GenerateData first | wf-5d9b6ad6aa23 | number_of_examples 10 | 10 distinct example markers, 100 observations each, 1000 CSV data rows |
| GenerateData second | wf-956d17cb477d | number_of_examples 20 | 20 distinct example markers, 100 observations each, 2000 CSV data rows |

Both generations use the same saved solution, instance, contract pins, graph and
authorized model. The second value was changed with Builder's Generated sequences
control, Save draft, success dialog and reload. The initial count 10 and reloaded
count 20 were inspected in the actual application. Training controls show epochs
1 and batch size 4. Source tests additionally cover independent duplicate
instances, copy, ownership and immutable settings; those are not extra real jobs.

- Model SHA256: 9d7af5049b4e59daf14aca1e74d50419a88c10a71ca4076a347407932ca63f22.
- First CSV: becaca408f6a7a2f153575fa75a1737e0e57a7414f1b4ee1d620024924127fab (41807 bytes).
- Second CSV: 30912aefb86c40546ace2d035b7f862461a4b2069c7deb90488c02217c7e8e73 (84504 bytes).
- After the second Save and execution, the first immutable submission and
  authenticated CSV bytes/hash remain identical. Model hash also unchanged.
- Outputs use workflow+task-derived separate identities; equal logical task IDs
  across the two workflows do not alias their output files.
- Both CSVs were independently parsed and hashed through the authenticated
  artifact endpoint. Unauthenticated access was denied. Generic artifact-preview
  guards were not changed.
- Synchronous training HTTP 200 after save plus a model listing established
  completion; saved model configuration independently confirmed consumed values.
- Actual jobs: TrainModel 1/1, GenerateData 2/2. No retries, replacement attempts,
  provider requests or extra workflows. Journal ceilings are exhausted.
- All tasks terminal, zero queued list items; only the new worker was stopped.
  Other new components remain available for review.
- Shared ledger: 25/25, zero outstanding reservations, byte-for-byte unchanged
  SHA256 cf9fa12e87633b9e260d3983a3dd9e5c51df346c04237b3babd255ee66cd7d2b.
- C: headroom after verification: 18.70 GiB.

### Owner handoff

Builder:
http://127.0.0.1:23124/builder?solutionId=d86f823b-9a86-481e-8a2c-6c12ad30636f

Latest run:
http://127.0.0.1:23124/deployments/wf-956d17cb477d#results

Sign in as pt-sandbox-designer@example.test, using the password in the private
original-checkout file:
local-backups/portuguese-sandbox-20261112/profile/credentials.json.
No password is included in this report. Login/proxy and actual Builder access
were checked with that isolated designer. No existing account/profile changed.

Select the single processing step to inspect Generated sequences = 20. Review
the earlier run's immutable requested/effective value 10 separately. Save is
design-only; do not confirm another deployment. The bounded jobs are complete.

The generic results page truthfully displays completed runtime state and validated
immutable parameters. It currently says algorithm-consumption evidence is not
enabled for this runtime. The separate, correlated experimental adapter artifacts
and saved model configuration above supply the consumption proof; no Dutch capture
profile was impersonated and no broader UI evidence adapter was added.

### Reproducibility and scope notes

See deploy/portuguese_sandbox/README.md and verification.json for pinned images,
source identities, safe startup/shutdown and sanitized machine-readable evidence.
Actual request snapshots, CSVs, model configuration, source/build manifests and
rendered screenshots remain private in the original checkout's
local-backups/portuguese-sandbox-20261112 directory. Raw data/models/databases and
private configuration are excluded from Git and build contexts.

The next, separately authorized connected-workflow milestone is recorded in
PORTUGUESE_CHAINED_WORKFLOW_2026-11-13.md. It preserves this three-job proof and
its exhausted authorization; it does not reinterpret the standalone proof as a
qualified TrainModel-to-GenerateData handoff.

The initial resource manifest inherited an older retained WP3 image identity.
A source parity check rejected that image before any dispatch. A separate exact
source layer c0a0b19a07619401f74ff944146b4d3fd33f3b4bc86fd71a7dfadcc1ceb85589
was built, verified against all maintained PR #3 runtime Python bytes and pinned
in published profile configuration before training. Original snapshots are
preserved; this note reconciles their earlier preparation manifest rather than
rewriting history. Bootstrap import-path/ORM metadata and missing experimental
image metadata were corrected before any submission. No failed real job was
repaired or retried.

The retained original image contains a packaged test_user_id/test_model. It was
not selected or used as an approved model. The fresh server-derived owner
namespace was empty, justifying the one authorized training. The project has its
own model volume, database, Redis and adapter journal; no original writable
volume or ledger is mounted.

This proves bounded parameter delivery, completion and output semantics on these
pinned local images. It does not establish scientific suitability, Portuguese
owner approval, hosted portability, multi-tenant model authority or production
compatibility. ApplyFunction, alternate output format, sequence length, arbitrary
functions/kwargs, paths and overwrite controls remain unavailable. Provider
allowance stays exhausted and disconnected; no production, merges or tracker
changes were made.
