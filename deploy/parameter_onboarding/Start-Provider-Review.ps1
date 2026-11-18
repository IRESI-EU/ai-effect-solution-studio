# Read this script before running it. It creates a NEW worktree and review data.
# No package installation, old checkout switch, Docker change or production write.
[CmdletBinding()]
param(
    [string]$Checkout = 'C:\Users\as\OneDrive - Maynooth University\Projects_2025\AI-effect\Web_Portal\ai-effect-solution-studio\ai-effect-solution-studio-production-ui',
    [string]$Python = ''
)
$ErrorActionPreference = 'Stop'
$branch = 'codex/reusable-provider-onboarding-20261117'
if (-not (Test-Path (Join-Path $Checkout '.git'))) { throw 'Choose the existing Portal checkout with -Checkout. Nothing was started.' }
if (-not $Python) { $Python = Join-Path $Checkout '.venv\Scripts\python.exe' }
if (-not (Test-Path $Python)) { throw 'Existing Python environment was not found. Pass its python.exe using -Python. No dependencies were installed.' }
& $Python -c 'import fastapi, sqlalchemy, pydantic_settings, uvicorn, openai'
if ($LASTEXITCODE -ne 0) { throw 'The selected Python environment lacks required Portal packages. No packages were installed and nothing was started.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js was not found. Nothing was started.' }
if (-not ((Test-Path (Join-Path $Checkout 'node_modules\next\dist\bin\next')) -or (Test-Path (Join-Path $Checkout 'apps\web\node_modules\next\dist\bin\next')))) { throw 'The original checkout has no existing Next.js dependencies to reuse. No packages were installed.' }
$parent = Split-Path $Checkout -Parent
$review = Join-Path $parent 'ai-effect-provider-review-20261118'
$data = Join-Path $parent 'ai-effect-provider-review-data-20261118'
& git -C $Checkout fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch the review branch. Existing work was not changed.' }
$expected = (& git -C $Checkout rev-parse "origin/$branch").Trim()
if ($LASTEXITCODE -ne 0) { throw 'Review branch identity could not be read.' }
if (Test-Path $review) {
    $current = (& git -C $review rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $current -ne $expected) { throw 'The separate review folder already exists at another version. It was preserved; no reset or overwrite was attempted.' }
} else {
    & git -c core.longpaths=true -C $Checkout worktree add --detach $review "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated review checkout. Existing work was preserved.' }
}
Write-Host 'Starting a SEPARATE review workspace. The retained demo on 23124 is unchanged.'
Write-Host 'Review sign-in will be http://127.0.0.1:23125/login AFTER the launcher reports running.'
Write-Host 'Keep this window open. Ctrl+C stops only the new review processes.'
$launcher = Join-Path $review 'deploy\parameter_onboarding\review_workspace.py'
& $Python $launcher launch --directory $data --dependencies-from $Checkout --open-browser
if ($LASTEXITCODE -ne 0) { throw "The review workspace did not start. Its logs are under $data. No old service was stopped or replaced." }
