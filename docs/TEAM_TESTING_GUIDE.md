# AI-EFFECT Solution Studio Team Testing Guide

## Purpose

This guide supports structured consortium testing of the local Solution Studio MVP. It assumes Windows, PowerShell, Docker Desktop, and access to the separate WP3 repository.

Record the Solution Studio commit, WP3 commit, browser, and Docker Desktop version in every test report.

## 1. Test environment preparation

Keep the repositories separate:

```text
working-directory/
  ai-effect-solution-studio/
  ai-effect-wp3/
```

In PowerShell, define paths without embedding user-specific locations:

```powershell
$StudioRoot = Resolve-Path ".\ai-effect-solution-studio"
$Wp3Root = Resolve-Path ".\ai-effect-wp3"

git -C $StudioRoot rev-parse --short HEAD
git -C $Wp3Root rev-parse --short HEAD
docker version
docker compose version
```

Create the external artifact volume required by Solution Studio:

```powershell
docker volume inspect wp3_artifacts 2>$null
if ($LASTEXITCODE -ne 0) { docker volume create wp3_artifacts }
```

For a clean database, explicitly remove the Solution Studio Compose volumes. This is destructive and should not be used when test history must be retained:

```powershell
Set-Location $StudioRoot
docker compose down -v
```

## 2. Docker startup commands

Start the WP3 Orchestrator from its repository:

```powershell
Set-Location "$Wp3Root\orchestrator"
docker compose up -d --build
```

Start the Portuguese Node example:

```powershell
Set-Location "$Wp3Root\use-cases\file_based_energy_pipeline"
docker compose up -d --build
```

Start the Dutch Node examples:

```powershell
Set-Location "$Wp3Root\use-cases\dutch_node\data_synthesizer"
docker compose -f docker-compose-all.yml up -d --build

Set-Location "$Wp3Root\use-cases\dutch_node\benchmarking"
docker compose -f docker-compose-all.yml up -d --build
```

Start Solution Studio:

```powershell
Set-Location $StudioRoot
docker compose up -d --build
docker compose ps
```

If external repository paths or Compose filenames differ, follow that repository's README and record the variation.

## 3. Health verification commands

```powershell
Invoke-RestMethod http://localhost:18080/health
Invoke-WebRequest http://localhost:13000
Invoke-RestMethod http://localhost:18000/health

Invoke-RestMethod http://localhost:18081/health
Invoke-RestMethod http://localhost:18082/health
Invoke-RestMethod http://localhost:18083/health
Invoke-RestMethod http://localhost:18084/health

Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8004/health

Set-Location $StudioRoot
docker compose exec -T postgres pg_isready -U solution_studio -d solution_studio
```

Expected:

- the Solution Studio and WP3 health endpoints return status `ok`;
- the web request returns a successful HTTP status;
- node-service health endpoints return 2xx;
- PostgreSQL reports that it is accepting connections.

For diagnostics:

```powershell
Set-Location $StudioRoot
docker compose logs --tail 100 api
docker compose logs --tail 100 web
docker compose logs --tail 100 postgres
```

## 4. Service import instructions

### Pasted manifest

1. Open <http://localhost:13000/publish>.
2. Select **Load example HTTP manifest**, or paste one of the files under `examples/service-manifest/`.
3. Select **Preview pasted manifest**.
4. Confirm that validation is `valid` or `warning` and normalized metadata is shown.
5. Select **Confirm import to Catalogue**.
6. Record the created service ID.

### Public Git manifest

1. Enter a public repository URL, branch, and manifest path.
2. Preview the Git import.
3. Review validation results.
4. If confirmation is required, use the normalized manifest workflow presented by the page.

Private Git authentication is not implemented.

### WP3 package

```powershell
$PackageRoot = Resolve-Path "$Wp3Root\use-cases\file_based_energy_pipeline\export"
$Body = @{
  provider = "Portuguese Node"
  category = "File-Based Energy Pipeline"
  trust_badge = "Imported"
  blueprint = Get-Content "$PackageRoot\blueprint.json" -Raw | ConvertFrom-Json
  dockerinfo = Get-Content "$PackageRoot\dockerinfo.json" -Raw | ConvertFrom-Json
} | ConvertTo-Json -Depth 100

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:18080/admin/import/wp3-package `
  -ContentType "application/json" `
  -Body $Body
```

Use the corresponding package path for Dutch services. Imported services require governance review before readiness can pass.

## 5. Catalogue testing

1. Open <http://localhost:13000/catalogue>.
2. Search by service name, provider, or capability.
3. Filter by category and provider.
4. Open a service details page.
5. Verify provider, version, lifecycle, trust, interface type, orchestration mode, adapter, contract, runtime, and source metadata.
6. Confirm archived services are absent from the default catalogue.
7. Select **Add to workflow** and confirm Builder opens.

Expected: active and deprecated services are discoverable; deprecated services have visible warnings; archived services are hidden.

## 6. Service governance testing

1. Open <http://localhost:13000/admin>.
2. Select an imported `pending_review` service.
3. Approve it and verify status/trust becomes approved or validated.
4. Reopen its review and verify it returns to pending review.
5. Reject it and verify the rejected state.
6. Test deprecate, archive, restore, and activate.
7. Return the service to the state needed by the following scenarios.

Expected:

- rejected and pending-review services are not deployment-eligible;
- archived services are hidden from Catalogue and Builder;
- deprecated eligible services remain available with warnings.

## 7. Solution Builder testing

Open <http://localhost:13000/builder>.

1. Give the solution a distinctive name.
2. Add services from the internally scrolling palette.
3. Connect Workflow Input through the service chain to Workflow Output.
4. Move nodes and remove/reconnect edges.
5. Select a service and inspect its metadata.
6. Select **Save draft**.
7. Open **Saved solutions** and verify the workspace exists.
8. Return to Builder and confirm the graph loads.

The intended Portuguese workflow is:

```text
Workflow Input
-> input_provider1 / GetConfiguration
-> data_generator1 / GenerateData
-> data_analyzer1 / AnalyzeData
-> report_generator1 / GenerateReport
-> Workflow Output
```

## 8. Blank-workflow validation test

1. Open a new Builder workspace.
2. Do not add a service.
3. Select **Validate design**.
4. Select **Prepare & deploy**.

Expected:

- design validation reports that at least one service is required;
- preparation stops before runtime preflight;
- no confirmation action appears;
- no WP3 workflow or Deployment record is created.

## 9. Rejected-service eligibility test

1. Reject a service in Admin.
2. Add that service to a complete input-to-output workflow.
3. Select **Prepare & deploy**.

Expected:

- design validation can pass if the graph and types are valid;
- readiness reports the service as `ineligible`;
- the reason identifies governance rejection;
- confirmation is unavailable.

Restore or approve the service after the test.

## 10. Offline-runtime test

1. Use an approved or legacy validated service.
2. Stop its provider container using the companion repository's Compose command:

```powershell
Set-Location "<directory-containing-the-service-compose-file>"
docker compose stop <service-name>
```

3. Build a structurally valid workflow.
4. Select **Prepare & deploy**.

Expected:

- the solution is saved before preflight;
- readiness reports `unavailable`;
- the responsible party and recommended provider action are shown;
- confirmation is unavailable.

Restart the service:

```powershell
docker compose start <service-name>
```

## 11. Runtime-ready test

1. Confirm every selected service health endpoint returns 2xx.
2. Confirm every service is approved or legacy validated.
3. Build a complete, type-compatible workflow.
4. Select **Prepare & deploy**.

Expected:

- the current solution is created or updated automatically;
- readiness reports `ready`;
- **Confirm deployment** appears;
- no WP3 submission occurs before confirmation.

## 12. Stale-readiness reset test

1. Reach the ready state in the previous test.
2. Add, remove, or reconnect a service or edge.

Expected:

- design results, readiness, confirmation, and previous deployment result are cleared;
- the page reports that the solution changed and must be revalidated;
- confirmation cannot use the stale readiness result.

## 13. Deployment confirmation test

1. Prepare a ready workflow.
2. Note the saved solution ID from Saved solutions or the solution workspace URL.
3. Select **Confirm deployment** once.
4. If testing double-click protection, click rapidly twice.
5. Query the deployment records:

```powershell
Invoke-RestMethod http://localhost:18080/deployments | ConvertTo-Json -Depth 20
```

Expected:

- one WP3 submission is made;
- one local Deployment record is created for the workflow;
- `solution_id` matches the automatically saved solution;
- the UI reports **Deployment submitted**.

## 14. Deployment monitoring test

1. Open <http://localhost:13000/deployments>.
2. Select **Refresh statuses**.
3. Open the new run.
4. Compare workflow and task state with WP3.
5. Archive and restore a disposable deployment if lifecycle testing is in scope.

API verification:

```powershell
$WorkflowId = "<workflow-id>"
Invoke-RestMethod "http://localhost:18080/orchestrator/workflows/$WorkflowId" |
  ConvertTo-Json -Depth 20
Invoke-RestMethod "http://localhost:18080/orchestrator/workflows/$WorkflowId/tasks" |
  ConvertTo-Json -Depth 20
```

Expected: the local record can be synchronized, task status is visible, and archive operations preserve history.

## 15. DataReference inspection test

1. Open a deployment containing task input or output references.
2. Select a DataReference.
3. Preview inline JSON/CSV or an accessible HTTP reference.
4. Record the behavior for file, gRPC, S3, or artifact references.

Direct API example:

```powershell
$Body = @{
  protocol = "inline"
  uri = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes('{"result":"ok"}')
  )
  format = "json"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:18080/data-references/preview `
  -ContentType "application/json" `
  -Body $Body |
  ConvertTo-Json -Depth 20
```

Expected: supported content is rendered as structured evidence; unsupported protocols return an explicit limitation rather than fabricated content.

## 16. Expected results and interpretation

| Scenario | Expected result |
|---|---|
| Blank workflow | Design blocked |
| Rejected service | `ineligible` |
| Approved service with stopped runtime | `unavailable` |
| Invalid host, port, or health path | `misconfigured` |
| Deleted catalogue reference | `unknown` |
| Eligible service returning 2xx | `ready` |
| Canvas change after readiness | Old readiness invalidated |
| Direct blocked submission | HTTP `409 Conflict` |
| Ready preparation | Separate confirmation required |
| Confirmed deployment | WP3 submission and linked local record |

Runtime readiness is not operation-precondition validation. In particular, `AnalyzeData` alone may be healthy and eligible, then fail during execution with:

```text
No input file provided
```

Use the complete Portuguese pipeline when testing execution that requires upstream data. The repository does not contain evidence that the full Portuguese regression has been completed for every release candidate.

## 17. Defect-reporting template

```markdown
### Summary
One sentence describing the defect.

### Environment
- Solution Studio commit:
- WP3 commit:
- Node-service commit(s):
- Windows version:
- Docker Desktop / Docker Engine:
- Browser:
- Persona preview:

### Preconditions
- Service ID(s) and governance state:
- Solution ID:
- Workflow ID / deployment ID:
- Containers running:

### Steps to reproduce
1.
2.
3.

### Expected result

### Actual result

### Readiness evidence
- Overall status:
- Per-service status/message:
- Checked timestamp:

### Logs and screenshots
Attach relevant UI screenshots and sanitized logs. Do not include credentials or tokens.

### Reproducibility
Always / Intermittent / Once

### Severity
Blocking / Major / Minor / Cosmetic
```

## Related documents

- [Repository README](../README.md)
- [Current capabilities](CURRENT_CAPABILITIES.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
- [MVP release notes](MVP_RELEASE_NOTES.md)
