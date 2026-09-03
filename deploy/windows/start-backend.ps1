$ErrorActionPreference = "Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\backend")).Path
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$startScript = Join-Path $backendRoot "scripts\start_production.py"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Backend virtual environment Python was not found."
}

Set-Location -LiteralPath $backendRoot
& $pythonPath $startScript --check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
& $pythonPath $startScript
exit $LASTEXITCODE
