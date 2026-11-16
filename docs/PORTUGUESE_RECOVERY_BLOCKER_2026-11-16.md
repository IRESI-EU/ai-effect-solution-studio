# Retained Portuguese application recovery — 2026-11-16

**Blocked before engine startup. Packaging, live preservation, PostgreSQL test
execution and fresh Builder acceptance have not passed. Execution stays disabled.**

Starting clean review heads matched Portal
`862c42dd471c76be3dc27d11d8c29b2d6a0304fe` and maintained WP3
`17f32be413fe64532373f70d8b862002c3427a8c`. No unrelated work was reset.
This record supplements the [prepared supervised milestone](PORTUGUESE_SUPERVISED_PREPARATION_2026-11-16.md);
it does not change the historical completion evidence.

## Demonstrated startup failure

- Context remains desktop-linux. Desktop/backend processes were stopped; Windows
  WSLService and vmcompute were running. The retained docker-desktop, Ubuntu and
  Ubuntu-24.04 distributions were stopped. The initial sandboxed WSL check's
  E_ACCESSDENIED did not recur in the normal host check.
- There was 66.53 GiB free on C:, so low disk space is not the demonstrated blocker.
- One normal supported `docker desktop start --timeout 30` was issued. It ended
  with **Docker Desktop terminated unexpectedly**. No repeated launch/restart,
  service reset, settings reset, reinstall, update, WSL unregister or disk operation.
- The backend fails **before initializing the Linux engine** while saving its
  settings: rename of settings-store.json.tmp-* over
  `C:\Users\as\AppData\Roaming\Docker\settings-store.json` returns **The system
  cannot find the path specified**. A separate marlin event-file rename fails
  similarly. The missing engine pipe is a consequence of this earlier failure.

Existing settings were privately copied and ACL metadata preserved before probes.
The JSON parses; settings and its parent exist, have ordinary file/directory
attributes, are not junctions/reparse points and resolve to the expected local
paths. Case sensitivity is disabled. The recorded directory ACL grants the
current account full control. No ACL, backend choice, data-disk location or
configuration value was changed.

| Disposable probe from this session | Observed result |
| --- | --- |
| Create/write/read/delete in Docker settings directory | Works |
| Python rename / replace existing destination there | WinError 3, path not found |
| Native PowerShell Rename-Item there | Could not find a part of the path |
| Rename in a new child under that directory | WinError 3 |
| Rename in AppData\Roaming itself | WinError 3 |
| Rename in workspace or AppData\Local\Temp | Passes |
| Extended Windows path spelling | Same failure |

Only uniquely named disposable files/subdirectory were used and removed. Real
settings bytes remain identical to their private backup. Inherited duplicate
separators were ruled out. The tested process token is not restricted or an app
container. No matching Defender block event was found; Controlled Folder Access
was observed in audit mode. These facts do **not** identify a particular security
product, filesystem driver or corruption as the cause. Read-only filter-driver
listing requires administrator access and was denied. Changing permissions or
disabling security is not justified by the evidence.

The installed signed com.docker.diagnose.exe completed **one local-only gather**
in 86 seconds, producing a 3,672,909-byte ZIP. No diagnostic upload was requested.
Private logs, settings/ACL backup and probe summaries are in the original checkout's
`local-backups/pt-review-20261116`. Diagnostic ZIP (private; do not publish):
`C:\Users\as\AppData\Local\Temp\pt-docker-diagnostics-c677ecaa81ed44bd92fcfbc41d089f2b.zip`.

Installed CLI/help and current official Docker guidance were used:
[normal bounded start](https://docs.docker.com/reference/cli/docker/desktop/start/),
[diagnostic collection](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/).

## Required next operator observation

Test a disposable rename in a **normal PowerShell window outside Codex**. This
distinguishes the host condition from this automation context; the cause is not
yet established outside this session. No real Docker setting is touched:

```powershell
$probe = Join-Path $env:APPDATA ('codex-rename-check-' + [guid]::NewGuid() + '.tmp')
$renamed = $probe + '.renamed'
try {
    Set-Content -LiteralPath $probe -Value 'probe'
    Rename-Item -LiteralPath $probe -NewName ([IO.Path]::GetFileName($renamed)) -ErrorAction Stop
    'Rename passed'
} finally {
    if (Test-Path -LiteralPath $probe) { Remove-Item -LiteralPath $probe }
    if (Test-Path -LiteralPath $renamed) { Remove-Item -LiteralPath $renamed }
}
```

If it passes, try one normal Start-menu Docker launch outside Codex and report
whether Engine running appears; do not reset anything. If it fails, an administrator
must investigate the AppData\Roaming rename failure, using the exact error/path
and retained diagnostics. A filtered filesystem trace of the disposable rename
is the next diagnostic action; do not reset Docker, replace valid settings or
assume that a reboot is required. No reboot requirement has been established.

## Preservation and pending acceptance

Current local checks confirmed existing private compose is byte-identical to its
preparation record, settings unchanged, provider/grants/mode unmodified, and the
ledger unchanged at **25/25**, zero outstanding, SHA
`cf9fa12e87633b9e260d3983a3dd9e5c51df346c04237b3babd255ee66cd7d2b`.
No workflow submission, journal authorization, training, generation, provider
request, image build or profile update occurred. C: free space afterward was
66.41 GiB; no cleanup was performed.

Ports 23124 and 28188 remain unavailable. The Docker-held workflow, seven jobs,
models, artifact hashes, scopes, queues and container identities could not be
freshly checked. Last live observations remain the original 14 November record;
no current preservation pass is claimed. Retained image/configuration pins were
not replaced. No application source is currently verified as serving.

Prepared four PostgreSQL concurrency cases in the **existing** postgres_tests
suite: same/different saved designs and accepted/uncertain mocked dispatch.
They use that suite's newly allocated disposable *_test database, real reviewer
row locks and attempt records, and forbid unexpected HTTP. The test observes
pg_blocking_pids to verify actual serialization, then requires a single dispatch
and durable replay/uncertainty behavior. Source syntax parses. **These tests have
not run**: the retained PostgreSQL engine is unavailable. No database-identity
guard or production database behavior was relaxed, and no replacement database
or alternative stack was created.

After recovery, inspect automatic container starts first, keep workers stopped,
then complete preservation before backup/build/update. Follow
[CHAIN_RUNBOOK](../deploy/portuguese_sandbox/CHAIN_RUNBOOK.md) and
[SUPERVISED_RUNBOOK](../deploy/portuguese_sandbox/SUPERVISED_RUNBOOK.md).
Run the new PostgreSQL cases only against the suite-created disposable database
using installed dependencies; do not point tests at owner data.

Fresh empty-Builder assembly, Save/refresh/Validate, inspection-only browser/server
checks, image import smoke checks and current historical-results inspection remain
pending. No fresh design URL or exact frozen request/revision/hash exists yet.
Do not substitute an older prepared design or present an execution authorization
request before these prerequisites pass. The prior proposed 2/4/10, one-training/
one-generation scope remains only a proposal, not activated authority.
