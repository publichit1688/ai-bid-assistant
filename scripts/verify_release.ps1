$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$pytestBaseTemp = ".pytest-tmp-release-$PID-$([guid]::NewGuid().ToString('N'))"
$pipAuditCache = ".pytest-pip-audit-cache-$PID-$([guid]::NewGuid().ToString('N'))"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Project backend/.venv Python was not found."
}

Push-Location $backendRoot
try {
    & $pythonPath -m compileall -q app scripts
    if ($LASTEXITCODE -ne 0) { throw "Python compile check failed." }
    & $pythonPath -m pytest "--basetemp=$pytestBaseTemp"
    if ($LASTEXITCODE -ne 0) { throw "Backend regression failed." }
    & $pythonPath scripts\scan_secrets.py
    if ($LASTEXITCODE -ne 0) { throw "Secret scan failed." }
    & $pythonPath -m pip_audit --local --progress-spinner off --cache-dir $pipAuditCache
    if ($LASTEXITCODE -ne 0) { throw "Python dependency audit failed." }
}
finally {
    Pop-Location
}

Push-Location $frontendRoot
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    npm audit --omit=dev --audit-level=low
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency audit failed." }
}
finally {
    Pop-Location
}

Write-Host "V1 automated release checks passed."
