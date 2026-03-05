# publish.ps1 — NetworkManagerV2 (release + asset + version.txt)
# Run vanuit de repo root:  .\publish.ps1
# Vereist: gh (ingelogd) + git

param(
    [string]$Owner = "barremans",
    [string]$Repo = "networkmanagerv2"
)

$ErrorActionPreference = "Stop"

# Repo root = map waar dit script staat (dynamisch)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# 1) Versie lezen uit app/version.py
$versionPy = Join-Path $Root "app\version.py"
if (-not (Test-Path $versionPy)) { throw "Niet gevonden: $versionPy" }

$txt = Get-Content $versionPy -Raw
$m = [regex]::Match($txt, '__version__\s*=\s*["''](?<v>\d+\.\d+\.\d+)["'']')
if (-not $m.Success) { throw "Kon __version__ niet vinden in app/version.py" }
$version = $m.Groups["v"].Value

$tag = "v$version"
$assetName = "Networkmap_Creator_setup_$version.exe"
$assetPath = Join-Path $Root ("dist\" + $assetName)

Write-Host "[INFO] Repo: $Owner/$Repo"
Write-Host "[INFO] Versie: $version"
Write-Host "[INFO] Tag: $tag"
Write-Host "[INFO] Asset: $assetPath"

# 2) Installer bestaat?
if (-not (Test-Path $assetPath)) {
    throw "Installer niet gevonden: $assetPath`nRun eerst build.bat en maak de installer."
}

# 3) Release bestaat? Anders maken. (release not found mag NIET crashen)
$releaseExists = $false
try {
    & gh release view $tag --repo "$Owner/$Repo" *> $null
    if ($LASTEXITCODE -eq 0) { $releaseExists = $true }
}
catch {
    $releaseExists = $false
}

if (-not $releaseExists) {
    Write-Host "[INFO] Release $tag bestaat nog niet. Maken..."
    & gh release create $tag --repo "$Owner/$Repo" --title "$tag" --notes "Release $tag"
    if ($LASTEXITCODE -ne 0) { throw "Aanmaken release $tag mislukt." }
}
else {
    Write-Host "[INFO] Release $tag bestaat al."
}

# 4) Upload asset (clobber)
Write-Host "[INFO] Uploaden asset..."
& gh release upload $tag "$assetPath" --repo "$Owner/$Repo" --clobber
if ($LASTEXITCODE -ne 0) { throw "Upload asset mislukt." }

# 5) Download URL opbouwen (stabiel)
$downloadUrl = "https://github.com/$Owner/$Repo/releases/download/$tag/$assetName"
Write-Host "[OK] Download URL: $downloadUrl"

# 6) version.txt (2 regels) schrijven in repo
$versionTxt = Join-Path $Root "releases\latest\version.txt"
$versionDir = Split-Path -Parent $versionTxt
if (-not (Test-Path $versionDir)) { New-Item -ItemType Directory -Path $versionDir -Force | Out-Null }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($versionTxt, "$version`n$downloadUrl", $utf8NoBom)

# 7) Commit + push version.txt
& git add "releases/latest/version.txt"
& git commit -m "Update version.txt to $version" *> $null
# 'nothing to commit' is ok; push blijft veilig
& git push

Write-Host ""
Write-Host "============================================================"
Write-Host "[DONE] Published $tag"
Write-Host "Release: https://github.com/$Owner/$Repo/releases/tag/$tag"
Write-Host "Version file: https://raw.githubusercontent.com/$Owner/$Repo/main/releases/latest/version.txt"
Write-Host "============================================================"