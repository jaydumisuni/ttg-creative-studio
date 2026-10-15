$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$issFile = Join-Path $projectRoot "installer\creative_studio_core.iss"
$distExe = Join-Path $projectRoot "dist\TTG Creative Studio\TTG Creative Studio.exe"
if (!(Test-Path $distExe)) { throw "Build Creative Studio first: $distExe" }
$candidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (!$iscc) { throw "Inno Setup 6 required; cannot claim installer built" }
Push-Location $projectRoot
try {
    & $iscc $issFile
    if ($LASTEXITCODE -ne 0) { throw "Creative Studio installer compiler failed" }
} finally { Pop-Location }
$installer = Join-Path $projectRoot "dist\installer\TTG-Creative-Studio-Core-Setup.exe"
if (!(Test-Path $installer)) { throw "Installer missing after compilation: $installer" }
Write-Host "Creative Studio installer: $installer"
