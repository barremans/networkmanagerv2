# build_and_publish.ps1 — build.bat + publish.ps1
# Run vanuit repo root:  .\build_and_publish.ps1

$ErrorActionPreference = "Stop"

# Repo root = map waar dit script staat
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$buildBat = Join-Path $Root "build.bat"
$publishPs = Join-Path $Root "publish.ps1"

if (-not (Test-Path $buildBat)) { throw "Niet gevonden: $buildBat" }
if (-not (Test-Path $publishPs)) { throw "Niet gevonden: $publishPs (maak eerst publish.ps1)" }

Write-Host "[STEP 1/2] Build starten: $buildBat"
# Start build interactief en wacht tot klaar
$proc = Start-Process -FilePath $buildBat -WorkingDirectory $Root -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "Build faalde (exitcode $($proc.ExitCode))." }

Write-Host "[STEP 2/2] Publiceren via: $publishPs"
& powershell -ExecutionPolicy Bypass -File $publishPs
if ($LASTEXITCODE -ne 0) { throw "Publish faalde (exitcode $LASTEXITCODE)." }

Write-Host ""
Write-Host "============================================================"
Write-Host "[DONE] Build + Publish afgerond."
Write-Host "============================================================"