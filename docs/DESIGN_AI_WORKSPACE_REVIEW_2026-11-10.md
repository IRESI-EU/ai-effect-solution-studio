# Design with AI workspace review

Starting source: verified draft PR #15, `5d9c398cad1a0944f3fe61edc1da90a832341e11`. Implementation: **`66114c6fe3b8183dd890ecc1aeb7464ba92c0a60`**. This focused draft stacks on PR #15 without changing the earlier stack or backend composition scope.

## Owner acceptance and unresolved feedback

The owner explicitly confirmed the following in the 10 November brief. These are **owner functional observations**, not independent usability or real-provider acceptance:

| Owner observation | Reported outcome |
|---|---|
| Generator count 3 | Confirmed |
| Design, connection and count survive refresh | Confirmed |
| Undo restores the empty design | Confirmed |
| Reapply and Save | Confirmed |
| Purpose and controls understandable | **PARTLY** |
| Remaining feedback | Still text-heavy and far from the original reference |

Preserved owner draft: `49ce7803-1e55-51ac-b47b-94b8731a913c`; saved solution: `f6f86d6f-107a-46b4-8ce1-000b06405473`. Its complete stored rows and the other pre-existing draft/solution rows are unchanged. It was opened read-only for handoff; no owner Create/Apply/Undo/Save was replayed. The original earlier reports and outcomes remain historical.

## Reference inspection and bounded redesign

The [owner's original reference](https://ai-effect-chatbot-composer.vercel.app/) was inspected in its empty and populated browser states. It gives the central canvas most of the workspace, uses compact catalogue cards on the left and keeps the assistant and composer adjacent on the right. Its catalogue, graph mutation and execution/readiness messages are scripted demonstration behavior. None of its unsupported services, automatic graph changes, Ready/Workflow complete claims or simulated execution was adopted.

The actual authenticated Design with AI page now uses that spatial hierarchy within the existing AI-EFFECT identity:

- Compact library contains only existing server-returned creation paths or capabilities in the authorised current review. Inspect cards never add nodes directly. Unavailable generic Dutch prompts/cards no longer occupy the main workspace.
- A compact toolbar holds the design name, Empty/Proposed/Applied/Saved status, full Undo, explicit Save and Technical details. Advanced Builder appears as an optional saved-design link; Save keeps the user here.
- The central canvas has a stable height, readable labels and an explicit proposed/current preview switch. Undo restores the empty applied canvas immediately while preserving its reviewable proposal and direct Apply action.
- One adjacent proposal presents the changes, important settings and connection, with one explicit Apply control. The assistant scrolls independently; the composer remains accessible. Disconnected fixtures advertise no arbitrary suggested prompts.
- Selecting a node opens declared purpose and read-only settings over the canvas. Escape/Close returns to the same workspace. IDs, pins, schemas and tool diagnostics are behind Technical details; errors and unresolved required inputs stay visible. Verified upstream requirements are not presented as missing inputs.
- Narrow screens switch between Library, Workflow and Assistant rather than compressing columns. Arrow/Home/End navigation works; the chosen area and unsent prompt survive switching and reload. A viewport-only adapter refits the graph after resize/reappearance without graph setters or Save callbacks.

The visible notice remains **“Prepared synthetic proposal. No live AI or execution.”** Saving does not imply runtime readiness. Catalogue-composed execution stays unavailable. Authentication, ownership, source provenance, contracts, revisions and all API semantics are unchanged.

## Actual agent verification

The existing native port-23123 walkthrough, installed dependencies and same disposable host SQLite database were reused. There were no new ports, accounts, profiles, services, adapters, container stacks, dependency upgrades or image builds. The retained `.next` demonstration build and all prior profile/evidence files remain unchanged; compilation uses the existing isolated Next dev output.

The opt-in `prepare_workspace_review.py` harness helper generated one distinct server-issued synthetic recommendation via the normal authenticated discovery route and existing preparation-only provider double. An ignored local bootstrap restores the normal owner-bound conversation format; it has no mock controls and is not shipped as production behavior. Existing recommendation records were not replaced. No real provider request or arbitrary chat occurred.

New engineering draft: `a719a04c-a06f-57fb-9e41-9cac795d9534`; saved solution: `4ed856eb-8b95-46b4-a2cd-8ca8b82fe764`.

| Check | Actual result |
|---|---|
| UI regressions | **31 passed**, zero failures/skips: session/restoration, allowance, composition, review actions, compact rendering, state labels, readonly inspection, scoped suggestions and keyboard switching |
| TypeScript | Passed: `tsc --noEmit --incremental false -p apps/web/tsconfig.json` |
| Real application flow | Explicit Create → Apply → Undo → Apply → Save/reload, optional Builder and return checked in the browser on the new engineering copy |
| Final Undo presentation | Additional Apply/Undo cycle verified immediate empty canvas with preserved proposal; final reapply/save at **revision 5**. No manual draft repair or restoration helper |
| Identity/configuration retention | Complete initial empty state restored; pending graph, applied graph and saved graph match exactly, including allocated IDs, count 3, pins and binding |
| View-only interactions | Complete API draft response unchanged after selection, purpose/settings/pin inspection, dialogs, zoom and Fit View |
| Desktop | 1440×900 browser viewport, unchanged zoom (`1`); library, central canvas, assistant, main actions and composer visible together; settled saved canvas approximately 602×628 CSS pixels |
| Narrow | 390×844 browser viewport, unchanged zoom; no horizontal document overflow; proposal Apply and composer within viewport; switching/reload retains unsent prompt and active area; settled nodes fully inside canvas after refit |
| Owner/history preservation | **551** protected file hashes match; both pre-existing drafts and both saved solutions retain identical complete rows |
| Execution/provider boundary | Zero real provider requests, deployments or execution submissions. Existing serving harness still blocks chat, readiness, submission and execution. Grants/ledger untouched; shared allowance remains 13/13 |
| Backend evidence | Existing PR #15's 192 focused backend checks reused: no `apps/api` source change. No unrelated complete inventory or new PostgreSQL concurrency claim |

Browser inspection caught and corrected clipped nodes after resizing: the final viewport adapter only refits on initial visibility/dimension changes, not normal selection or pan/zoom. Intermediate browser timing/locator errors and preliminary stale-frame captures remain in private evidence and are excluded from published screenshots. The final images were visually inspected after rendering settled. No browser zoom or image resizing was used to make the layout fit. Existing module warnings remain visible in local test logs.

## Comparable screenshots

Both desktop captures use the same configured 1440×900 browser viewport at normal zoom, with equivalent two-operation synthetic saved designs. The baseline capture opens the retained agent copy read-only; the after capture uses the new engineering copy. Native capture includes the baseline's scrolling page and scrollbar; the unedited raster dimensions are recorded in the machine evidence. Narrow capture is separate. These are agent technical evidence, not participant observations.

| Before | After |
|---|---|
| [Baseline workspace](screenshots/workspace-before-desktop-20261110.jpg) | [Redesigned workspace](screenshots/workspace-after-desktop-20261110.jpg) |

[Narrow workflow](screenshots/workspace-after-narrow-20261110.jpg) · [Sanitized exact-source evidence](DESIGN_AI_WORKSPACE_EVIDENCE_2026-11-10.json).

## Owner review — three steps

1. Open the [existing saved owner workflow](http://127.0.0.1:23123/design-ai?draftId=49ce7803-1e55-51ac-b47b-94b8731a913c), signing in with the retained human walkthrough account if needed. The original private credential file is unchanged; no password is reproduced here.
2. Select either node, inspect purpose/settings (generator count 3), then close the view. Check the assistant/prompt remain accessible; on a narrow window use Workflow/Assistant switching. No replay of the completed copy is needed.
3. Report whether the layout, proposal and controls are now understandable and identify any remaining confusing wording or placement. New owner usability feedback is pending; no independent participant result is invented.

AIE-18 is unchanged and remains In Review. Broader composition, real-provider interpretation, independent usability and production compatibility remain unverified. No Docker recovery, staging, production, workflow execution, grant/allowance/ledger change, merge or tracker update occurred.
