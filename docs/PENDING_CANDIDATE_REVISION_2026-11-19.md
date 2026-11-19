# Pending candidate identity and revision correction

**PASS: focused implementation, offline regressions and ordinary-designer browser walkthrough. Genuine recovery is not attempted or authorised.** No model calls, workflow Runs or real spending ledgers were created for this task.

## Root cause and implemented contract

The reviewed lineage is `128edf860a2abf9415c8a4da709bf493c17bf812`. Its genuine exercise served `48c24e7f1aa892be3095ff32b25472c18025c89a`. In I3 the saved graph had no applied instances, while a valid connected design existed only as pending edits. The model received a change summary, not an identified complete candidate. It addressed catalogue IDs as instance IDs, and the normal validator correctly rejected them. A matching confirmation needed no edits; actual pending revision also lacked an explicit base contract.

Implementation commit and browser serving source: **`4cb162a7b49d5fdb8155b18d334820c4e8add030`** on `codex/pending-candidate-revision-20261119`. Paired WP3 remains `39405313f9b685d91b8263b9b87a3fc42577331d`, with tracked source unchanged and its existing untracked test cache preserved. This increment changes Portal editing only.

Context now separates accessible `catalogue` choices, `saved_design` applied instances and a validated `pending_candidate`. The projection is derived read-only by replaying existing stored edits and allocations. It includes proposal/base identity and candidate digest, stable proposed node IDs, readable labels, service references, contract definitions/versions, effective settings/overrides, slot-bound connections and current/earlier assumption disclosures. It includes only a boolean about separate selected input, never input contents or runtime credentials/addresses. Ownership, saved-base version/content, normal graph validation and catalogue authority are checked before a pending candidate is advertised as current. Stale reviews remain inspectable but cannot be applied or used as a current pending edit base.

The focused response adds nullable strict `edit_base`. A proposal must copy an advertised saved or exact pending base: kind, saved timestamp, current conversation revision, and pending proposal ID/candidate hash when applicable. Non-proposals have a null base and no edits. Existing-instance edits and connection endpoints require a server-issued `target_ref` from that base. References are scoped to solution, saved version and proposal; they rotate between proposals while actual unchanged node identities stay stable. Catalogue IDs select additions/replacements only. Unique local references can identify additions within the current edit list. Unknown, raw-node, stale, cross-solution/proposal or catalogue-as-instance references are rejected. Two copies of a service remain individually targetable; no single-match service-ID inference exists.

An answer acknowledging a matching proposal preserves it exactly. Pending revision uses the same editor/validator to apply a delta to the derived candidate, then stores the complete cumulative edits, allocations and edit-batch sizes against the actual saved base. It replays those batches again and compares the full result hash before storing a replacement review. Batch sizes preserve normal boundary creation, node ordering and layout across later additions; no independently editable candidate graph or second editing engine is stored. Limits remain 24 service instances / 10 edits per response, with 80 cumulative edits and 12 retained historical disclosures bounding revision chains.

Each replacement review supersedes the previous proposal ID. The UI shows the complete current candidate, all effective settings and connections, and separately the changes since previous review. Current assumptions and earlier disclosure history are distinguished so an earlier Drawing A choice is not represented as the current Drawing B choice. Prompts require a published contract before calling any value/view a catalogue default. Explanations and reopening retain the current review. Apply replays and hash/authority-checks the full cumulative candidate, then uses the normal owned Builder writer. Undo restores the previous saved design. Compilation and explicit Run remain in their existing paths; chat never executes. Catalogue authority is also rechecked after provider response to reject drift during dispatch.

The actual updated SDK response-schema digest is **`05889d52b879b04e52af474bb615ee24d42387f354fe23744e4befde03610bc8`**. Offline SDK checks verify the same selected schema is dispatched, parsed, audited and included in the conservative input reservation. There is no legacy-response fallback.

## Successful transitions and negative checks

Eighty affected backend/provider/audit tests passed. Fourteen scoped-accounting tests passed separately. Five focused frontend component tests, TypeScript and the Next build passed. An additional whole-design Apply assertion passed. Earlier setup failures (wrong Python environment/temp directory, incomplete synthetic contract metadata, old fixture missing its new base and an accidentally added projection field) were corrected before the final browser build. Final machine-readable results are in the [sanitised evidence](verification/pending-candidate-revision-20261119.json); raw test diagnostics remain ignored.

| Requirement | Verified through normal offline paths |
| --- | --- |
| A–B | Empty saved graph to connected proposal; exact answer confirmation keeps proposal/graph unchanged |
| C–D | Parameter revision and compatible drawing replacement before Apply retain stable identities, settings and connection |
| E | Two same-service instances require explicit distinct target references or clarification; only the selected copy changes |
| F | Reopen and explanation retain current candidate and disclosures |
| G | Multiple revisions, including another connected addition, Apply to the exact whole reviewed design hash; earlier additions survive with latest values |
| H | After Apply, a saved-base response targets the saved instance correctly |
| I–J | Superseded Apply, old/raw/catalogue/cross-solution references, wrong proposal/hash/revision, malformed connection references, unsupported slots, Builder races and catalogue authority drift reject without overwrite |
| K | Undo restores the immediately previous saved design, including the original empty base for initial Apply |

The exact historical I3 fixture remains unchanged and digest-verified. Its edit payload is replayed as a negative regression with the newly required base explicitly wrapped around it; no success is inferred from rejection. No final candidate is seeded into the database. Fixture catalogue contracts are synthetic test setup, not provider scientific limits. SQLite tests do not establish PostgreSQL locking behaviour.

## Ordinary-designer browser acceptance

A small API/web harness reused a read-only backup of the existing explicitly OFFLINE catalogue database, with a separate database/cookie and fresh browser-created solution. It started no Docker project, worker, raw ML API or model. Authentication and ownership checks are normal. Runtime submission is explicitly disabled in this harness. Existing demonstrations were not replaced. Starter READY, actual API health and the browser were checked; critical serving file bytes match the implementation source.

An ordinary designer signed in, opened Design with AI, entered a fresh goal and used the normal Send action four times with visibly labelled OFFLINE responses:

1. Create Generator → Drawing A, maximum two, published boolean defaults and a disclosed view choice. Saved graph remained empty.
2. Confirm: exact same pending ID, candidate, settings, graph and disclosures.
3. Change maximum to three: new review superseded the first, preserving both proposed node identities and the connection.
4. Replace Drawing A with B: another review retained the drawing identity, generator settings and connection.

The designer refreshed the same solution and inspected the complete current review and earlier disclosure. Its state was exactly unchanged by reopening. Explicit **Apply and save reviewed changes** then saved two processing instances, the service connection and normal workflow boundaries. The whole saved design hash exactly matched the review: `32d85b1f0cf4dd07e3bd5501dd99d8da40192f4e1fef59b559fd1233ed8fe076`. Builder's generator inspector showed maximum three, both booleans enabled and Drawing B connected. The conversation remained on that same solution. Execution submissions remained zero.

Screenshots: [complete current review](verification/pending-revision-complete-20261119.png), [earlier disclosure and replacement delta](verification/pending-revision-review-20261119.png), [applied Builder instances/settings](verification/pending-revision-applied-20261119.png). This is successful UI/application acceptance using scripted responses, not evidence that a genuine model chooses the new references correctly.

## Historical I2 review note and preservation

The original I2 response described Drawing A as a default available in the catalogue. The contract did not publish a drawing-view default. A disclosed assistant-selected view is a reviewable choice; disclosure does not substantiate that catalogue-default claim. This note qualifies the unsupported wording. The original report, scores, actual responses and failed I3 fixture remain unchanged; the historical score is not a new endorsement of that wording. Future recovery correctness requires accurate distinction between published defaults and proposed choices.

The original checkout remains `12aae82dd47b078ba077aca40b0712c375b9d7f3` with its 150 dirty entries. The retained demo/review/genuine/offline workspaces remained healthy. Read-only preservation comparisons again confirmed unchanged snapshots and bytes for Danish `wf-7596a65908e7` / `wf-04a2b43ae794` and Portuguese `wf-c155a6dd6853` / `wf-6066f56dcf4b`. Phase I remains closed with exactly its prior three requests; Phase J's ledger remains absent. No old volumes, grants, services, branches or evidence were reset. No merge, force-push or production deployment occurred. Private database/account/operator paths and credentials remain ignored.

## Next live checkpoint

The [narrow recovery proposal](PENDING_CANDIDATE_RECOVERY_PROPOSAL_2026-11-19.md) fixes three planned genuine requests: create, confirm and revise before explicit browser Apply, with a new three-request/USD 0.21 ceiling. The operator initializer now accepts only lower limits for new exclusive scopes; old defaults and closed files are unchanged, and offline tests verify the lower cap. No real scope was initialized or activated. Separate concrete paid approval is still required.

Remaining uncertainty is genuine-model use of the new contract and references. General conversation reliability, model-driven compatible additions/replacements, full two-Run acceptance, independent renderer consumption, scientific owner confirmation and release readiness remain unaccepted. This checkpoint establishes reproducible pending-design revision ready for the proposed narrow genuine verification.
