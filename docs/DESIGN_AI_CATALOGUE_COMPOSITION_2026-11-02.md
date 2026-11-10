# New two-operation catalogue designs

Bounded AIE-38 review milestone, stacked on PR #14 at `f36f8fdfcfb95576d948fea2971907ad4d433e3a`. Tested implementation: `6efa943b0ce4bd76f372815efc008f43460e823d`. This is a design milestone. It adds no execution qualification, runtime adapter or paid acceptance. Historical discovery, usability and live-acceptance reports remain unchanged.

## Before and after

Before: an authorized generator and analyzer could be recommended as catalogue capabilities, but creation required an existing registered workflow.

After: when their active contracts validate one supported connection, the server advertises a two-operation candidate. A labelled offline example proposes a synthetic observation generator with registry-default sample count 3, followed by its compatible observation analyzer. The user reviews both purposes, settings and the complete observation reference passed downstream, then explicitly creates a new design. No saved template is copied. The second synthetic image-family test follows the same generic logic; neither fixture establishes real service availability or scientific validity.

Registered Dutch creation retains its existing qualified journey. Catalogue-only matches without a supported pair still cannot create workflows. Broader composition remains incomplete.

## Supported boundary and authority

- Exactly two distinct processing operations, one linear named-slot `whole-output-v1` connection, and no required external input at the first step. The existing authoritative binding validator checks semantic/schema/version identity, representation, protocol/content type, cardinality and named slots. The existing parameter validator and pure compiler check the completed design. No readiness probe or submission runs.
- Operations must be approved/visible/active, native control services with unique supported active contracts and the existing compiler metadata. Adapters, branching, multiple slots, conversion and unsupported routing are excluded. Discovery considers at most 16 service records for pairing, advertises at most eight pairs within 12,000 JSON characters, and discloses truncation. The surrounding discovery projection retains its 24,000-character bound. This is not an exhaustive catalogue search.
- The provider selects only an advertised pair ID and two bounded lists of typed settings. The server supplies graph structure, instance IDs, contract pins and binding. Strict parsing rejects model graphs/endpoints/extra properties. String choices come from the registry; private/path/endpoint-bearing settings are excluded. Missing required values and ambiguous intent require specific clarification, without creating a draft. Invalid recommendations fail rather than being manually repaired.
- Explicit Create rechecks current actor/visibility/catalogue/contracts, locks current authority, validates supplied/default settings and preserves complete service/contract/actor/binding snapshots. Provenance is `source.kind=catalogue_composed`; there is no fake legacy template key or qualification. A retained server-issued creation nonce makes duplicate identical requests return the same owned draft; altered reuse is rejected.
- The initial engineering state has zero nodes and edges and a pending two-operation proposal. Apply rechecks authority and revision before installing it. Full Undo restores the entire initial engineering state and the same reviewable proposal. Apply again retains the allocated instance IDs. Save rejects pending/empty/stale designs and preserves the exact settings, pins and binding on reopen. Concurrent PostgreSQL behavior is not newly verified by these SQLite tests.
- The full authority snapshot remains private server state and owned saved-design metadata. Provider explanation context contains only the sanitized review and source kind. New draft chat cannot expand the graph or change settings in this milestone; explicit Apply/Undo/Save controls remain primary.
- Saved composition provenance and the design-only execution marker cannot be stripped through ordinary Builder updates. Builder suppresses runtime/deployment actions, and server preflight/submission rejects a marked design before invoking runtime functions. The existing qualified Dutch execution gate rejects it independently. No grant is inherited or created.

## Actual checks and limits

Final source: **192 backend tests passed** (50 composition + 142 related compatibility), **25 frontend tests passed**, typecheck passed and staged Gitleaks found zero secrets. Backend: 162.86 seconds, 1,729 existing warnings; zero failures/errors/skips. Implementation/source fingerprint stayed unchanged through the final checks.

See [sanitized exact-source evidence](DESIGN_AI_CATALOGUE_COMPOSITION_EVIDENCE_2026-11-02.json) for commands, source identity and counts. Focused checks cover template-free discovery/Create/Apply/Undo/Apply/Save/reopen, a second synthetic family, incompatibility and missing contracts, required values/defaults, invented/ambiguous/unauthorized candidates, authority drift, duplicate actions, stale Save, owner boundaries and explicit execution denial. Existing discovery, registered creation, targeted settings, structural editing and goal-to-results compatibility tests are included.

All new composition tests use isolated SQLite and labelled provider doubles, with socket connections, real provider construction, readiness probes and submission forbidden. Six frontend test files cover state/cache restoration, exact creation request, static proposal rendering, escaping and Builder review behavior. Typecheck runs against existing dependencies. No dependency installation, Docker operation, application/image build, new profile/port, real provider, workflow or runtime/evidence database connection occurs.

Real-provider interpretation, integrated browser rendering, new PostgreSQL concurrency, independent usability, runtime availability and production compatibility remain unverified. The known earlier backend package-import failure was resolved in the recorded staging consolidation; no new complete backend inventory is claimed here. Existing deprecation/module warnings and intermediate harness failures remain in private logs.

## Next non-paid acceptance

After the separate Docker/API availability blocker is resolved and an offline walkthrough environment is explicitly prepared, have an independent person review a labelled synthetic pair proposal, explain what changes and what remains unverified, Create, Apply, Undo to the empty design, Apply again, Save, reopen and open Builder. Ask whether any workflow executed; the answer must be no. Record hesitation, confusing wording and assistance without inventing observations. No arbitrary chat interpretation, provider call or execution is required for that walkthrough. **Prepared in code; awaiting independent human acceptance.** No new profile or fixture deployment was created in this milestone.

Preservation: original local changes, protected evidence/configuration/credentials, retained demonstration build and existing source stack remain intact. Shared allowance remains exhausted at 13/13 with no ledger or grant changes. AIE-18 remains In Review. Docker recovery and staging approval remain separate work.

## 6 November — separate host browser acceptance preparation

The original implementation/offline record above is preserved. Starting source was verified as PR #15 `a2efec14911624f0d4d423163461cd69229951a4`, on PR #14 `f36f8fdfcfb95576d948fea2971907ad4d433e3a`, with a clean milestone worktree. Harness source: **`22cded06e3f4efdaef4055376b0724929df975b0`**. No application feature source changed. Existing Python 3.12.14, Node 24.15.0, Next 16.3.8 and installed dependencies were reused. C: free space was 45.11 GiB before preparation and 43.66 GiB after initial development compilation. No cleanup, downloads, production build or container operation was performed.

One bounded Docker check returned a named-pipe permission error; the existing API did not respond. This does not establish that Docker was stopped. No repair, restart or repeated Docker diagnosis was attempted. Instead, the opt-in [host walkthrough harness and five-step brief](../deploy/composition_walkthrough/README.md) use disposable SQLite with the existing portable test-only JSONB compiler support. Production database behavior and validation are unchanged. The native API binds `127.0.0.1:28187`; Next dev binds `127.0.0.1:23123` and uses `.next-controls-20261106`. Retained `.next` and tracked TypeScript configuration remain byte-for-byte preserved. Processes are detached with private local logs and a startup/PID record.

**One human entry:** <http://127.0.0.1:23123/api/offline-controls/human>. Normal sign-in is `controls-human@example.test`; read `human.password` privately from `local-backups/composition-browser-acceptance-20261106/profile/private-credentials.json` under the original checkout. No password is included here, in browser evidence or in Git. The browser is left signed into that account with its prepared recommendation open. The entry restores the existing conversation format then opens the actual Design with AI application; it does not imitate the controls or bypass authentication. The fixed recommendation, two catalogue operations and contracts are synthetic, and its label is:

> Offline controls walkthrough: prepared synthetic proposal. No live AI or execution.

Two distinct actor-bound recommendations were generated through normal authenticated discovery and a labelled provider double during one-time harness preparation. During serving, chat is rejected server-side and Send is disabled. The fixture cannot interpret arbitrary chat or become a production fallback. Outbound connect/connect_ex/create_connection, real provider SDK calls, runtime/readiness functions and submission/execution HTTP routes are blocked. No allowance or grant is attached. The sole network exception is the exact stdlib Windows asyncio socketpair caller used for the server's own wake-up pipe.

### Agent technical checks — completed, not human usability observations

| Actual check | Observed result |
|---|---|
| Normal login and real Design with AI proposal | Both synthetic steps, count 3, complete upstream observation-reference connection, new-design provenance and no-execution label displayed |
| Explicit Create | New owned draft `22e31c23-7eee-5390-8c81-7ee8cbe9ee36`, revision 0; zero applied nodes/edges plus pending proposal; no saved template copied |
| Apply | Revision 1, two nodes and one binding |
| Undo | Revision 2, entire applied graph empty and the same proposal reviewable; Apply control immediately available |
| Apply again | Revision 3 with exact same settings, node identities, contract pins and binding; no helper or new fixture response |
| Save/reload/Builder | Saved solution `b899b411-47db-4208-a5eb-1c3e7c289917`; exact graph preserved; Builder shows count 3, both pins/IDs and `observations → observations`, `whole-output-v1`; states no execution result and execution unavailable |
| Focused rejection checks on actual API | Stale Apply/Undo/Save: 409; another owner Read/Apply/Save: 404; chat, execution review, runtime preflight and submission: 403; no design mutation |
| Harness network checks | Three tests passed in 0.19s, with each outbound method rejected before network access; stdlib socketpair still works |
| Launcher | PowerShell syntax passed; initial native start succeeded; generated type-reference restoration was independently verified against original bytes |
| Fresh human recommendation | Separate account/nonce; **zero drafts and zero saved solutions**; no Create, Apply or Save performed on it |
| No execution | Disposable database contains zero deployments and zero execution submissions; no actual algorithm, provider call, readiness probe or grant |
| Preservation | All **548** protected file hashes match (250 prior local-work/evidence records plus retained build/configuration); original checkout's dirty status unchanged; existing allowance remains 13/13 and protected provider/grant state unchanged |

Agent [prepared-proposal evidence](screenshots/composition-controls-prepared-20261106.png) and [saved Builder evidence](screenshots/composition-controls-builder-20261106.png) are labelled synthetic. Private records retain revision responses, binding/pin inspection, rejection statuses, logs and screenshots. [Sanitized browser-preparation evidence](DESIGN_AI_COMPOSITION_BROWSER_EVIDENCE_2026-11-06.json) records source, hashes and counts. No full unrelated suites or previous acceptance were repeated. Next dev emitted transient React Flow container-size warnings; the subsequent saved Builder screenshot shows the actual connected canvas. A narrow viewport requires scrolling inside the proposal card. Existing unavailable Dutch-library copy and general readiness wording were not redesigned in this task.

### Human acceptance — prepared; awaiting human walkthrough

Use the five-step participant brief and blank observer checklist in the harness README. The human proposal is left untouched and requires no chat interpretation or operator restoration between Undo and Apply again. Record completion, hesitation, confusing wording and assistance only after observation. No owner or independent participant usability result is claimed.

This verifies the actual host browser controls journey with synthetic catalogue/settings/provider data. Real-provider interpretation, the full first-time-user journey, PostgreSQL concurrency, live availability/qualification, scientific validity and production compatibility remain unverified. Docker/API recovery remains separate and does not block this host-only controls walkthrough. AIE-18 remains In Review; broader AIE-38 composition remains incomplete. No staging, production, tracker or merge action occurred.

## 10 November — owner functional acceptance and separate workspace refinement

The owner confirms count 3, design/connection/count surviving refresh, full Undo to the empty design, and reapply/Save. Purpose/controls are **PARTLY** understandable; the remaining feedback is that the workspace is text-heavy and far from the original reference. This is owner functional acceptance with unresolved usability feedback, not independent usability or real-provider acceptance. The completed owner draft and solution are preserved without reset or replay.

A separate focused draft stacked on PR #15 implements the [workspace refinement and three-step owner review](DESIGN_AI_WORKSPACE_REVIEW_2026-11-10.md), using the existing host walkthrough and a distinct engineering copy. The earlier records above remain historical; the new design awaits owner usability feedback. AIE-18 is unchanged.
