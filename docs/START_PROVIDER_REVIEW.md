# Test the new provider-review feature

**This is a NEW test workspace. It is not the old demo at port 23124 and is not production.** The starter is prepared for Windows; it has not been run on your Windows computer by this agent. Do not assume port 23125 is available until the starter prints **READY**.

## Start it once

1. Save `deploy/parameter_onboarding/Start-Provider-Review.ps1` from the current development branch onto your Windows computer. Review the script, then run it in your normal PowerShell session. It uses the existing Portal checkout path supplied for this project. If that path or its Python environment differs, pass `-Checkout` or `-Python`; the script stops rather than guessing or installing a new stack.
2. Leave its window open. It creates a separate checkout and separate review data, reuses installed dependencies, and builds the interface in a separate source copy. It does not switch your existing branch, install packages, change Docker, or modify the demo.
3. Wait for **READY**. The browser opens the new sign-in page. The normal default is `http://127.0.0.1:23125/login`; this address becomes usable only after the starter succeeds on your machine.
4. Open the new private `credentials.private.json` file at the path printed in that window. Under `provider_portugal`, use its **email** and **password** to sign in. Keep this file private. These are new review accounts; do not use the old demo account.

## Your next test — save a parameter draft

1. Click **Publish** in the left menu. This menu appears for the provider account.
2. Find the existing-service selector under **Adjustable service settings**. Select **REVIEW COPY - model_trainer1 / TrainModel**. It is a copy of catalogue metadata, not a deployed replacement service.
3. Open **Supply an interface description**.
4. At **Interface description file**, choose `portugal-source-openapi.json`. You may use the file you already downloaded. **Do not put it in Advanced import → Paste JSON.**
5. Enter the file's source reference shown in the corrected daily walkthrough, or a clear local-review source reference. Select **POST /train** from the operation dropdown.
6. Click **Discover candidate settings**. You should see `sequence_len`, `batch_size` and `epochs`. The uploaded CSV, user identity and model reference are separate inputs/controls.
7. Select **epochs**. Check its meaning and source-declared default of **10**. Leave limits blank if the source and provider have not declared any.
8. For this temporary review only, enter operation identifier **urn:local-review:training** and version **0.1.0**. These are local draft identifiers, not an official Portuguese service release.
9. In the runtime-mapping description, enter **Planned mapping: configuration.parameters.epochs to the /train query parameter epochs; actual consumption still requires qualification.**
10. Click **Save reviewed settings as draft**. A card marked **draft** should appear. Refresh the page, select the same service again, and confirm the draft remains.

**Success means the new review draft was saved and survived refresh.** This is the first user test of the new onboarding feature. A screenshot of that draft card is useful milestone evidence. It does not establish runtime consumption or active designer configuration.

Runtime confirmation, publication, new execution and paid chat are deliberately disabled in this workspace. Do not claim checks that have not been performed. The same interface/code applies to other nodes; separate review provider accounts are created for each declared node in the public catalogue.

## Stopping and resuming

Press **Ctrl+C** in the starter window to stop the new API and interface. Its review database and drafts remain. Start the same review workspace to resume; it never resets existing review data. If a port or folder belongs to something else, the starter stops and reports the problem rather than replacing it.

If the separate review checkout already exists at a different source version, the Windows starter preserves it and stops. Update that separate checkout through a normal reviewed Git operation; do not reset or replace the old demo to make it start.

## Developer verification and limits

`review_workspace.py` runs the actual API with normal authentication and a dedicated SQLite database. PostgreSQL JSONB is compiled to SQLite JSON **only inside this explicit review launcher**; the normal application's database behavior is unchanged. This is not PostgreSQL locking/migration qualification.

It copies selected public catalogue metadata, marks every copy pending review, records source provenance and creates no active contracts or runtime grants. It uses new random IDs, normal node ownership, fresh review accounts, a unique session-cookie name, separate ports and isolated contract storage. No old database, volume, model, grant, ledger or credential is read. Provider keys and experimental settings are scrubbed from child process environments. Runtime verification/publication, workflow execution and chat calls are blocked at the launcher boundary. The real shared-solution assistant UI is visible but reports its provider disconnected; no synthetic assistant is substituted.

The actual frontend production build runs in a source copy so that Next's generated TypeScript metadata cannot alter the checked-out application files. Both hoisted and workspace-local Next installations are supported; no dependency installation is attempted.

Native-process verification uses copied public catalogue metadata: **37 records, four node-provider accounts plus administrator/designer**. Normal Portuguese provider login, source discovery, draft persistence, isolated cookies, cross-node ownership denial, frontend proxying, disabled runtime/provider paths and clean process shutdown are checked. The sanitized checkpoint is [provider-review-workspace-20261118.json](verification/provider-review-workspace-20261118.json).

The Windows PowerShell starter and browser interaction on the user's computer remain **unverified**. The live screenshot-based review above concerns the old demo only. Production remains unchanged. No paid model or ML algorithm call was made in this milestone.

Reproduce the launcher check from the Portal root with the matching API Python environment:

```sh
REVIEW_TEST_WEB=1 pytest -q deploy/parameter_onboarding/tests/test_review_workspace.py
```

The default portable test uses explicit source-metadata fixtures. `REVIEW_CATALOGUE_SNAPSHOT` optionally selects a sanitized local snapshot for the 37-record check. `REVIEW_WORKSPACE_EVIDENCE_FILE` writes a checkpoint only after all checks and shutdown pass.

For a prepared checkout with its dependencies already available:

```sh
python deploy/parameter_onboarding/review_workspace.py launch --directory local-backups/new-provider-review --open-browser
```
