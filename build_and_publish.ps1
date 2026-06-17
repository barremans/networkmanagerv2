# build_and_publish.ps1 - Networkmap_Creator
# Vraagt alle build-parameters vooraf, voert build.bat niet-interactief uit,
# en publiceert daarna via publish.ps1 naar GitHub.
# Run vanuit repo root:  .\build_and_publish.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$buildBat = Join-Path $Root "build.bat"
$publishPs = Join-Path $Root "publish.ps1"

if (-not (Test-Path $buildBat)) { throw "Niet gevonden: $buildBat" }
if (-not (Test-Path $publishPs)) { throw "Niet gevonden: $publishPs" }

# ============================================================
# Parameters vooraf vragen
# ============================================================

Write-Host ""
Write-Host "============================================================"
Write-Host "  Networkmap Creator - Build + Publish"
Write-Host "============================================================"
Write-Host ""

# Versie-bump
$bumpPart = ""
while ($bumpPart -notin @("patch", "minor", "major")) {
    $bumpPart = Read-Host "Versie verhogen? [patch/minor/major] (Enter = patch)"
    if ($bumpPart -eq "") { $bumpPart = "patch" }
}
Write-Host "[OK] Versie-bump: $bumpPart"

# Installer bouwen
$makeInstaller = ""
while ($makeInstaller -notin @("J", "N", "j", "n")) {
    $makeInstaller = Read-Host "Inno Setup installer bouwen? [J/N] (Enter = J)"
    if ($makeInstaller -eq "") { $makeInstaller = "J" }
}
$makeInstaller = $makeInstaller.ToUpper()
Write-Host "[OK] Installer: $makeInstaller"

# Signing
$doSign = ""
while ($doSign -notin @("J", "N", "j", "n")) {
    $doSign = Read-Host "Binaries signen? [J/N] (Enter = J)"
    if ($doSign -eq "") { $doSign = "J" }
}
$doSign = $doSign.ToUpper()
Write-Host "[OK] Signing: $doSign"

# Publiceren naar GitHub
$doPublish = ""
while ($doPublish -notin @("J", "N", "j", "n")) {
    $doPublish = Read-Host "Publiceren naar GitHub na build? [J/N] (Enter = J)"
    if ($doPublish -eq "") { $doPublish = "J" }
}
$doPublish = $doPublish.ToUpper()
Write-Host "[OK] Publiceren: $doPublish"

Write-Host ""
Write-Host "------------------------------------------------------------"
Write-Host "  Samenvatting:"
Write-Host "    Versie-bump : $bumpPart"
Write-Host "    Installer   : $makeInstaller"
Write-Host "    Signing     : $doSign"
Write-Host "    Publiceren  : $doPublish"
Write-Host "------------------------------------------------------------"
$bevestig = Read-Host "Starten? [J/N]"
if ($bevestig.ToUpper() -ne "J") {
    Write-Host "Afgebroken."
    exit 0
}

# ============================================================
# [STEP 1/2] Build uitvoeren via omgevingsvariabelen
# ============================================================

Write-Host ""
Write-Host "[STEP 1/2] Build starten..."

# Schrijf een tijdelijk wrapper .bat bestand dat variabelen zet en build.bat aanroept
# Dit vermijdt alle PowerShell -> cmd argument-parsing problemen
$wrapperPath = Join-Path $Root "_build_wrapper.bat"
$wrapperContent = "@echo off`r`n"
$wrapperContent += "set NM_BUMP_PART=$bumpPart`r`n"
$wrapperContent += "set NM_MAKE_INSTALLER=$makeInstaller`r`n"
$wrapperContent += "set NM_DO_SIGN=$doSign`r`n"
$wrapperContent += "call `"$buildBat`"`r`n"
$wrapperContent += "exit /b %ERRORLEVEL%`r`n"
[System.IO.File]::WriteAllText($wrapperPath, $wrapperContent, [System.Text.Encoding]::ASCII)

Write-Host "--- Wrapper inhoud ---"
Get-Content $wrapperPath | ForEach-Object { Write-Host $_ }
Write-Host "--- Einde wrapper ---"

$buildExitCode = 0
& cmd.exe /c "`"$wrapperPath`""
$buildExitCode = $LASTEXITCODE

Remove-Item $wrapperPath -ErrorAction SilentlyContinue

# Omgevingsvariabelen opruimen (waren al gezet als fallback)
Remove-Item Env:\NM_BUMP_PART      -ErrorAction SilentlyContinue
Remove-Item Env:\NM_MAKE_INSTALLER -ErrorAction SilentlyContinue
Remove-Item Env:\NM_DO_SIGN        -ErrorAction SilentlyContinue

if ($buildExitCode -ne 0) {
    throw "Build faalde (exitcode $buildExitCode). Zie output hierboven."
}

Write-Host "[STEP 1/2] Build geslaagd."

# ============================================================
# [STEP 2/2] Publiceren (optioneel)
# ============================================================

if ($doPublish -eq "J") {
    if ($makeInstaller -ne "J") {
        Write-Host "[WARN] Installer niet gebouwd - publiceren overgeslagen."
    }
    else {
        Write-Host ""
        Write-Host "[STEP 2/2] Publiceren via publish.ps1..."
        & powershell -ExecutionPolicy Bypass -File $publishPs
        if ($LASTEXITCODE -ne 0) { throw "Publish faalde (exitcode $LASTEXITCODE)." }
        Write-Host "[STEP 2/2] Publiceren geslaagd."
    }
}
else {
    Write-Host "[STEP 2/2] Publiceren overgeslagen (keuze gebruiker)."
}

Write-Host ""
Write-Host "============================================================"
Write-Host "[DONE] Build + Publish afgerond."
Write-Host "============================================================"