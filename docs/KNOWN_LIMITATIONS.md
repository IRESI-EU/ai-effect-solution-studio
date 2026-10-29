# Known MVP Limitations

## Status

AI-EFFECT Solution Studio is an MVP for local consortium evaluation. The following limitations should be considered when planning tests, interpreting evidence, or demonstrating the platform.

## Identity, permissions, and governance

### Authentication is not implemented

The application does not authenticate users. Do not expose the MVP directly to untrusted networks or use production credentials.

### Real RBAC is not implemented

The **Preview experience as** selector changes guidance only. It does not change API permissions, authorize actions, or grant Platform Admin rights.

### Governance is not production certification

Approval, rejection, lifecycle state, and trust badges support the MVP review journey. Solution Studio is not a production certification authority and does not provide legal or regulatory assurance.

## Runtime preparation and readiness

### Deployment Profiles are not first-class entities

Runtime ownership, environment, health policy, and deployment-specific configuration are not represented by a separate Deployment Profile model.

### Legacy service runtime metadata is used

Runtime readiness resolves `internal_host`, `internal_port`, and `health_path` from the service catalogue. `provider_managed` is the legacy default management mode.

### Solution Studio does not manage provider runtimes

Platform-managed start, restart, scheduling, and log controls are not implemented. The service provider or TEF operator must prepare and diagnose runtimes using the external service environment.

### Health checks are sequential

Each selected service is checked one after another with a two-second request timeout. Large workflows can therefore take approximately two seconds per unavailable service, plus connection overhead.

### Readiness is not execution assurance

A ready result confirms governance eligibility, valid runtime metadata, and a 2xx health response at one point in time. It does not guarantee:

- WP3 is reachable;
- the runtime remains healthy after the check;
- the operation accepts the submitted arguments;
- required input files or DataReferences exist;
- the workflow will complete successfully.

The backend reruns readiness at confirmation, reducing but not eliminating time-of-check/time-of-use risk.

### Semantic validation is not implemented

The Builder compares adjacent input and output type strings and checks graph structure. It does not reason about semantic meaning, units, schemas, operation preconditions, or adapter suitability.

### AnalyzeData requires upstream input

The Portuguese `AnalyzeData` operation requires an upstream input file. An AnalyzeData-only workflow may pass runtime readiness and reach WP3, then fail with:

```text
No input file provided
```

Use the complete Portuguese workflow for end-to-end execution testing.

## Traceability and persistence

### Nullable solution linkage remains in the data/API model

Earlier Builder versions, direct API clients, or imported historical records can produce a Deployment with an empty `solution_id`, because the persistence schema remains nullable for compatibility.

The current Builder corrects the normal user journey: **Prepare & deploy** creates or updates the solution before preflight and uses the returned ID for preflight, WP3 submission, and Deployment persistence. Existing unlinked records are not automatically repaired.

### Database migrations are manual

The API runs SQLAlchemy `Base.metadata.create_all(...)`. There is no Alembic or equivalent migration history. Existing local PostgreSQL volumes may require manual adjustment after model changes.

### Local state is not multi-user safe

The MVP has no user ownership, optimistic locking, or concurrent editing model. Multiple testers can overwrite the same saved solution.

## WP3 and external repositories

### WP3 is a separate required repository

Solution Studio does not bundle the WP3 Orchestrator. The orchestrator must run separately at the configured address.

### Node services are external dependencies

Portuguese and Dutch examples are maintained outside this repository. Their paths, Compose services, images, health endpoints, or payload contracts can change independently.

### Current WP3 schema requires compatibility mapping

The compiler maintains the current blueprint and docker-information structure. Non-gRPC services may use a `contract_uri` to `proto_uri` compatibility bridge until the orchestrator contract evolves.

### Full external regressions are release-specific

The presence of example support does not prove that the complete Portuguese or Dutch workflow passed for the current set of commits. Record all repository revisions when reporting a successful regression.

## Monitoring and evidence

### File inspection depends on shared storage

A `file` DataReference can be previewed only when the referenced path is available inside the API container. Otherwise, the UI shows metadata and an availability explanation.

### gRPC artifact inspection is limited

gRPC DataReferences are shown as metadata. The portal does not retrieve or decode the remote gRPC payload.

### S3 and orchestrator artifacts are not configured

The API recognizes `s3` and `artifact` protocols but does not fetch their content.

### HTTP preview is basic

HTTP/HTTPS preview fetches remote content with a ten-second timeout and infers JSON, CSV, or text. It does not provide an allowlist, credential flow, large-artifact streaming, or malware scanning.

### Preview sizes are limited

Text preview is capped, and CSV preview is limited to a small row sample. Evidence shown in the UI may therefore be truncated.

## Deployment environment

### Local Docker is the supported environment

The current Compose stack and `host.docker.internal` orchestrator routing target Docker Desktop. Other container runtimes or Linux host setups can require configuration changes.

### Cloud deployment is not provided

There is no maintained Kubernetes, AWS, Azure, or other cloud deployment package in this repository.

### Development server in the web container

The current web Dockerfile starts `next dev`. It is appropriate for local MVP testing, not for production hosting.

### Dependencies are not fully pinned

Several Python requirements and frontend package declarations do not use fixed versions. A clean rebuild at a later date can resolve different packages.

## Security and operational limitations

- No secret-management integration is provided.
- No rate limiting or tenant isolation is implemented.
- Runtime and DataReference URLs should be treated as trusted test metadata.
- Audit history is functional application data, not a tamper-evident compliance log.
- Backup, disaster recovery, observability, and service-level objectives are not defined.

## Related documents

- [Repository README](../README.md)
- [Team testing guide](TEAM_TESTING_GUIDE.md)
- [Current capabilities](CURRENT_CAPABILITIES.md)
- [MVP release notes](MVP_RELEASE_NOTES.md)

## AIE-37 local qualification limits — 28 October 2026

Only the pinned Dutch capture chain has the new end-to-end qualification. The
whole-output transport supports one input/output slot and no merge, projection,
conversion or workflow-input routing. Scientific validity, KPI units, real
node-owner attestation, production auth/network/storage, concurrency, cancellation
and crash recovery are not established by its one local run. The Danish renderer
and German VILLAS lifecycle still need independent qualification. See
[AIE37_CATALOGUE_QUALIFICATION.md](AIE37_CATALOGUE_QUALIFICATION.md).

## AIE-38 bounded composition limits — 28 October 2026

Structural composition supports one existing terminal analyzer with one pinned
whole-output input/output and no editable target settings. Replacement, deletion,
branching, loops, routing, projections, conversions, merges and onboarding remain
unsupported. Fixture review/Apply/Undo/Save checks do not establish model intent
quality, runtime availability, scientific validity, independent usability or
production compatibility. The existing allowance remains exhausted at 12/12.
See [AIE38_CONVERSATIONAL_COMPOSITION.md](AIE38_CONVERSATIONAL_COMPOSITION.md).


## AIE-41 usability review limits — 29 October 2026

The completed guided walkthrough and wording findings are owner feedback. They
are not independent first-time-user evidence, and the revised UI awaits owner
retest and independent observation. The offline fixture checks prepared proposal
review/controls, not arbitrary conversation, real-provider interpretation or full
onboarding. Existing workflow/run/session terminology remains pending team agreement.
Design compatibility does not establish runtime or production readiness. Explicit
Fit workflow may show a wide graph at overview scale; readable initial view and
per-user/per-solution viewport restoration remain available. The full backend
baseline remains 339 passed / 1 failure. See
[AIE41_USABILITY_REFINEMENT.md](AIE41_USABILITY_REFINEMENT.md).


The AIE-41 follow-up has 35 passing UI regressions and rendered desktop/narrow
checks, including bounded dialogs and stale Save rejection on one disposable copy.
It still awaits a new human walkthrough; owner feedback is not independent evidence.
Offline checks do not exercise runtime readiness/execution or production compatibility.
