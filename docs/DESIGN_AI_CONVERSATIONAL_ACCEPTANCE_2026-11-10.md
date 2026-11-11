# Conversational two-service creation — integration review

> Later 10 November availability/catalogue follow-up is appended below. Normal catalogue reads are now restored, and current PR #17 source validates one real registered pair. The retained serving image still predates discovery/composition. Original results and the earlier blocked observation remain historical.

> Subsequent authorized packaging/update: source **1068cea** now serves both normal ports, and discovery passes under the actual unchanged Dutch policy. Browser verification found that the earlier claimed placeholder fix was incomplete: the helper is imported but unused. The failed wording check and unapplied one-line correction are recorded in the final section. No provider acceptance is claimed.

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

## Authorized normal-profile packaging/update of 1068cea

The owner subsequently authorized packaging and updating only the normal local web **23121** and API **28185** from **1068ceaa4bfd30d664b5cf475bc05ebe5e54d80e**. The source worktree was clean at that exact commit before packaging. No application source change was included. Report-only publication afterward does not change the served application identity.

### Recovery point and build inputs

Private recovery directory under the original checkout: **local-backups/normal-composition-update-20261110/**. It contains:

- **before.json**, private retained/candidate container inspections and configuration references; original API image **sha256:993302f295ac9feb511b448ea9730bf9aa6b64312841b43ac82b9a880a00cce8**, historical native web build **_9OUF0yBLv4pKPA0e0pex**, unchanged database container **9ab6a3495af7ed408795440ca15a805d397d752012327f445b3dd2bd09abde27**, volume **ai-effect-aie37_aie37-db**, database **design_aie37_qualification**, role **aie37**.
- **design_aie37_qualification-before.dump**, a consistent **pg_dump -U aie37 -d design_aie37_qualification -Fc** snapshot, **39,470 bytes**. SHA-256 and a successful **pg_restore --list** check are in **backup-verified.json**; user/solution table data are present. No restore-roundtrip rehearsal is claimed and the dump was not restored over any retained database.
- **Rollback-API.ps1** verifies the retained historical image then recreates only API from the original base/demo Compose files plus rollback.compose.json, with **--no-deps --no-build --pull never**. It does not restore data or start workers.
- **Start-NormalWeb.ps1 -Rollback** verifies the retained historical BUILD_ID, checks the exact recorded normal-port process, and starts that retained build detached with local logs. No new web compilation is needed for rollback. The original .next build remains in local-backups/design-ai-demo-portal/apps/web.

Read-only model/schema inspection found all current model columns and types already present. Models/migrations are unchanged since the earlier candidate baseline; **no migration was necessary or run**. Engineering data was hashed before replacement for comparison afterward. Normal login/session/audit metadata is separately excluded.

API context was a **727,040-byte source-only archive** of the committed apps/api/app tree plus the local packaging Dockerfile. Its dependency base is the positively identified historical API image above; the derived image adds only the current app source/labels, with the retained dependency layer chain verified. Docker used **linux/amd64, --pull=false, --network=none**. No pip install, dependency upgrade or base-image pull occurred.

Web package is a minimal Git export of apps/web, the package/workspace/lock files and four tracked JSON examples imported by the existing publish route. It links installed dependencies instead of copying them. No private configuration, profile, credentials, captures, historical builds or untracked synthetic bootstrap HTML entered either context. **3,178** output-trace references were checked with zero references to protected runtime/profile/credential paths.

Host inputs: **Node v24.15.0, Next 16.3.8**, existing installed dependency versions, pnpm-lock SHA-256 **c666d9d7d02bbe06d7b4b195a99a55e90cdd6292d663544f94780d84bea34974**. C: free space was **25.31 GiB** before packaging and **24.73 GiB** after cutover.

Intermediate failures are retained in private logs: sandbox compiler-worker EPERM; Docker plain-PAX stdin detection; initially omitted tracked workshop JSON imports; and a Windows trace-read failure. The trace failure was specifically **semver@7.8.5/preload.js**, an unreadable **83-byte OneDrive placeholder**. The exact **29,399-byte semver-7.8.5.tgz** archive was fetched from the official npm registry and verified against the existing lock's SHA-512 before recovering that one file. The original unreadable object remains preserved privately; dependency version and expected code did not change. No broad dependency hydration/reinstall or unrelated cleanup occurred. Final build ran without diagnostic hooks, skipped checks or tracing exclusions.

### Actual served identities and update

| Component | Actual served identity |
|---|---|
| API source | **1068ceaa4bfd30d664b5cf475bc05ebe5e54d80e**; all **72** app-file hashes match committed source |
| API image | **ai-effect-local-api:conversation-1068ceaa4bfd** / **sha256:076b83f6fe526682c78b103343fd7006e5d008a0a9337dd62e3e9f0ca8b6a3cf** |
| API container | **a30d8c5f1b31b2a92cbb285e6b2e21a452737eef900121d5faad4ce0ff827e22** |
| Web source | **1068ceaa4bfd30d664b5cf475bc05ebe5e54d80e**; **77** exported web/example files match exactly, with zero source differences |
| Web build | **ZwPsznKFUeJqsX_w16oos**, native Next production build; Design with AI bundle SHA-256 **5c8f0881efade0b1582b437fcbe2e02c3a96b5264c51c1a33aad4285986e6ee0** |
| Web runtime | Detached native node PID **36272**, IPv4 loopback **127.0.0.1:23121**; source package **local-backups/normal-composition-update-20261110/web-source/apps/web**, logs **web-normal.stdout.log / web-normal.stderr.log** |

API replacement used only the documented base/demo Compose configuration plus the candidate image override and **up -d --no-deps --no-build --pull never api**. Every environment value, port and all seven read-only mount targets/sources/modes were verified against the prior container. Docker Desktop canonicalized the same authorization directory from Windows notation to its /run/desktop/mnt/host/c path; this is not a different directory or permission. PostgreSQL was neither recreated nor migrated. No unrelated retained container was started. Old API image and old web build remain usable rollback inputs.

### Actual normal-policy discovery and preservation checks

The existing **aie37-designer** signed in through the normal application proxy and in the browser. Within the **served API container**, the installed normal private MCP discovery tool ran for that same authorized designer in an enforced **read-only transaction**, with its **actual unchanged template policy**. No policy clearing, chat request, provider double or prepared recommendation was used.

Outcome: **dutch** policy remains configured. **workflow-283fb89a71a310be07f72cbd** is still advertised as a separate registered workflow; it does **not** hide or replace **pair-a5c5793a07b3017820d63c7a**. The pair authority revision remains **26add1b21313352f06577e801fb4178c012cd3b4ed7f3d0505d5e7401a10a0db**.

| Pair pin / binding | Verified unchanged |
|---|---|
| aie37-synth / ConfigureAndSynthesize | **921a87fc-329f-42b6-a546-ddf7d9c0ec26 @ 1.0.0**, active |
| aie37-benchmark / RunBenchmark | **441153b2-9b3b-48c1-81e4-649645f30143 @ 1.0.0**, active |
| Settings | **first={seed:43}; second={}**, accepted by existing parameter validation and pure compiler |
| Connection | **captured_grid → captured_grid**, **whole-output-v1**, unchanged exact semantic/schema/protocol/content type/1..1 rules and fingerprint **ba3e279298a6ead4581484ccfbcef4061182d9c9b35601c8197c9384e576ad80** |

Both normal catalogue/contract HTTP reads and saved solution **ef10cde8-15d4-4f6d-82dd-0525a16de4fd** are accessible. Existing workflow **wf-1b6eb7caaf57** remains completed with recorded seed **43**, both tasks completed and available qualified evidence, using its **recorded terminal observation**, without starting a runtime. All four authorized downloads match their recorded SHA-256 and byte counts (configuration 1,441; grid 148,660; network 129,851; benchmark 855). This is historical inspection, not a new live execution.

**Preservation:** all **nine engineering-table hashes** match before/after; user credentials/roles/permissions are unchanged apart from ordinary login timestamps. Both ledger file hashes match. Database container/volume identity is unchanged. All **41** retained-profile containers remain represented (only the authorized API container was replaced); other container IDs/states are unchanged. All **551** previously protected file hashes and six recorded prior fixture draft/solution rows match, including the completed owner design. The separate synthetic walkthrough on **23123** was not rebuilt, restarted, replayed or reconfigured.

Normal API/web pages and proxy return 200. Synthetic bootstrap URLs on normal port 23121 return **404**. Provider remains **unconfigured**, grant empty, ledger mounts read-only, count **13/13**, zero outstanding reservations. No chat, recommendation nonce, design creation/mutation, checkpoint, provider call, workflow, production/staging change, merge or tracker operation occurred.

### Failed browser wording check — correction required before full handoff acceptance

The actual browser displays the updated library/canvas/assistant workspace and **AI messages paused**, with Send disabled. However its composer placeholder still says **Prepared walkthrough · chat unavailable** in this genuine normal profile.

**Cause:** approved source 1068cea imports the tested promptPlaceholder helper but the textarea still uses the old hard-coded conditional. Earlier reports claiming this wording was corrected were inaccurate. Helper-only unit tests did not verify its connection to the actual page. This failed observation is retained in [actual normal browser evidence](screenshots/normal-composition-1068cea-browser.jpg); it is not reported as a pass.

The exact **unapplied** one-line correction is prepared as [review patch](patches/normal-placeholder-wiring-1068cea.patch):

```tsx
placeholder={promptPlaceholder(config.provider_mode==="test",chatEnabled,allowancePaused)}
```

It replaces the hard-coded textarea placeholder in apps/web/app/design-ai/page.tsx. It was **not applied** to the shared review checkout or normal source package: this task authorized serving exact 1068cea, and changing the shared page would also recompile the separately protected 23123 dev walkthrough. No served-code change beyond the authorized commit was silently introduced.

**Provider boundary:** genuine discovery/context/pins/settings prerequisites now pass, but the requested complete browser wording check does not. The two already grounded provider cases remain locked and **are not reported ready for spending approval**. Next change is to review the one-line wiring correction, verify the actual normal page under disconnected/exhausted conditions, and package an authorized corrected web source while preserving the synthetic walkthrough. No ledger amendment or paid request should be used to diagnose this display defect.

Normal owner URL: **http://127.0.0.1:23121/design-ai**. Sign in as **aie37-designer@example.test**, reading the unchanged password privately from **local-backups/aie37-profile-20261028/reviewer.json** under the original checkout. The browser is left signed in on that normal workspace. Do not replay the owner's completed synthetic copy or submit chat.


## Restricted live beta follow-up — NOT LIVE (10–11 November 2026)

This record supplements all earlier results. The original failed normal-browser placeholder observation and screenshot remain intact. The maintained textarea now calls promptPlaceholder; a regression renders the **actual page** in disconnected, allowance-paused and synthetic configurations, checks the helper arguments, rendered placeholder and disabled Send, and forbids network access. These are agent checks, not owner or independent usability observations. The retained normal port-23121 build was not silently replaced by this candidate.

**Candidate source:** 4ff3285bdaf6cd0951b946b1d1667212b197e74d (implementation 21320aa, packaging e732f6d, fail-closed accounting guard 4ff3285). The later evidence-only commit does not change application/build source. Both local **linux/amd64** images built successfully without pulls, downloads, service starts or dependency upgrades:

| Component | Candidate image identity |
|---|---|
| API | sha256:da0a7a87a9cebb479f6458491621cdd6856a2b45f2c5481dc1c999145e22823d |
| Web | sha256:fba983fef01d461e79db22444c34c76b9737df84365d200972085672a4052614 |

Web BUILD_ID **XLX_batDPkRXN0X7avzOq**. Read-only, network-disabled utility containers verified all 65 exported API Python files and 74 web files against the committed-source manifest. Synthetic bootstrap HTML and the staging seed script are absent. Only installed dependencies were copied from retained content-addressed images; their source/application/configuration was not inherited. Python 3.12.14 / Node 24.15.0 base digests, dependency image IDs, lock validation and the source-only context hash are recorded in [machine evidence](DESIGN_AI_RESTRICTED_BETA_2026-11-10.json). Reproduce with deploy/restricted-beta/build_candidate.py --records <new-private-record-directory>; it refuses dirty source, changed dependency tags and overwriting existing image tags. The historical builds, images and profiles remain retained.

### Actual production baseline and release gates

Retained authorized SSH access succeeded to the server serving the public hostname. This is the existing Traefik/server deployment, not a Vercel Preview. HTTPS homepage, proxied health and public catalogue respond 200. Running identities:

| Component | Actual served identity |
|---|---|
| API | 89072340c9a13f3aa49d3e433380de8928cc16dd; image sha256:ded4f325be3769f834f5a40b1e3cf7f85aef0e0d25126b51d9509892cd562340 |
| Web | df5b75873326ab56cad608990f3bd4add125bcc4; image sha256:851115fb98582c8c077ed28e3b6db46c40a1079467cb4e3a11faabf5c19f2a0f |
| Web build | aLp4c1xkUjCM1v23PtrYY |
| Database | solution_studio, PostgreSQL 16.15; 37 services, 46 solutions, 54 deployments, 31 users |

All 44 served Python source files and 32 served web source files examined match those Git revisions. This records the source files and the actual build identity; it does not assert that an older source tag alone proves a reproducible bundle. Authentication/ownership columns already exist in production; the previous historical claim that production lacked all authentication is not the current baseline. Cumulative differences still include 42 API and 46 web files, plus additive migrations 003–005. Secure cookies are enabled. The web uses its retained internal API target, API/database ports are private, web binds server loopback behind Traefik, and existing artifact/contract volumes remain mounted with their retained identities. No Clerk or infrastructure migration was introduced.

One HTTPS login attempt using the existing private temporary credential record returned **401**. It was not retried, reset or replaced. No owner/reviewer account was activated or inferred from a local test account, role, email similarity or stored session. Existing identities, permissions and passwords remain unchanged. A failed-login audit entry may be recorded normally. The private credential record is under the original checkout at local-secrets/production-admin-credentials.txt; it is **not currently verified usable** and must not be copied into a deployment.

PRs **#8–#17 are drafts with zero submitted reviews** at inspection. Main reports no branch protection and the repository lists no rulesets; that absence is not approval or permission to self-approve. The queried prior head's Vercel status/Preview Comments passed; those checks do not verify this server, migrations, restricted access or genuine AI. No stack PR was merged and no check requirement was modified. Final pushed-head checks must be assessed separately.

### Real catalogue: no eligible production pair

The normal public catalogue advertises two approved/active Dutch families:

| Generator / ConfigureAndSynthesize | Benchmark / RunBenchmark |
|---|---|
| pkg-data-synthesizer1-afa8ed26ac | pkg-benchmarking1-cef41fb569 |
| svc-imported-grid-synth-service-configureandsynthesize | svc-imported-benchmark-runner-runbenchmark |

All four normal operation-contract endpoints return 200 with **zero active contracts**. The live database has **zero operation-contract records in total**, independently confirmed by read-only SQL and both backup restores. Similar operation names and legacy input/output labels do not establish native compatibility. No production pair ID, seed-43 accepted-settings proof, contract/version pins or validated whole-output binding exists. The local pair-a5c5793a07b3017820d63c7a and its capture-profile pins are not production authority and were not copied or substituted.

**Immediate owner action:** have the Dutch service owner select the authoritative service family and provide reviewed, versioned contracts for those actual deployed operations. Required evidence is the precise accepted seed/settings schema (including whether 43 is valid), all required inputs, output/input slot semantics and schema/version fingerprints, representation/protocol/content type/cardinality, provenance and exact whole-output connection. Publish/activate only through normal owner-authorized contract governance after verification. Do not invent a 1.0.0 version or assume captured_grid exists in these services. If the upstream output is not accepted whole by the benchmark, an explicitly reviewed service/adapter change is required; this report does not declare that change implemented or portable. Runtime/scientific qualification is separate and remains unverified for new composition.

### Focused security corrections and checks

Restricted mode now uses exact **existing user IDs** on every Design with AI route, including config and the execution-review routes sharing pilot_user. An empty list fails closed; active-role checks remain authoritative and administrators have no allowlist bypass. The feature remains off in current production. No production reviewer IDs or provider key were configured.

Generic preview now requires an authorized, non-legacy-owned deployment; an integrity-checked **server-recorded submitted execution** with matching workflow/owner/solution; an exact task from the same observed workflow; and the task's recorded output reference. File resolution must retain the workflow namespace after traversal/symlink resolution. Directory children must remain inside a verified owned output directory. Unknown legacy associations and unqualified remote preview transports return a truthful unavailable/conflict response. Arbitrary remote fetches are blocked. The browser supplies workflow identity. Existing protected qualified-capture downloads are unchanged.

The review also found that POST /deployments could previously claim an otherwise unregistered runtime workflow ID. New registrations now require matching server-recorded submission authority and snapshot integrity; existing authorized records are preserved. An arbitrary client workflow ID cannot establish ownership. No legacy owner was guessed or backfilled. These repairs are **candidate source only**, not a claim that the live route has been repaired already.

Checks: **94 focused backend tests** passed on the composition/preview/restriction/evidence source before the final provider-only guard; **20 restricted-mode/provider-adapter tests** then passed on the final source. The latter reruns overlapping restricted tests and adds the fail-closed cases; these counts are not summed as independent inventories. **14 frontend tests**, host typecheck and Linux Next production build passed; cached web steps were reused for the final API-only guard because web/build source was byte-identical. Deprecation warnings remain visible. An initial sandbox temporary-directory permission failure is retained; the permitted host runs passed. No complete unrelated inventory was repeated. Historical failures/results remain in their earlier records.

A fresh **86,227-byte PostgreSQL custom backup**, SHA-256 b5d862f4d99c57d3e4532166cc171a57b053f8eb439a8a90be2d0c5915b59764, restored independently into two newly allocated local databases. All five reviewed migrations were applied twice on one restore. Existing rows were preserved except the declared Netherlands-to-Dutch normalization, if present; new tables/design_metadata were additive. The second restore exactly reproduced the original backup rows. Both temporary databases were removed. Production was not migrated; no local qualification data/accounts/captures entered production. These checks do not establish successful existing-owner login, complete production-compatible browser controls or PostgreSQL pair concurrency.

### Spending and activation boundary

**Both genuine-provider cases: NOT RUN.** Catalogue prerequisites failed before spending. No 13→15 amendment, new checkpoint, beta policy, execution grant, model request or workflow occurred. The locked exact two messages and expected outcomes in the earlier report remain unchanged.

Read-only ledger inspection: **13/13**, US$0.10 ceiling, accounted conservative usage **US$0.004207375**, conservative monetary remainder **US$0.095792625**, **zero outstanding reservations**, 26,575 input / 1,771 output tokens across prior requests. This task used **0 calls / US$0**. These are durable ledger accounting figures, not a newly verified provider invoice. The ledger SHA-256 remains c5d34d33914623978335c02471f635239b1fae29bee6fcf2f77411e930a8477f. No funds or usage were reset.

Current accounting supports only the earlier exact audited amendments/local database guards and checkpoints capped at three calls. It does **not** yet support the requested 13→15 amendment followed by ten beta calls or one authoritative ledger across this Windows profile and the live server. No ledger was copied/forked, mounted into production, enlarged or hand-edited. That narrow durable operator/accounting work remains a release prerequisite. Restricted mode now explicitly prevents an unbudgeted provider fallback if either accounting control is absent; the existing database-identity guard also continues to reject unsupported deployment scopes. No guard was relaxed to treat production as the local qualification database.

Remain disabled: DESIGN_AI_ENABLED=false; for any later reviewed beta configuration use DESIGN_AI_RESTRICTED_BETA=true and exact established reviewer IDs, with keys server-side. Do not turn these on until current production login, owner-approved real contracts, cumulative reviews, complete isolated controls checks, audited shared accounting and genuine acceptance all pass. Paid acceptance pricing/context checks were not represented as passed after the catalogue stop.

Private rollback/recovery evidence is under the original checkout at **local-backups/restricted-beta-release-20261110/**: production-before.custom, backup identity, private production inventory/source/auth response records, source comparison, rehearsal report, both build logs/manifests and image verification. The live API/web images and release directories are still running; **no production rollback is necessary because no deployment occurred**. For a later application rollback retain those exact authenticated image/configuration identities and additive history; never restore this older database over new user writes automatically. Retained local rollback remains under local-backups/normal-composition-update-20261110/.

**Target only, not a launched beta:** https://platform.ai-effect.eu/design-ai. No beta reviewer access has been enabled. After the gates pass, the owner checklist is: (1) sign in with the existing approved account and review both grounded steps/settings/connection; (2) explicitly Create → Apply → Undo → Apply → Save/reopen; (3) request the unsupported three-step case and confirm clarification/no-match with no mutation or execution. No independent usability or production compatibility pass is claimed. No tracker changes, production deployment, merge, new account/permission, provider call or execution was performed.


## 11 November follow-up: contract source investigation and shared accounting preparation

The [separately identified engineering record](DESIGN_AI_BETA_ENGINEERING_2026-11-11.md) and [machine evidence](DESIGN_AI_BETA_ENGINEERING_2026-11-11.json) append new source-backed Dutch contract drafts and inactive shared-accounting support. Application source is **7165a398c1583daae567fb5cf48aabf35fe32a7b**; 111 focused accounting/provider regressions pass and the API candidate builds from retained pinned inputs. Web source is unchanged and its verified image is reused. No earlier result or failed observation above is replaced.

The earlier missing-accounting implementation is now prepared and tested: one authority over the original ledger, exact audited 13-to-15 then 15-to-25 transitions, separate two/ten-permit phase caps, durable uncertainty/receipt handling and no environment-local allowance fallback. No transition or service was activated. Private cross-environment transport remains an isolated release prerequisite.

The deployed Dutch source exposes concrete gaps: inline seed configuration does not establish consumption of composer http-parameters-v1 settings; GetGridData returns a process-wide latest cache rather than an immutable task-specific grid. The imported family is the strongest owner-review starting point; the duplicate package family has empty protobuf messages and unresolved image/source provenance. Four 0.1.0-draft.1 contracts remain unconfirmed and cannot advertise compatibility. Exact missing owner artifacts and the smallest service changes are listed in the contract dossier.

Normal production sign-in, Dutch-owner confirmation, required partner changes, cumulative code review and isolated accounting transport qualification remain gates. Genuine cases A/B and all original expectations remain unchanged and **NOT RUN**. Shared ledger bytes remain identical, **13/13**, USD0.10 ceiling, USD0.004207375 conservative held usage, USD0.095792625 remainder, zero outstanding reservations; new usage **0 calls / USD0**. No credential retry, deployment, provider call, workflow, new grant, profile, permission, merge or tracker change occurred.
