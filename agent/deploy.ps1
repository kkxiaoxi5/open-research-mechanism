# One-click local deployment for mechanism-agent (Windows PowerShell).
#
#   .\deploy.ps1          init (if needed) + seed demo + start console
#   .\deploy.ps1 -Port 9000
#   .\deploy.ps1 -Stop
#
# Zero dependencies: Python >= 3.11 standard library only.
param([int]$Port = 8765, [switch]$Stop)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$HomeDir = if ($env:MECH_HOME) { $env:MECH_HOME } else { Join-Path $PWD "mech-state" }
$PidFile = Join-Path $PWD ".mech-agent.pid"

if ($Stop) {
    if (Test-Path $PidFile) {
        Stop-Process -Id (Get-Content $PidFile) -ErrorAction SilentlyContinue
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        Write-Host "stopped"
    } else { Write-Host "not running" }
    return
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host "python not found (need >= 3.11)"; exit 1 }

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "port $Port is already in use by process $($listener.OwningProcess) — stop the old console first:"
    Write-Host "  .\deploy.ps1 -Stop    (or: Stop-Process -Id $($listener.OwningProcess))"
    exit 1
}

$env:PYTHONPATH = Join-Path $PWD "src"
function Invoke-Py {
    param([string[]]$Args_)
    & python @Args_
    if ($LASTEXITCODE -ne 0) {
        Write-Host "command failed (exit $LASTEXITCODE): python $($Args_ -join ' ')"
        exit $LASTEXITCODE
    }
}
if (-not (Test-Path (Join-Path $HomeDir "board.jsonl"))) {
    Invoke-Py "-m", "mechanism_agent", "--home", $HomeDir, "init"
    Invoke-Py "-m", "mechanism_agent", "--home", $HomeDir, "seed-demo"
    Write-Host "seeded demo data (leaves D1-D3, two tickets)"
}
$p = Start-Process -PassThru -NoNewWindow python -ArgumentList `
    "-m", "mechanism_agent", "--home", $HomeDir, "serve", "--port", $Port
$p.Id | Out-File $PidFile -Encoding ascii
Start-Sleep -Seconds 1
Write-Host "mechanism-agent console: http://127.0.0.1:$Port"
Write-Host "state dir: $HomeDir   stop: .\deploy.ps1 -Stop"
