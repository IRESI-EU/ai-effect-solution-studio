# Normal saved CSV input and owned results — 18 November 2026

This increment reviews and builds on Portal `72e440c7003f6c210f3a13e7dd0d2c4b6b19c550` and WP3 `7e16c810bd928a4bc13df16cb0fb7d712e6f57d8`. Both published commits and the full Windows qualification report were inspected through GitHub. The reported DGAN probe calls the actual model implementation and inspects its newly saved configuration and weights; its model qualification remains separate from the fixture task observations used by the earlier Portal result test. No SharePoint access was needed.

## Completed connections

| Gap found in review | Implemented behavior |
| --- | --- |
| Normal Builder input was always encoded as JSON; training expects CSV. | Builder now selects a small UTF-8 CSV through Deployment options → Run input → CSV data. Selection stays inside the existing owned solution's `run_input`, Save/version checks and immutable Run snapshot. The compiler sends an ordinary inline CSV DataReference. No local path, remote URL or service-specific dataset registry is introduced. |
| A runtime could advertise parameter support while ignoring the new CSV input mode. | WP3 advertises input validation; each start operation must advertise implemented `inline-csv-v1` support. Preflight, submission and Control dispatch check this without algorithm execution. Older runtimes reject the new input path before creating a job. |
| The new HTTP reader rejected normal WP3 output references containing optional metadata. | It compares the authoritative protocol/URI/format while retaining exact operator target, task/configuration, receipt and byte/hash checks. Ancillary metadata confers no fetch authority. |
| New receipt details and CSV counts were absent from the results screen. | Existing Recorded instance settings now shows the selected CSV name, validated submitted values, delivered values, CSV observations and the separate algorithm-evidence verdict. Received inline CSV bytes must match the immutable selected input hash. |

The input selection is deliberately bounded: UTF-8 CSV text up to 60,000 bytes, within the existing 64 KiB saved JSON input ceiling, unique nonempty column names and consistent data rows. The data lives in the same owned solution and submission storage; there is no new upload database or credential mechanism. Ordinary JSON/prompt input remains supported. The assistant receives only the existing input-selected indicator, not CSV contents or its file name, and edits the same saved solution through the same writer. Selecting data, asking the assistant and applying a proposal do not dispatch algorithms.

This does not claim arbitrary dataset sizes, managed dataset storage, multiple independently selected per-step datasets or support for every interface. A compatible service implements and advertises the transport. No Portal service-ID or node-specific branches were added. The runtime-specific Portuguese mapping remains in its node connector. Owner-confirmed index/data semantics and scientific limits remain external dependencies.

## Verification actually performed

The new normal-route integration journey uses authenticated provider, administrator and independent designer accounts. It imports services, discovers settings, saves drafts, exports/installs isolated qualification definitions, performs valid/invalid software checks, confirms explicitly synthetic fixture evidence, approves/publishes fixture contracts, selects/saves CSV data and explicitly submits two runs. Real HTTP WP3, native Redis, Worker and configured Control provide the observed task state and HTTP results; no task observations or immutable submissions are fabricated for this journey.

The unchanged Portuguese FastAPI source executes its real query/multipart binding and CSV construction. Its **DGAN dependency is an explicit double** in this environment. Manual mode edits settings through the normal saved-solution route. Assistant mode injects an explicit structured assistant response, applies it through the normal proposal writer and uses the same Run path. Both runs retain their original submitted inputs/settings, output hashes and task associations. Old output evidence remains unchanged after the next edit/run. Cross-owner access, unsaved/replaced CSV input and unadvertised input transport are denied. CSV contents are excluded from model context.

The existing Danish enumerator/renderer journey also passes using the actual native algorithms, including its assistant-boundary-double variant. These reusable paths remain in place; work has not narrowed the Portal to the Portuguese pair.

| Check | Result |
| --- | --- |
| Portal selected CSV + full normal API runs + ownership/results + saved-solution assistant + parameter/discovery regressions | 148 passed |
| WP3 Control/configuration + CSV transport checks | 54 passed |
| Portuguese source/connector + existing Danish source runtime | 42 passed |
| Rendered CSV/results and assistant components + Builder/submitted settings helpers | 26 passed |
| Next production build, including TypeScript | Passed |
| Canonical validator, all five byte/provenance exports | Passed |
| New WP3 patch applied to its published parent in a fresh worktree | Exact tested tree reproduced |

The first build attempt encountered an external-dependency symlink restriction in Turbopack. Copying the existing dependency closure into this isolated worktree resolved it; no dependencies were installed or changed. Existing dependency deprecation warnings remain.

[Sanitised manual/assistant API traces](verification/normal-designer-csv-api-20261118.json) contain the explicit test boundaries, per-run delivered settings, CSV counts, workflow IDs and output hashes.

## Source and next acceptance gate

Portal branch: `codex/normal-designer-run-20261118`, based on the published Windows increment. WP3 local source branch: `codex/normal-designer-evidence-20261118`, source commit `e837d12365be7cd8bcc872db845f9f4211a704ec`, tree `8aa7bab50d9d934ed9f333b4a8fda98ed89147e0`, parent `7e16c810bd928a4bc13df16cb0fb7d712e6f57d8`.

The current GitHub app can read WP3 but its create-tree request returned `403 Resource not accessible by integration`. No WP3 remote ref was changed. The [exact WP3 patch](../deploy/patches/wp3-selected-csv-input-20261118.patch) is preserved here with SHA-256 `eec0045eaf3eca8bf230c8b00a19786a5c7bb243f6c98c7408f068e67bb5a511`. Applying it to the published parent reproduced tree `8aa7bab50d9d934ed9f333b4a8fda98ed89147e0`. Windows Codex can publish this new branch through the push access it already verified.

The next showcase is an ordinary designer selecting a CSV on screen, saving, changing parameters, explicitly running and inspecting the new run's own CSV/settings. It requires a fresh execution workspace with this paired source. The existing 23125 guarded review workspace must not be repurposed by removing its restrictions. Its last reported build is `8a15bce`; this pass does not claim any Windows URL was upgraded or started.

The earlier real DGAN fixture's requested batch 16 → effective 8 remains a real observation of its own run/image. It must not be copied into a new run's result or inferred from delivery. The updated UI can display a separately verified consumed value different from the submitted value, but the new HTTP reader intentionally does not infer model consumption from a receipt. Actual current-run model observations and a generic verified observation path remain necessary to show runtime-effective batch 8 automatically.

Remaining product gates: real model/browser/independent-user acceptance of this new normal journey; provider-confirmed production data/index/settings; genuine fresh LLM conversation and follow-up under separately approved paid acceptance; second independently onboarded service-family acceptance and useful multi-step/multiple-input composition; coherent staging/PostgreSQL/migration/rollback and production release review. No paid call, production deployment, retained Windows demo/data/model-volume change or historical scope reopening occurred here.

Use the [next Windows Codex task](CODEX_WINDOWS_NORMAL_DESIGNER_NEXT.md) to continue from the already inspected environment without repeating the initial inventory.
