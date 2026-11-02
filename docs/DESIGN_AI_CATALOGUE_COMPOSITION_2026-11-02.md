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
