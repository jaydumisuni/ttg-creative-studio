$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$specFile = Join-Path $projectRoot "Background Remover.spec"
$distExe = Join-Path $projectRoot "dist\Background Remover.exe"

Write-Host "Building EXE from:"
Write-Host $specFile
Write-Host ""

Push-Location $projectRoot
try {
    pyinstaller --noconfirm --clean $specFile
}
finally {
    Pop-Location
}

Write-Host ""
if (Test-Path $distExe) {
    Write-Host "EXE created:"
    Write-Host $distExe
}
else {
    throw "PyInstaller finished but the EXE was not found at $distExe"
}
