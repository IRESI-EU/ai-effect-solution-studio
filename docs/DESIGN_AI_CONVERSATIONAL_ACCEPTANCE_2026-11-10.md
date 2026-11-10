# Conversational two-service creation — integration review

> Later 10 November availability/catalogue follow-up is appended below. Normal catalogue reads are now restored, and current PR #17 source validates one real registered pair. The retained serving image still predates discovery/composition. Original results and the earlier blocked observation remain historical.

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

## Later 10 November — normal catalogue recovery and real pair inspection

This is a separate **read-only catalogue/source inspection**, starting from PR #17 **791aa438a1215ac29b59e6cb6a6f068246bfa061**. It is not provider acceptance, a controls replay, a new qualification or an execution. No implementation change or new draft PR was required.

### Demonstrated cause and selective recovery

Docker Desktop/daemon responded normally. The retained API and its PostgreSQL dependency were **stopped**, not running with a slow query. Direct port **28185** refused connections (WinError 10061); the native port-23121 web process remained running. Its request log reported **ECONNREFUSED 127.0.0.1:28185**, matching the documented rewrite target and retained API port mapping. Thus the proxy target was correct. The earlier two-second client timeout was an incomplete availability observation, not proof of an application/database request timeout.

Retained PostgreSQL logs showed ready-to-accept-connections followed by a previous fast shutdown. A previous readiness diagnostic had used nonexistent role postgres; restoration used the documented **aie37** role/database. No database corruption or current startup failure was observed.

Restored with bounded **docker --context desktop-linux start <existing-full-ID>**, database first, then API after **pg_isready -U aie37 -d design_aie37_qualification** succeeded:

| Component | Retained identity | Retained image |
|---|---|---|
| ai-effect-aie37-postgres-1 | 9ab6a3495af7ed408795440ca15a805d397d752012327f445b3dd2bd09abde27 | sha256:5d143123fdf80462d1778cd4f24b9f7ca13c87174bca19141fb194c5a1ebca59 |
| ai-effect-aie37-api-1 | 5e5481f227157f367f1ba8878e63d564660bbe919f80e791f323513e2c89807e | sha256:993302f295ac9feb511b448ea9730bf9aa6b64312841b43ac82b9a880a00cce8, ai-effect-aie37-api:goal-results-v1 |

No recreation, pull, build, configuration edit or volume operation occurred. The existing broad Restore-RecordedServices.ps1 was inspected but **not run**: it would start ten unrelated retained services, including workers, outside this task. Only the two required retained containers changed from exited to running. All **41** container image identities matched the preservation record; all other container states were unchanged. Runtimes, workers, orchestrator and Redis were not started.

After restoration, direct API config, proxied **http://127.0.0.1:23121/api/design-ai/config**, and **http://127.0.0.1:23121/login** returned **HTTP 200**. The unchanged **aie37-designer** account signed in through the normal web auth route, retained active solution_designer authorization, and read the normal /services and operation-contract routes. No password or environment content was printed.

### Serving-source gap — distinct from availability

The restored API image is the preserved pre-PR14 goal/results build. Read-only container inspection found **no app/services/catalogue_discovery.py or catalogue_composition.py**. Its routers/design_ai.py SHA-256 is **fdddbedaa9d9db27231800d58798159e13934b5bdadee11328eb22dc806e1116**. The retained native web build is also the historical demonstration build, not the PR #17 workspace.

**Catalogue access is restored; new pair advertisement in the currently served normal chat is not established and cannot be supplied by that old API image.** The old image was preserved rather than modified or rebuilt under this task. The healthy synthetic port-23123 profile was not substituted.

To complete useful source inspection without another service, the exact PR #17 **normal private MCP discovery tool** was invoked against the same retained PostgreSQL data, under the same normally authenticated designer ID and enforced **transaction_read_only=on**, with autoflush disabled. Only discovery/list tools were invoked. The inspection process had provider/grant/ledger configuration empty and did not import/start the HTTP application. This was an actual registry read using normal source authorization/validation, not an installed API route, test-provider response or synthetic catalogue.

The process set its own DESIGN_AI_TEMPLATES={} solely to inspect operation pairs independently of the legacy registration. It did not change the serving environment. The legacy registered-workflow projection/full production provider context was not evaluated in that process; pair eligibility/fingerprint does not depend on that policy. The tool returned exactly **one operation pair**, with no pair/catalogue truncation. A separate read-only pure compiler validation accepted seed 43 and its exact binding. No draft, saved design, recommendation nonce or workflow was created.

### Verified real registry pair

Both services are visible to the active designer, approved/active, owned by **NL**, and registered as **native / control**, with **adapter_type=null**. Both active contracts have schema version 1.0, contract version **1.0.0**, and manual provenance; created_by_user_id is null. This records existing authority as accepted by the application. It is not newly manufactured node-owner attestation.

| Step | Service / operation | Operation identity | Active contract pin |
|---|---|---|---|
| Generate synthetic power grid | aie37-synth / ConfigureAndSynthesize | urn:aieffect:nl:configure-and-synthesize:capture | 921a87fc-329f-42b6-a546-ddf7d9c0ec26 @ 1.0.0 |
| Benchmark generated grid | aie37-benchmark / RunBenchmark | urn:aieffect:nl:run-benchmark:capture | 441153b2-9b3b-48c1-81e4-649645f30143 @ 1.0.0 |

**Inputs/settings:** generator has no external data input. Its integer seed accepts **42 or 43**, registry default **42**; the proposed positive case explicitly selects **43**. Benchmark has no declared configurable settings and requires the upstream captured_grid input; that requirement is satisfied by this connection. No unresolved required setting remains.

**Exact connection:** source output **captured_grid** → benchmark input **captured_grid**, transport **whole-output-v1**, semantic concept **urn:aieffect:nl:synthetic-grid-capture**, schema **urn:aieffect:nl:dutch-local-capture-v1:grid**, representation **data_reference**, protocol **file**, content type **application/json**, cardinality **1..1** on both sides. These are active contract declarations checked by the existing binding validator, not inferred from matching names or JSON alone.

- Candidate: **pair-a5c5793a07b3017820d63c7a**
- Authority revision: **26add1b21313352f06577e801fb4178c012cd3b4ed7f3d0505d5e7401a10a0db**
- Schema fingerprint: **ba3e279298a6ead4581484ccfbcef4061182d9c9b35601c8197c9384e576ad80**
- Effective case settings: first={seed:43}; second={}

**Native design compatibility versus runtime:** the actual registry fields and source/analyzer contracts meet the native composition rule without adding an adapter type, transport or contract. The implementations remain the narrowly qualified Dutch capture wrappers; contract notes describe manifest/task/workflow association and historical capture validation. Earlier generic reasoning that “Dutch adapter qualification” necessarily excluded these registry records was not verified and must not replace these actual findings. Nothing here broadens the runtime adapter or certifies arbitrary grids.

Historical qualification applies to the pinned registered workflow and its existing captured run. A newly composed design **does not inherit that qualification or grant**, remains design-only, and must be blocked from execution. Runtimes remain stopped; current runtime availability, portability, scientific validity and production compatibility were not tested.

### Concrete next action and grounded acceptance — still locked

No service/contract change is required or justified for this pair under existing PR #17 rules. The remaining engineering/operational prerequisite is a **separately authorized source-parity packaging/update of the normal API and web to the reviewed PR #17 source**, within the same retained local profile/ports. Preserve the current image and historical web build for rollback, retain database/mounts/credentials, leave workers/runtimes stopped, and keep provider/grants disabled. Do not relabel an old image as current or inject source into a running container. No such build or replacement was performed here.

After that scoped update, verify the **served normal** discovery path, including its actual registered-workflow policy/context, advertises the same pair and authority revision for the same designer. Drift, disappearance or a registered-workflow-only response stops acceptance preparation. Record new build/image/source identities before seeking spending approval.

The earlier two exact proposed messages can now be grounded in the actual pair above:

1. **“Create a new two-step design that generates a sample electricity grid using seed 43 and benchmarks that same grid. Do not copy a registered or saved workflow.”** Expected selection: only pair-a5c5793a07b3017820d63c7a, exact pins/revision above, first seed 43, no benchmark parameters, and the captured_grid binding. Chat creates/applies/saves nothing. Explicit subsequent controls may create a new owned design; no execution. A registered-workflow recommendation is not a composition pass.
2. **“Create a three-step workflow that forecasts demand, optimizes dispatch and controls live equipment.”** Expected clarification or no supported match; no recommendation authority or draft/solution mutation. The actual authorized two-service catalogue supplies none of these three capabilities. Do not answer clarification or simplify the request.

These remain **provisional pending serving-source parity and separately approved provider preflight**. No provider acceptance has occurred. The previously proposed maximum two attempts, gpt-6-luna/low/Standard, output ≤2,000 tokens, zero retries/fallback, US$0.005 each and US$0.010 aggregate remain a proposal only. Any future supported audited **13→15** amendment/new checkpoint requires separate approval; preserve the same US$0.10 ceiling and remaining funds. Do not reopen old checkpoints.

Final normal config confirms **request_count=13, max_calls=13, remaining_calls=0, outstanding_reservations=0, can_request=false**. Provider is unconfigured, execution grant empty, shared allowance mount read-only. No paid request, grant, workflow, saved-design edit, owner controls replay, synthetic demonstration, image build, Docker settings repair, production operation, merge or tracker update occurred. No unrelated test suites were rerun for these documentation findings.
