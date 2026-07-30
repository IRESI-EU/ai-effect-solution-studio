# AI-EFFECT Solution Studio MVP Release Notes

## Release purpose

This release candidate pauses feature development and prepares the current Solution Studio MVP for AI-EFFECT consortium team testing. It brings the catalogue, governance, visual composition, runtime readiness, explicit deployment confirmation, and monitoring journeys into one local Docker-based test environment.

This is an MVP test release, not a production or certification release.

## Release highlights

### Catalogue and service governance

- Service marketplace with service detail pages and onboarding metadata.
- Pasted-manifest and public Git manifest preview/import.
- WP3 package import from blueprint and docker information.
- Approval, rejection, review reopening, activation, deprecation, archive, and restore.
- Deployment eligibility tied to approved or legacy validated service status.
- Archived services excluded from normal Catalogue and Builder use.

### Visual composition

- React Flow Builder with Workflow Input, Workflow Output, service palette, and inspector.
- Internal palette scrolling for larger catalogues.
- Structural validation for complete input-to-output participation.
- Adjacent service input/output type comparison.
- Detection of disconnected services and stale validation state.

### Saved solution workspaces

- Draft creation and update.
- Persistent graph, name, status, and description.
- Solution list, workspace, latest-run context, graph view, and deployment history.
- Solution archive and restore.
- Automatic solution save before deployment preparation.

### Deployment lifecycle

- Deployment record created after confirmed WP3 submission.
- Deployment linked to the saved solution in the normal Builder journey.
- Active and archived deployment views.
- Status synchronization from WP3.
- Archive and restore without deleting audit history.

### Runtime readiness

- Preflight checks service existence, governance, runtime metadata, and provider-managed health.
- Results distinguish `ready`, `unavailable`, `misconfigured`, `ineligible`, and `unknown`.
- Controlled messages identify the responsible party and recommended action.
- Health calls use a two-second timeout, require 2xx, and do not follow redirects.
- Checks currently run sequentially.

### Prepare-and-deploy flow

The main journey is:

```text
Save draft (optional)
-> Validate design
-> Automatically save current design
-> Prepare & deploy
-> Resolve readiness blockers
-> Confirm deployment
-> Submit through WP3
```

Preparation does not submit a workflow. Confirmation is shown only after readiness succeeds. The submit endpoint independently reruns preflight and returns HTTP `409 Conflict` when blocked.

### WP3 integration

- Compilation to the current WP3 blueprint v2 and docker-information structure.
- Service registry metadata resolved at submission time.
- Compatibility metadata retained for onboarding traceability.
- Adapter calls for workflow submission, workflow status, and task status.
- WP3 remains a separate repository and execution service.

### Monitoring and evidence inspection

- Deployment and solution-workspace status refresh.
- Workflow and task status display.
- Input and output DataReference listing.
- Inline, accessible file, and HTTP JSON/CSV/text preview.
- Explicit limitations for gRPC, S3, inaccessible files, and orchestrator artifact references.

### Portuguese and Dutch examples

Documentation covers:

- the Portuguese file-based energy pipeline:

  ```text
  Workflow Input
  -> input_provider1 / GetConfiguration
  -> data_generator1 / GenerateData
  -> data_analyzer1 / AnalyzeData
  -> report_generator1 / GenerateReport
  -> Workflow Output
  ```

- the representative Dutch composition:

  ```text
  Workflow Input
  -> grid_synth_service / ConfigureAndSynthesize
  -> benchmark-runner / RunBenchmark
  -> Workflow Output
  ```

The orchestrator and node services are external dependencies; their exact commits must be recorded with test evidence.

## Verified test evidence

The following focused scenarios are recorded as verified for the MVP readiness work:

| Test | Verified result |
|---|---|
| Empty workflow | Blocked before runtime preparation |
| Rejected service | Reported as `ineligible` |
| Validated service with offline runtime | Reported as `unavailable` |
| Canvas change after readiness | Old design/readiness/confirmation results invalidated |
| Direct deployment while blocked | Backend returns HTTP `409 Conflict` and does not compile or submit |
| Runtime-ready workflow | Requires a separate explicit confirmation |
| Confirmed workflow | Creates a local Deployment record after submission |
| AnalyzeData-only workflow | Reaches WP3 when runtime-ready but fails execution because no input file is supplied |

The AnalyzeData-only result demonstrates the boundary between operational health and operation preconditions. Runtime readiness is not execution assurance.

## Verification not claimed

These release notes do **not** claim that the complete Portuguese pipeline regression was run successfully for the current combination of Solution Studio, WP3, and node-service commits. The full chain should be executed using the [team testing guide](TEAM_TESTING_GUIDE.md), and all repository revisions should be attached to the result.

The same evidence rule applies to the complete Dutch workflow.

## Compatibility and data notes

- The WP3 execution payload remains limited to the current supported `blueprint`, `dockerinfo`, and optional established fields.
- Solution Studio metadata is retained outside the WP3 execution object for traceability.
- Existing PostgreSQL volumes are not managed through a migration framework.
- Historical or direct-API Deployment records can have a nullable `solution_id`; the current Builder auto-saves and links new normal-path deployments.
- Existing saved Portuguese and Dutch service records remain compatible with legacy `validated` governance status.

## Known limitations

Material limitations include:

- no authentication or enforced RBAC;
- no first-class Deployment Profiles;
- no platform-managed runtime controls;
- no semantic or operation-precondition validation;
- sequential runtime health checks;
- limited file and gRPC artifact inspection;
- local Docker-only supported environment;
- no cloud deployment or production certification authority.

See [Known MVP limitations](KNOWN_LIMITATIONS.md) for the complete list.

## Test documentation

- [Repository README](../README.md)
- [Team testing guide](TEAM_TESTING_GUIDE.md)
- [Current capabilities](CURRENT_CAPABILITIES.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
