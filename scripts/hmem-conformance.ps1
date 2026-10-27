# Fetches the Meterless repository into external/ (git-ignored) and runs the
# official H-MEM conformance suite against the reference implementation.
# Usage, from the project folder:  powershell -File scripts\hmem-conformance.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$repo = Join-Path $root "external\meterless"

if (-not (Test-Path $repo)) {
    git clone --depth 1 https://github.com/Meterless/Meterless.git $repo
}

Push-Location (Join-Path $repo "engines\hmem\reference")
try {
    if (-not (Test-Path "node_modules")) {
        npm ci --ignore-scripts --no-audit --no-fund
    }
    npx tsx ../conformance/runner.ts
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
