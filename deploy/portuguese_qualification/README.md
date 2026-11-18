# Disposable Portuguese qualification

This harness uses the already installed pinned CPU DGAN image. It creates only a
new Docker project with private raw ML, fresh nocopy model/state/evidence volumes,
random credentials, an input fixture and read-only normal qualification exports.
It does not install the draft stack, activate contracts, submit normal Portal
workflows, contact paid providers or reuse retained experiment storage.

Read [the Windows evidence and limitations](../../docs/WINDOWS_PORTUGUESE_QUALIFICATION_2026-11-18.md)
before running it. A completed experiment must be inspected, not automatically
rerun. Preserve uncertain operations and reconcile their upstream outcome.

From an isolated Portal worktree with the original Python environment available:

```powershell
..\..\.venv\Scripts\python.exe deploy/portuguese_qualification/qualify_local.py prepare --directory ..\NEW-PRIVATE-DIRECTORY --wp3 ..\pw --expected-tree 45ea7dbf869f5883aa7ef6de90d859cb5c586a23 --review ..\provider-review-ready-20261118 --training-service-name 'model_trainer1 / TrainModel' --generation-service-name 'data_generator1 / GenerateData' --fixture-only
..\..\.venv\Scripts\python.exe deploy/portuguese_qualification/qualify_local.py run --directory ..\NEW-PRIVATE-DIRECTORY --fixture-only
```

The service names select explicitly named review catalogue copies; they are not
service-ID exceptions in Portal code. The expected tree must be the separately
reviewed WP3 release being tested. Contract identities and task/volume names are
generated for the new experiment. Fixture bounds 1–32 and synthetic data are
software tests, never partner-approved scientific limits/defaults. Port 28190
must be free. Its Control API requires the new private bearer credential.

`prepare` freezes tracked connector bytes into private source storage before
mounting them read-only. `ml_probe.py` wraps the unchanged API's real DGAN calls,
records effective config and saved tensors, and loads only freshly generated
model files. No model is replaced with a double. `run` refuses existing work by
default. Explicit recovery switches have narrowly checked pre-dispatch conditions;
they never clear journals or retry an unresolved algorithm dispatch.

## Portal result inspection

The default remote-result guard remains closed. In a separately reviewed runtime,
set `OWNED_CONTROL_TARGETS_FILE` to an ignored private operator file shaped as:

```json
{
  "targets": [{
    "runtime_destination": "http://private-orchestrator:8000",
    "base_url": "http://private-configured-connector:8080",
    "token": "<new private Control bearer credential>"
  }]
}
```

Use a base URL without path/trailing slash, query, fragment or embedded credentials.
Keep the file operator-owned and readable only by the API service; mount it
read-only in a container. Never check it into Git or return it to a browser.
The target must match both the immutable submitted runtime and its compiled
endpoint. Normal deployment ownership and server-observed task outputs are still
required. The reader derives only that task's receipt/data paths, uses no proxy
inheritance or redirects, bounds reads, validates byte/CSV counts and pins the
receipt through existing receipt rows. There is no general remote URL fetch.

Authenticated delivery receipts do not establish algorithm consumption. Model
qualification evidence is separate. Draft capability installation does not make
the contract active or enable a designer Run. The optional
`test_portuguese_owned_live_result.py` reads existing real qualification outputs
without dispatch, using explicit SQLite submission/task-observation fixtures.
