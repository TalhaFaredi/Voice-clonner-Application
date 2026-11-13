# Run from any directory. All paths resolve inside this standalone project.
param([ValidateSet('api','worker','frontend')][string]$Service='api')
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run uv sync --extra worker from the project folder first.' }
if ($Service -eq 'frontend') {
    Push-Location (Join-Path $taskRoot 'frontend')
    try { & $taskPython serve.py } finally { Pop-Location }
} else {
    Push-Location (Join-Path $taskRoot 'backend')
    try {
        if ($Service -eq 'worker') { & $taskPython -m app.worker }
        else { & $taskPython run.py }
    } finally { Pop-Location }
}
