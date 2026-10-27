# Steward on Windows, in one go (PowerShell, from the project folder):
#   powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1 -AtlasDir D:\path\to\Hackathon-GenAI-public
# - creates .venv and installs the Python dependencies
# - vendors the Meterless H-MEM reference, runs its conformance suite, starts H-MEM on :8787
# - copies the Zetaris and Nightshift settings from the Atlas checkout's .env / .settings.json (never printed)
# - starts the Brikk sources (Postgres :5434, S3 drive :9000) if Docker is running
# - runs the tests and the MCP smoke test
# Everything is logged in logs\setup-windows.log.
param([string]$AtlasDir = "")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root
New-Item -ItemType Directory -Force logs, data | Out-Null
Start-Transcript -Path (Join-Path $Root "logs\setup-windows.log") -Append | Out-Null
function Say($t) { Write-Host "`n==> $t" -ForegroundColor Yellow }
$Py = Join-Path $Root ".venv\Scripts\python.exe"

Say "1/6 Python dependencies"
if (-not (Test-Path $Py)) { python -m venv .venv }
& $Py -m pip install -q --upgrade pip
& $Py -m pip install -q -r requirements.txt

Say "2/6 Settings (.env)"
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
function Set-EnvVar($key, $value) {
  if (-not $value) { return }
  $lines = @(Get-Content ".env" | Where-Object { $_ -notmatch "^$key=" })
  $lines += "$key=$value"
  Set-Content -Path ".env" -Value $lines -Encoding UTF8
}
if ($AtlasDir -and (Test-Path (Join-Path $AtlasDir ".env"))) {
  $atlas = @{}
  foreach ($l in Get-Content (Join-Path $AtlasDir ".env")) {
    if ($l -match '^\s*([A-Z_]+)\s*=\s*(.*)$') { $atlas[$Matches[1]] = $Matches[2].Trim() }
  }
  foreach ($k in "ZETARIS_BASE_URL", "ZETARIS_REST_URL", "ZETARIS_ORG_ID", "ZETARIS_API_KEY",
                 "METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_STATE_DIR") {
    if ($atlas[$k]) { Set-EnvVar $k $atlas[$k] }
  }
  $settings = Join-Path $AtlasDir ".settings.json"
  if (Test-Path $settings) {
    $s = Get-Content $settings -Raw | ConvertFrom-Json
    if ($s.meterless_runtime_token) { Set-EnvVar "METERLESS_RUNTIME_TOKEN" $s.meterless_runtime_token }
    if ($s.meterless_base_url) { Set-EnvVar "METERLESS_BASE_URL" $s.meterless_base_url }
  }
  Write-Host "Zetaris and Nightshift settings copied from $AtlasDir (values not shown)."
} else {
  Write-Host "No -AtlasDir: fill ZETARIS_API_KEY and METERLESS_RUNTIME_TOKEN in .env yourself."
}
Set-EnvVar "SAMPLE_MODE" "false"
Set-EnvVar "HMEM_URL" "http://127.0.0.1:8787"

Say "3/6 Meterless H-MEM (reference implementation + our service with supersedes)"
$Meterless = Join-Path $Root "vendor\meterless"
if ($AtlasDir -and (Test-Path (Join-Path $AtlasDir "external\meterless\engines\hmem"))) { $Meterless = Join-Path $AtlasDir "external\meterless" }
if (-not (Test-Path (Join-Path $Meterless "engines\hmem"))) { git clone --depth 1 https://github.com/Meterless/Meterless.git $Meterless }
$V = Join-Path $Root "hmem-service\vendor"
if (-not (Test-Path (Join-Path $V "hmem-reference\src"))) {
  New-Item -ItemType Directory -Force $V | Out-Null
  robocopy (Join-Path $Meterless "engines\hmem\reference") (Join-Path $V "hmem-reference") /E /XD node_modules /NFL /NDL /NJH /NJS | Out-Null
  robocopy (Join-Path $Meterless "engines\hmem\conformance") (Join-Path $V "hmem-conformance") /E /NFL /NDL /NJH /NJS | Out-Null
  Copy-Item (Join-Path $Meterless "LICENSE") (Join-Path $V "LICENSE-meterless") -Force
}
Push-Location hmem-service
if (-not (Test-Path node_modules)) { npm install --silent }
$env:HMEM_IMPL = Join-Path $V "hmem-reference\src\index.ts"
npx tsx vendor/hmem-conformance/runner.ts | Select-Object -Last 2
Pop-Location
try { Invoke-RestMethod http://127.0.0.1:8787/health -TimeoutSec 2 | Out-Null; Write-Host "H-MEM already running" }
catch {
  $env:HMEM_DIR = Join-Path $Root "data\hmem"
  Start-Process -WindowStyle Minimized -WorkingDirectory (Join-Path $Root "hmem-service") -FilePath "cmd.exe" `
    -ArgumentList "/c npx tsx server.ts > ..\logs\hmem.log 2>&1"
  Start-Sleep -Seconds 6
  try { Invoke-RestMethod http://127.0.0.1:8787/health -TimeoutSec 3 | Out-Null; Write-Host "H-MEM started on :8787" }
  catch { Write-Host "H-MEM did not start: see logs\hmem.log" }
}

Say "4/6 Brikk sources for Zetaris (Postgres + S3 drive)"
try { docker info *> $null; docker compose up -d brikk-db drive drive-init; Write-Host "brikk-db :5434, drive :9000" }
catch { Write-Host "Docker is not running: start Docker Desktop and rerun." }

Say "5/6 Nightshift lanes (served model checked against Nemotron)"
& $Py scripts\configure_nightshift.py

Say "6/6 Checks"
& $Py -m pytest -q
& $Py scripts\mcp_smoke.py
Write-Host "`nNext: python scripts\zetaris\run_steward_sql.py   then   python run.py serve   (console: http://localhost:8000/console)"
Stop-Transcript | Out-Null
