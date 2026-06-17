$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$issFile = Join-Path $projectRoot "installer.iss"
$distExe = Join-Path $projectRoot "dist\Background Remover.exe"
$installerExe = Join-Path $projectRoot "installer\Background Remover Setup.exe"

if (!(Test-Path $distExe)) {
    throw "Missing EXE. Build it first: $distExe"
}

$candidatePaths = @(
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$iscc = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (!$iscc) {
    throw "Could not find ISCC.exe for Inno Setup 6."
}

Write-Host "Using Inno Setup compiler:"
Write-Host $iscc
Write-Host ""

Push-Location $projectRoot
try {
    & $iscc $issFile
}
finally {
    Pop-Location
}

Write-Host ""
if (Test-Path $installerExe) {
    Write-Host "Installer created:"
    Write-Host $installerExe
}
else {
    throw "Installer build finished but the output file was not found at $installerExe"
}
