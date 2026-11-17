# Portuguese retained-demo result previews: verified

**PASS, 17 November2026.** The retained port23124 application was updated only
for the owner-authorized preview repair. All further development remains paused
for the18 November meeting. The published meeting freeze and unrelated work are
preserved; this is not a staging/production installation or another algorithm run.

Source fix: [0660430724007c537c44d0985163043c5fa5688f instructions](https://github.com/IRESI-EU/ai-effect-solution-studio/blob/0660430724007c537c44d0985163043c5fa5688f/docs/PORTUGUESE_RESULT_PREVIEW_FIX_2026-11-17.md).
Only its three API source changes and two regression-suite changes were backported
onto the retained serving source `25dda8b1e9bfda78790dbe27e1b1ab38e7556c2b`.
No later production-portability or staging application changes were installed.

## Actual installation

- Backport source commit: `de58dc98f581642339d753c8d3a228e97d94a1fb`.
- Serving API: `sha256:511b44899c6f437ad33c3cbfc514a31581cbc9dc240e54dcb02aaa7b1d4cc1b5`.
- Rollback API retained: `sha256:802fb23b14152d5043659b8e7c254926c87b5c26cbeade1cdced7acb3440ea6e`.
- Unchanged web: `sha256:a7ca1100fb5364ca876117a176b351f411bb330f5baa8dfe6a4f09de49d635ed`.
- Unchanged sidecar: `sha256:7709b05cb41329a2ef55a05816c82e2d9371cdde131ee92e2c0a31fc8247a8c6`.
- Unchanged original ML: `sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f`.

The existing pinned offline packager built **API only**, linux/amd64, with network
disabled/pullfalse, using the retained dependency image and Python base. No
dependency download, web build, schema migration or profile initialization occurred.
Changed-file syntax and preview-module imports passed with networking disabled.
Full-app import without its database cannot succeed because this retained source
initializes database metadata on import; actual startup was verified against the
retained PostgreSQL database. Startup and the application proxy returned200.

A fresh consistent57,412-byte PostgreSQL backup and readable table-of-contents,
original private Compose bytes, rollback image and all pre-update identities were
retained privately. Only `services.api.image` changed in that Compose. Installation
used `up -d --no-deps --no-build --pull never api`, with automatic rollback on
startup failure prepared. The API's ports, mounts, network and configuration were
preserved. Neither rollback nor a data restore was needed.

## Actual browser observations

Existing reviewer signed in normally, then refreshed
<http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results>.

| Visible action | Actual result |
| --- | --- |
| Technical task details → TrainModel Output References → Preview → View raw JSON output | PASS: JSON object containing the recorded opaque `model_ref` |
| GenerateData Output References → Preview | PASS: CSV table with DATETIME, SYNTHETIC_LOAD, SYNTHETIC_SOLAR, EXAMPLE; “Showing up to20rows” |
| Download generated CSV | PASS: actual browser download,41,826bytes; SHA-256 `553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540` |
| Historical status/settings | Completed; TrainModel observed epochs2/batch4; GenerateData10sequences×100observations; same recorded model association |

[TrainModel JSON screenshot](screenshots/pt-trainmodel-preview-20261117.jpg) ·
[GenerateData CSV screenshot](screenshots/pt-generated-csv-preview-20261117.jpg).
These are actual rendered retained-demo pages, not synthetic test responses.
The CSV remains the historical completed count10 run's output; no new count20
design acquired results. Input/private-training previews and arbitrary HTTP
references remain unsupported. Only exact owned, signed task-output references
resolve through the existing capture validator; no remote URL fetch was enabled.

## Focused checks and preservation

`test_portuguese_evidence.py` + `test_owned_artifact_preview.py`: **47 passed**
in42.83seconds using the existing installed local environment. The tests use
isolated SQLite/synthetic signed fixtures and network-denial doubles, not live
algorithm execution. Existing646 deprecation warnings remain. No unrelated suite
was run. Staged implementation/evidence secret scans passed.

All72 baseline runtime Python files matched the retained source before update.
Afterward all59 other containers retained their exact IDs, images, mounts and
running/stopped states, including web/sidecar/ML/workers and all four HTTPS staging
services. The two workflow-qualified task identities remain `task_030152d9` and
`task_f6c5c14e`; both are completed. All saved designs/deployments, nine completed
journal jobs, closed authorizations, model mappings, output evidence and queues
remain unchanged. Provider disconnected; supervision OFF; canonical ledger28/28
closed and byte/record identical, zero outstanding. **Zero new workflows,
training, generation, scopes or provider requests.** Production was not changed.

[Sanitized verification record](../deploy/portuguese_sandbox/result-preview-verification-20261117.json).
Private evidence/backup and the repair-only freeze supplement live in the original
checkout's `local-backups/pt-result-preview-20261117`, including
`freeze-manifest.private.json`. No credentials, raw database, journal or training
bytes are published. Existing reviewer credentials remain in the retained profile;
no account/password/permission changed. The primary demo remains available.
