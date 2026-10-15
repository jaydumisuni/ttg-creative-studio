$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$specFile = Join-Path $projectRoot "TTG Creative Studio.spec"
$distExe = Join-Path $projectRoot "dist\TTG Creative Studio\TTG Creative Studio.exe"
Push-Location $projectRoot
try {
    & python -m PyInstaller --noconfirm --clean $specFile
    if ($LASTEXITCODE -ne 0) { throw "Creative Studio PyInstaller build failed" }
} finally { Pop-Location }
if (!(Test-Path $distExe)) { throw "Creative Studio executable absent: $distExe" }
Write-Host "Built TTG Creative Studio: $distExe"
