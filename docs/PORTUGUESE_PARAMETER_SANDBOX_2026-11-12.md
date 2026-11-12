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
