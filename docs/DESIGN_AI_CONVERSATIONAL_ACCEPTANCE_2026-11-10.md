# Conversational two-service creation — integration review

Implementation and serving source: **76a4d72a284916a3279d61a0754d62123e99a864**. Focused draft stacked on verified PR #16 **d8e6e3b269da0d3a6f936cb7e8349c719a9049fe**, whose base is PR #15 **5d9c398cad1a0944f3fe61edc1da90a832341e11**, on PR #14 **f36f8fdfcfb95576d948fea2971907ad4d433e3a**. Existing PRs are unchanged.

## What already works, and the focused changes

The normal application already implements the requested bounded conversation. This review reused it rather than adding another composer:

| Boundary | Authoritative implementation / behavior |
|---|---|
| Authorized discovery | Private MCP discovery tool → catalogue_discovery.projection; existing actor, visibility, approval, lifecycle and contract checks |
| Provider selection | Existing SYSTEM prompt and strict AssistantTurn/DiscoveryDecision schemas; choose an advertised pair ID and bounded typed settings, clarify, or return no supported match |
| Recommendation | selected rechecks actor and catalogue after the provider wait; catalogue_composition.recommendation validates settings/defaults and returns both purposes, connection and effective settings. Missing required values must clarify; a fabricated or invalid response fails unchanged |
| Create | Separate POST /design-ai/drafts; locks/revalidates authority; allocates a new owned empty draft and pending proposal without copying a saved template. Identical nonce reuse is idempotent; altered reuse fails |
| Apply / Undo | Explicit revision/proposal-bound actions; full prior design is restored by Undo, with the original proposal and allocated IDs available directly for reapply |
| Save / reopen | Explicit Save preserves engineering graph, settings, contract pins and named-slot binding; the workspace remains Design with AI. Advanced Builder is optional |
| Execution | Unqualified catalogue-composed provenance is preserved and rejected before runtime preflight/submission. No execution grant is inherited |

No backend production behavior needed rebuilding or changing. The actual presentation defect found was that an ordinary disconnected/exhausted provider displayed a **Prepared walkthrough** placeholder. The new helper distinguishes synthetic, disconnected, paused and enabled states. There is no new provider fallback or interpretation logic.

The PR #16 layout remains. Assistant messages/prompt are now 14px, proposal titles 14px and purpose/connection text 13px. The desktop assistant is 360px and grows to a bounded 400–480px on wide screens, keeping the canvas dominant. Technical JSON stays collapsed. Existing persistent restrictions, errors and controls remain; no additional notice stack or lifecycle redesign was introduced.

## Previously owner-confirmed observations — preserved

Owner draft **49ce7803-1e55-51ac-b47b-94b8731a913c** and solution **f6f86d6f-107a-46b4-8ce1-000b06405473** are unchanged. Count 3, refresh preservation, full empty Undo and reapply/Save remain owner-confirmed controls observations. Purpose/controls were only **PARTLY** understandable. The owner walkthrough was not replayed, and no new owner or independent participant observations are claimed.

## Actual catalogue findings and blocker

The recorded normal local API is **127.0.0.1:28185**. Its bounded availability check timed out. The existing normal web application's **port-23121 /api/design-ai/config** returned **HTTP 500**. This is an API/proxy availability blocker, not evidence of an empty catalogue or absence of real compatible services. No Docker repair/restart, credential reset or alternative profile was attempted.

Consequently, **no current authorized real operation pair was established in this milestone**. Catalogue visibility, exact active-contract compatibility and runtime qualification cannot be claimed from the walkthrough.

Historical AIE-37 evidence identifies the real Dutch ConfigureAndSynthesize → RunBenchmark chain and its local adapter qualification. That qualification is not permission to advertise it as a new native whole-output composition: this milestone excludes adapters, and a registered workflow is a different creation path. Historical Danish GenerateTopology → RenderTopologies source describes another real chain, but the report records missing qualified slot/capture evidence and required input. Neither historical record proves a current authorized pair in the normal catalogue. No contract was invented or service onboarded to make acceptance possible.

The healthy **port-28187** API is explicitly the retained **synthetic** host walkthrough, with only its two OFFLINE observation services. Its provider is unconfigured; serving chat, outbound provider network, readiness, submission and execution remain denied. It cannot establish live catalogue findings or genuine interpretation.

## New offline agent verification

Same profile, SQLite database, accounts, installed dependencies, ports and processes were reused. The existing opt-in preparation helper now accepts a distinct named conversation engineering review, refuses overwrite/reset, and emits one new server-issued fixture recommendation through normal authenticated discovery with the existing bounded provider double. It adds no serving chat capability or production import.

New disposable engineering draft **560f381c-b04c-505f-a9dc-0cabbbe48f41**, saved solution **ca93949c-86cd-42d3-ba82-b4b4616914f9**. Actual browser sequence: Create revision 0 → Apply 1 → Undo 2 → Apply 3 → Save/refresh 3. Undo restored the entire empty design and left Apply immediately usable; no repair helper or operator intervention was used. Read-only API snapshots establish equality of proposed/applied/reapplied/saved graph including count 3, IDs, pins and binding.

| Check | Actual result |
|---|---|
| Focused backend composition/discovery | **92 passed**, 737 existing deprecation warnings, 59.45s. Includes compatible recommendation, required-value/ambiguous clarification, no match, unauthorized/withdrawn/changed authority, duplicate nonce/actions, stale revisions/Save, ownership and execution denial |
| New backend regressions | Clarification and no-match discovery preserve another pending draft exactly; withdrawn contract rejects Apply without changing stored proposal/revision |
| UI checks | **35 passed**, zero failures/skips; session/restoration, composition requests, allowance, journey/Builder and static proposal rendering plus disconnected/paused/fixture wording |
| TypeScript | Passed: installed tsc --noEmit --incremental false -p apps/web/tsconfig.json |
| Actual browser | Normal Create/Apply/Undo/reapply/Save/reload; no automatic chat mutation; saved page remains Design with AI; optional Advanced Builder link present |
| Wide desktop | 1920×1080 at zoom 1; assistant 480px, canvas approximately 912×808px; message text 14px; no document overflow; technical details collapsed |
| Narrow | 390×844 at zoom 1; Workflow/Assistant tabs usable, both nodes fully inside 368.8px canvas; no horizontal overflow |
| Preservation | All **551 protected hashes** match. All three pre-existing draft rows and three pre-existing saved-solution rows are byte-for-value identical |
| Spending/execution | Zero actual provider calls, workflows or grants; ledger unchanged at **13/13**. Historical builds/evidence, accounts and profiles preserved |

The first sandboxed backend attempt encountered Windows temporary-directory permission errors during fixture setup/cleanup. Its failed log is preserved; the exact two-file suite then passed with permitted host access and a separate test-only temporary directory. No application assertion was waived. These are SQLite/provider-double checks, not PostgreSQL concurrency or real-provider interpretation.

[Wide desktop evidence](screenshots/conversation-review-desktop-1920-20261110.jpg) · [Narrow evidence](screenshots/conversation-review-narrow-390-20261110.jpg) · [Machine evidence](DESIGN_AI_CONVERSATIONAL_ACCEPTANCE_EVIDENCE_2026-11-10.json).

## Local review

One owner review URL: **http://127.0.0.1:23123/design-ai?draftId=49ce7803-1e55-51ac-b47b-94b8731a913c**.

The existing native Next dev process serves local-backups/design-ai-demo-portal, using the installed Webpack compiler and **.next-controls-20261106** output. Process command lines and rendered new text sizing were verified. The retained production .next build was not rebuilt or replaced. Source changes above are 76a4d72; later report-only commits do not change the serving implementation.

Sign in as **controls-human@example.test**. Read **human.password** privately from **local-backups/composition-browser-acceptance-20261106/profile/private-credentials.json** under the original checkout. Do not put passwords in chat, reports or screenshots. No credential/profile changes are needed.

Review the saved design and inspect a step/count or switch narrow tabs; do not repeat the completed owner's controls sequence. The separate agent draft can be inspected with the retained engineering account. No arbitrary chat messages can be interpreted by this fixture.

## Genuine provider acceptance proposal — LOCKED / not approval-ready

**Prerequisite still missing:** a current real authorized pair advertised by the normal discovery path. The positive case below is a concrete proposed domain request, not a verified supported request. It must not be sent, substituted with the synthetic observation pair, or counted as ready merely because the historical registered Dutch workflow exists. If the real catalogue cannot advertise this exact native pair with active compatible contracts and accepted settings, stop and return to the owner with a newly grounded proposal; do not silently change the case.

| Case / exact proposed message | Expected observable behavior once its preconditions are established |
|---|---|
| A: **“Create a new two-step design that generates a sample electricity grid using seed 43 and benchmarks that same grid. Do not copy a registered or saved workflow.”** | Only a currently advertised, authorized native generator → benchmark pair may be selected. Server validation unchanged; two purposes, seed 43 and same-grid reference connection shown; no draft/solution/run exists from chat. Explicit Create then Apply/Undo/reapply/Save/reload on a separate disposable copy preserves IDs/settings/pins/binding and stays in Design with AI. Execution unavailable. Current support is **unverified and blocked**, not a promised pass |
| B: **“Create a three-step workflow that forecasts demand, optimizes dispatch and controls live equipment.”** | No supported match, or a specific clarification, with no recommendation/Create authority, draft/solution mutation or execution. Do not answer clarification or simplify the request to force a pass |

Proposed future controls, **not enabled**: at most **two actual provider attempts total**, one per case, **gpt-6-luna / low reasoning / Standard processing / output ≤2,000 tokens**, zero retries, no fallback. Per-request reservation/spend ceiling **US$0.005**, aggregate **US$0.010**. This is a hard proposed cap, not an assertion of current pricing or sufficient remaining funds.

Only after catalogue access and pair/settings/contract pins are established, obtain separate owner approval for a supported audited shared-policy amendment **13 → 15 calls**, preserving the same ledger, all 13 records/checkpoints, remaining balance and **US$0.10** total monetary ceiling. Create a new two-call checkpoint capped at US$0.010; never reopen an exhausted one. Before approval/spending, verify genuine provider configuration, then-current approved pricing/context/token reservation, sufficient remaining shared money, zero outstanding reservations, shared 13/15 and new task 0/2, execution/network guards and unchanged fixture routing. Do not add funds or use a replacement/directly edited ledger.

Stop before spending on absent catalogue/authorization, no exact native pair, adapter/registered-only match, contract/settings drift, insufficient money, wrong provider/control limits or any outstanding reservation. During acceptance stop on clarification/refusal for A, invalid response, unexpected mutation, transport failure, uncertain attempt/accounting, stale authority or failed retention. A valid B clarification/no-match is terminal and is not answered. Preserve actual failures; never manually repair a response, retry or make a replacement request. Settle reservations normally, report actual tokens/costs/balances, and disconnect provider afterward. No execution grant or workflow is part of this proposal.

No policy amendment, checkpoint creation, provider connection or request was made here. The remaining catalogue blocker must be resolved before this proposal can become an approval-ready positive/negative pair.

Independent usability, broader composition, runtime and production compatibility remain unverified. AIE-18 stays In Review. No production/staging changes, dependency/image builds, merges or tracker updates.
