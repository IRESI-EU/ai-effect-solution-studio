param([Parameter(Mandatory=$true)][string]$Profile)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$profilePath = (Resolve-Path -LiteralPath $Profile).Path
$logs = Split-Path -Parent $profilePath
$python = (Resolve-Path (Join-Path $workspace '../../.venv/Scripts/python.exe')).Path
$node = (Get-Command node -ErrorAction Stop).Source
$tsPath = Join-Path $workspace 'apps/web/tsconfig.json'
$nextEnvPath = Join-Path $workspace 'apps/web/next-env.d.ts'
$tsBefore = [System.IO.File]::ReadAllBytes($tsPath)
$nextEnvBefore = [System.IO.File]::ReadAllBytes($nextEnvPath)
if (!(Test-Path -LiteralPath (Join-Path $profilePath 'prepared-human.json'))) { throw 'Prepare the disposable profile first; do not recreate an existing database' }
foreach ($port in @(23123,28187)) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$port)
    try { $probe.Start() } finally { $probe.Stop() }
}
# Detached native processes, fixed loopback ports, retained production .next untouched.
$apiArgs = '"' + (Join-Path $PSScriptRoot 'harness.py') + '" serve --profile "' + $profilePath + '"'
$api = Start-Process -FilePath $python -ArgumentList $apiArgs -WorkingDirectory $workspace -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logs 'api.stdout.log') -RedirectStandardError (Join-Path $logs 'api.stderr.log')
$env:INTERNAL_API_URL = 'http://127.0.0.1:28187'
$env:NEXT_BUILD_DIR = '.next-controls-20261106'
$env:NEXT_PUBLIC_ENVIRONMENT_LABEL = 'Offline controls walkthrough: prepared synthetic proposal. No live AI or execution.'
$env:NEXT_TELEMETRY_DISABLED = '1'
$webArgs = '"' + (Join-Path $workspace 'apps/web/node_modules/next/dist/bin/next') + '" dev --webpack --hostname 127.0.0.1 --port 23123'
$web = Start-Process -FilePath $node -ArgumentList $webArgs -WorkingDirectory (Join-Path $workspace 'apps/web') -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logs 'web.stdout.log') -RedirectStandardError (Join-Path $logs 'web.stderr.log')
@{api_pid=$api.Id;web_launcher_pid=$web.Id;api_port=28187;web_port=23123;web_output='.next-controls-20261106';profile=$profilePath;source=(git -C $workspace rev-parse HEAD)} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logs 'startup-record.json')
Write-Output 'Started only the disposable SQLite API and isolated Next development server; inspect local logs for readiness.'
# Next dev adjusts its generated type includes on startup. Preserve the original
# tracked configuration; the isolated output still contains dev-generated types.
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$ready = $false
while ($watch.Elapsed.TotalSeconds -lt 45) {
    try {
        $response = Invoke-WebRequest 'http://127.0.0.1:23123/login' -TimeoutSec 3 -UseBasicParsing
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (!$ready) { throw 'Web did not become ready within the bounded check. Inspect retained logs; do not relaunch automatically.' }
$generatedTs = Get-Content -LiteralPath $tsPath -Raw | ConvertFrom-Json
$generatedTs.include = @($generatedTs.include | Where-Object { $_ -notin @('.next-controls-20261106/types/**/*.ts','.next-controls-20261106/dev/types/**/*.ts') })
$originalTs = [System.Text.Encoding]::UTF8.GetString($tsBefore) | ConvertFrom-Json
if (($generatedTs | ConvertTo-Json -Depth 20 -Compress) -ne ($originalTs | ConvertTo-Json -Depth 20 -Compress)) {
    throw 'Unexpected concurrent tsconfig change; preserve it and inspect before restoring anything'
}
$generatedNext = [System.IO.File]::ReadAllText($nextEnvPath).Replace('.next-controls-20261106/dev/', '.next/').Replace('.next-controls-20261106/', '.next/')
if ($generatedNext.Replace("`r`n","`n") -ne [System.Text.Encoding]::UTF8.GetString($nextEnvBefore).Replace("`r`n","`n")) {
    throw 'Unexpected generated type-reference change; inspect before restoring anything'
}
[System.IO.File]::WriteAllBytes($tsPath,$tsBefore)
[System.IO.File]::WriteAllBytes($nextEnvPath,$nextEnvBefore)
Write-Output 'Login responds; original tracked TypeScript configuration restored byte-for-byte.'
