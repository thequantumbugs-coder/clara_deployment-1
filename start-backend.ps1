# Start CLARA backend. Run from project root (clara_deployment-1).
# Frees the backend port if in use, then starts backend so the frontend can connect.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Read PORT from .env (default 6969)
$port = 6969
if (Test-Path ".env") {
    $line = Get-Content ".env" | Where-Object { $_ -match '^\s*PORT\s*=\s*(\d+)' } | Select-Object -First 1
    if ($line -match 'PORT\s*=\s*(\d+)') { $port = [int]$matches[1] }
}

Write-Host "Backend port: $port (from .env or default 6969)"
Write-Host "Checking if port $port is in use..."

$listeners = netstat -ano | Select-String ":\s*$port\s+.*LISTENING"
if ($listeners) {
    $pids = $listeners | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
    foreach ($procId in $pids) {
        Write-Host "Stopping process $procId holding port $port..."
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual env not found. Run: python -m venv .venv && .\.venv\Scripts\pip install -r backend\requirements.txt"
}

Write-Host "Starting backend at http://0.0.0.0:$port ..."
& $venvPython backend\main.py
