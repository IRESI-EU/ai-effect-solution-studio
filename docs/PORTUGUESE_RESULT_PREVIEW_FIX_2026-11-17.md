# Portuguese recorded result preview correction

**Source fix tested; installation and browser verification on the retained Windows demo remain pending.** This is a narrow repair requested after the 18 November meeting freeze, not a feature expansion or production update.

## Cause and correction

The task-card Preview buttons POST to `/data-references/preview`. The generic owner-checked handler permits qualified file/inline outputs but deliberately rejects HTTP references. The completed Portuguese tasks advertise internal `http://pt-adapter:8080/control/data/...` references, so the buttons reached that rejection. The screenshot's generic error obscures this distinction. The serving API source `25dda8b1e9bfda78790dbe27e1b1ab38e7556c2b` has exactly the same pre-fix handler as the frozen Portal source.

The generated-CSV download already resolves an owner/workflow/task-bound signed capture. The repair reuses that validator for previews instead of enabling arbitrary remote fetches:

- Deployment ownership and immutable submission integrity/association are checked first.
- For the configured Portuguese evidence family, validate the signed terminal capture, authorization association, dataset/model provenance and current artifact hashes using the existing `portuguese_evidence.load` reader.
- Expose the validated TrainModel JSON and GenerateData CSV bytes through an optional internal preview map only after those checks pass.
- Require the caller's task/protocol/URI/format to match the exact signed output. No HTTP request or arbitrary browser-supplied path is used.
- Reuse the existing JSON/CSV formatter: JSON shows the recorded opaque model_ref; CSV shows up to 20 rows. The full CSV remains available through the existing download.
- Non-Portuguese generic previews keep their existing rules; invalid Portuguese evidence does not fall back to a live runtime. Successful preview responses are private/no-store.

No frontend source, runtime image, schema, contract, model, output file or provider/accounting mechanism was changed by this source repair. The live Windows application has not been updated from this workspace.

## Validation actually performed

Two focused real FastAPI route suites passed: **47 tests**, using isolated SQLite databases, synthetic signed evidence and explicit runtime/network-denial doubles:

```text
python -m pytest tests/test_portuguese_evidence.py tests/test_owned_artifact_preview.py -q
```

Coverage includes both task-card formats, the 20-row CSV limit, exact download hash equality, private/no-store, wrong owner/unauthenticated access before evidence reads, altered URI/protocol/task/format, corrupt JSON/CSV/model, invalid signatures and producer associations, immutable submission tampering, and the existing generic remote-preview denial.

Python syntax compilation passed. Existing deprecation warnings remain. The first collection attempt lacked the two contract fixture JSON files in the fetched snapshot; fetching the unchanged committed fixtures resolved collection. An initial offline dependency-cache attempt found no pytest; declared test dependencies were then installed into a scratch-only target. No application dependency file or lock was changed. Tests used Python 3.12.14 and the declared requirements-test resolution, not the retained Windows image. No Docker image build, PostgreSQL check or visible browser acceptance is claimed here. No model/provider/algorithm calls were made.

## Local Codex installation and verification

Use the same local Codex conversation. The user's request to correct the result view authorizes this narrow retained-review API update; it does not authorize production or another algorithm run.

1. Inspect actual branches, dirty files, current primary-demo API/web images and private Compose. Preserve the meeting-freeze record and all unrelated work. Read applicable AGENTS.md. Do not replace the retained checkout wholesale with the newest branch.
2. Fetch the published fix. Backport **only** its changes in `apps/api/app/main.py`, `apps/api/app/services/owned_artifact_preview.py` and `apps/api/app/services/portuguese_evidence.py` onto the retained serving API source `25dda8b1e9bfda78790dbe27e1b1ab38e7556c2b`. Check patch applicability and record the actual backport commit. Include/run the new regression assertions in the existing local test setup without copying credentials or fixtures into live data. Do not install unrelated production-portability/candidate changes.
3. Run the two focused suites using the existing pinned local environment. Preserve previous API image/config identities and verified backup metadata. Build the API only with the existing pinned offline packager. Do not rebuild web, pull dependencies, alter schema or replay profile initialization.
4. Update/recreate only the retained port-23124 profile's API, using its exact private Compose and the new immutable API image, with no-deps/no-build/pull-never semantics. Do not touch production, HTTPS staging, other profiles, original ML, sidecar, workers or volumes. Provider remains disconnected; ledger stays 28/28 closed; supervision stays OFF.
5. In the normal visible reviewer browser, open `http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results`. Click **TrainModel Output References Preview** and confirm a JSON object containing the recorded opaque model_ref. Click **GenerateData Output References Preview** and confirm a CSV table, not the generic error. Check the GenerateData input model reference if that existing control resolves the producer task.
6. Click **Download generated CSV** and verify 41,826 bytes and SHA-256 `553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540`. Confirm the historical workflow remains Completed, task counts unchanged, workers stopped and no new workflow/provider/algorithm/execution scope.
7. Input CSV/private training bytes and arbitrary HTTP references remain unsupported; do not loosen those controls to make every legacy Preview button succeed. If a positive output still fails, inspect its authenticated response and the actual served source before changing anything else. Do not run the algorithms again.
8. Publish the backport identity, new/rollback image, focused results and actual browser observations as a small checkpoint. Update the private freeze manifest with only this demo repair. Leave the rest of development paused and the primary demo available.

Return the actual JSON/CSV browser results, CSV hash result, serving API image/source, unchanged web/runtime identities and any remaining blocker. Do not label the Windows page fixed until that visible check passes.
