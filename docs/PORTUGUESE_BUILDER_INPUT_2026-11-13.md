# Fresh Portuguese Builder input — 2026-11-13

Starting Portal PR #22: `08130d445b37841ef131913d6a6a51012ad64d7a`.
The completed connected execution and its original evidence are unchanged; this
is a design-only follow-up. No new workflow submission or algorithm is authorized.

## Focused implementation checkpoint

Fresh Builder designs previously discarded run_input when design_metadata was
null; dirty-state detection had the same conditional. The published connection
action was inside a technical dialog. Dataset input required editing hidden JSON.

Builder now persists normalized workflow input even without prior metadata,
preserves existing provenance/authority fields, includes input in dirty state and
invalidates checked results when input changes. Null/empty objects normalize to
no input. Save/reload and copy retain the input, parameters, pins and binding.

Data connections shows Training CSV for a workflow requiring dataset_ref. A
minimal authenticated endpoint returns only the retained sandbox's configured
label/opaque reference to its existing designer. Other users/profiles receive no
choice; anonymous access is rejected. The control calls it Sandbox test dataset
and explains that this is this profile's test input, not a fixed CSV requirement
of the original Portuguese service. No paths, tokens, uploads or dataset catalogue
are exposed. The existing adapter mapping into uploaded_file is unchanged.

Use published connection is visible directly beside an unbound compatible edge,
using the existing explicit pin/binding callback. Incompatible or ambiguous
contracts do not acquire that action. Technical identifiers stay in the dialog.
Missing training input shows “Select a training CSV before validating.” beside
the control; normal backend compile still rejects missing or unauthorized input.
Reverse direction remains blocked.

Focused checks: 41 backend route/binding regressions, 19 frontend helper checks
and typecheck passed. An initial new regression compared hydrated service metadata
to its intentionally minimal fixture; it was corrected to assert unchanged
configuration and pins, then the complete focused set passed. No implementation
failure or real execution was concealed. SQLite tests do not establish PostgreSQL
concurrency. Actual browser acceptance is pending the separately recorded update.

## Retained-profile update boundary

Only Portal API/web may be rebuilt and replaced, using the existing offline
build_candidate.py and pinned retained inputs. Preserve previous image IDs and
private compose backup. Populate PORTUGUESE_TRAINING_DATASET_REF from the existing
private policy's dataset_ref, paired with the existing evidence owner and exact
pt_parameter_sandbox database identity. Do not change any runtime/contract/worker,
mount, port, account, provider or ledger configuration. No migration is required.

Private records: original checkout local-backups/portuguese-builder-20261113.
They include a consistent PostgreSQL dump, all five existing saved designs,
completed journal/audit rows, ledger hash and the prior compose configuration.
Never stage these private records or credentials.
