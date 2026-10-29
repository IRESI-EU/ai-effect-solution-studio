# Current MVP Capabilities

> Dated update: [AIE-37 local qualification, 28 October 2026](AIE37_CATALOGUE_QUALIFICATION.md) supersedes earlier baseline statements about semantic binding checks. Earlier evidence is retained.

## Scope

This document records functionality implemented in the AI-EFFECT Solution Studio MVP. “Implemented” means the repository contains the user interface and API path; it does not imply production certification, cloud readiness, or completion of every external WP3 regression.

## Implemented functionality

### Service catalogue and onboarding

| Capability | Current implementation |
|---|---|
| Service Catalogue | Lists active and deprecated services and supports search, category, and provider filtering |
| Service details | Shows identity, provider, version, lifecycle, trust, interface, orchestration, adapter, contract, runtime, and source metadata |
| Manual service publishing | Creates a service from the basic service form/API with pending-review governance state |
| Manifest import | Previews public Git manifests or pasted JSON, validates and normalizes metadata, then imports to the catalogue |
| WP3 package import | Converts `blueprint.json` and `dockerinfo.json` objects into catalogue services |
| Example manifests | Control, gRPC, HTTP, container-job, and sidecar examples are stored under `examples/service-manifest/` |
| Onboarding metadata | Preserves interface type, orchestration mode, adapter type, health path, contract URI, and repository traceability |

### Service governance

| Capability | Current implementation |
|---|---|
| Approval | Marks a service approved with validated trust state |
| Rejection | Marks a service rejected and blocks deployment eligibility |
| Reopening | Returns a rejected or reviewed service to pending review |
| Lifecycle governance | Activate, deprecate, archive, and restore |
| Catalogue visibility | Archived services are excluded by default; deprecated services remain visible with warnings |
| Eligibility enforcement | Only `approved` and legacy `validated` services pass readiness governance |

The shell’s persona selector is a preview utility. It changes guidance only; the API does not enforce role-based permissions.

### Solution Builder

| Capability | Current implementation |
|---|---|
| Visual composition | React Flow canvas with Workflow Input, Workflow Output, service nodes, and edges |
| Service palette | Searchable, internally scrolling list of non-archived services |
| Inspector | Shows selected service metadata and lifecycle/interface warnings |
| Structural validation | Requires a service, input connection, output connection, and complete input-to-output participation |
| Interface validation | Compares connected service output and input type strings |
| Disconnection detection | Identifies services outside a complete input-to-output path |
| Stale-result invalidation | Clears design, readiness, confirmation, and deployment results when nodes or edges change |

Validation is structural and syntactic. It does not understand operation semantics or required runtime files.

### Saved solutions and lifecycle

| Capability | Current implementation |
|---|---|
| Save draft | Creates or updates a solution containing name, nodes, edges, description, and draft status |
| Automatic preparation save | **Prepare & deploy** persists the current design before readiness begins |
| Traceable deployment link | Saved solution ID is used in preflight, submission, and the Deployment record |
| Solution library | Lists saved solutions and summary counts |
| Solution workspace | Displays graph, latest run, run health, and deployment history |
| Solution archive/restore | Preserves archived workspaces as read-only audit records |

The data model permits a nullable deployment `solution_id` for compatibility. The current Builder does not intentionally create an unlinked deployment.

### Deployment readiness

| Capability | Current implementation |
|---|---|
| Runtime preflight | `POST /workflows/runtime-preflight` checks each workflow service before deployment |
| Empty-workflow guard | A workflow with no services is blocked |
| Service-reference validation | Missing service IDs are `misconfigured`; missing catalogue records are `unknown` |
| Governance eligibility | Archived, rejected, and unapproved services are `ineligible` |
| Runtime metadata validation | Validates host, port range, and health path |
| Provider-managed health check | Calls the resolved HTTP(S) health endpoint sequentially with a two-second timeout and no redirects |
| Readiness outcomes | `ready`, `unavailable`, `misconfigured`, `ineligible`, and `unknown` |
| Recommended action | Returns responsible party, reason, and action for every blocked service |
| Backend deployment guard | Submission independently reruns preflight and returns HTTP `409 Conflict` when blocked |

### Prepare-and-deploy journey

The implemented sequence is:

```text
Save draft (optional explicit checkpoint)
-> Validate design
-> Automatically save current solution
-> Prepare deployment
-> Explain readiness blockers
-> Confirm deployment
-> Submit through WP3
```

The main user action is **Prepare & deploy**. WP3 remains an internal execution mechanism. A ready result exposes a separate **Confirm deployment** action; preparation alone does not submit.

Immediate in-flight guards and disabled controls reduce duplicate saves, readiness requests, and submissions caused by double-clicking.

### WP3 compilation and submission

| Capability | Current implementation |
|---|---|
| Workflow compilation | Converts selected services and service-to-service edges into WP3 blueprint v2 and docker information |
| Registry resolution | Resolves current service runtime metadata from the catalogue during compilation |
| Compatibility metadata | Adds Solution Studio onboarding traceability and compiler warnings outside the WP3 execution payload |
| Interface bridge | Maps non-gRPC contract metadata into the current `proto_uri`-compatible field where required |
| Submission adapter | Sends `blueprint`, `dockerinfo`, and optional supported fields to WP3 `POST /workflows` |

### Deployment and evidence monitoring

| Capability | Current implementation |
|---|---|
| Deployment persistence | Stores workflow ID, solution ID, name, and status after confirmed submission |
| Status synchronization | Refreshes active Deployment records from WP3 |
| Deployment lifecycle | Archive and restore without deleting audit history |
| Workflow monitoring | Retrieves normalized WP3 workflow status |
| Task monitoring | Retrieves task IDs, node keys, status, and references |
| DataReference inspection | Previews inline and accessible file/HTTP JSON, CSV, or text |
| Evidence limits | Returns explicit unavailable messages for unsupported or inaccessible protocols |

## Planned or not yet implemented

| Planned capability | Current status |
|---|---|
| Authentication and single sign-on | Not implemented |
| Enforced RBAC | Not implemented |
| First-class Deployment Profiles | Not implemented |
| Platform-managed runtime start/restart/logs | Not implemented |
| Semantic compatibility reasoning | Not implemented |
| Operation-precondition validation | Not implemented |
| Parallel health checking | Not implemented |
| Production migration framework | Not implemented |
| Cloud deployment | Not provided |
| Full gRPC payload inspection | Not implemented |
| S3 and orchestrator artifact retrieval | Reserved but not configured |
| Production certification workflow | Outside MVP scope |

## Capability boundaries

- A 2xx health response means the configured endpoint is reachable; it does not prove an operation will succeed.
- WP3 and node services are external dependencies maintained in separate repositories.
- Governance status is an MVP workflow, not legally authoritative certification.
- Local Docker Compose is the supported test environment.
- Current full Portuguese and Dutch regression status must be reported separately for each tested commit set.

## Related documents

- [Repository README](../README.md)
- [Team testing guide](TEAM_TESTING_GUIDE.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
- [MVP release notes](MVP_RELEASE_NOTES.md)

## 28 October 2026 — AIE-37 local qualification update

The earlier sections describe their historical baseline. Builder now checks
opt-in explicit slot bindings against pinned operation contracts on Save and
compile, then checks runtime contract fingerprints separately from governance
and health. Shared catalogue labels alone do not establish semantic compatibility.
Supported legacy graphs retain a clearly unqualified compatibility path.

The existing Dutch generation → benchmark workflow completed one isolated run,
with seed consumption, exact downstream references and four authorized hashed
downloads verified. A later draft setting edit left history unchanged. Details,
limits, source/runtime identities and review URLs are in
[AIE37_CATALOGUE_QUALIFICATION.md](AIE37_CATALOGUE_QUALIFICATION.md). This is not
production acceptance. AIE-18 remains In Review; AIE-38 structural editing is not
implemented. No provider call was made and the allowance remains exhausted 12/12.

## 28 October 2026 — bounded AIE-38 composition

An explicitly selected structural copy can propose adding one authorized,
contract-compatible terminal analyzer and its named whole-output connection.
Review includes terminal edge removal; Apply, full Undo, Save/reload and Builder
were verified with labelled offline provider-boundary fixtures. Existing settings-only
scopes remain restricted. No provider call or workflow execution was made. See
[AIE38_CONVERSATIONAL_COMPOSITION.md](AIE38_CONVERSATIONAL_COMPOSITION.md).


## 29 October 2026 — focused AIE-41 review refinement

Builder now leads with readable actual-endpoint connection summaries, separate
saved/configured/checked states, selected-step purpose/settings and collapsed
technical details. Proposal review leads with additions, data source and unchanged
settings while retaining explicit connection diffs. Owner-guided Apply/Undo/Apply/Save/
Builder/refresh completed with seed 42 preserved; independent usability remains
unverified. No broader composition or lifecycle vocabulary redesign was added.
See [AIE41_USABILITY_REFINEMENT.md](AIE41_USABILITY_REFINEMENT.md) for rendered
evidence, 28 UI checks, typecheck/build and preserved offline boundaries.
