# Explicit Authenticode signing gate. Never generate or store signing credentials.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installer = Join-Path $projectRoot "dist\installer\TTG-Creative-Studio-Core-Setup.exe"
$certificate = $env:TTG_STUDIO_SIGNING_PFX
$password = $env:TTG_STUDIO_SIGNING_PASSWORD
if (!(Test-Path $installer)) { throw "Unsigned Creative Studio installer is missing." }
if (!$certificate -or !(Test-Path $certificate) -or !$password) {
    throw "Signing blocked: supply an approved signing PFX path and secret through a protected release environment."
}
$signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (!$signtool) { throw "Windows SDK signtool.exe is unavailable." }
& $signtool sign /fd SHA256 /f $certificate /p $password /tr "http://timestamp.digicert.com" /td SHA256 $installer
if ($LASTEXITCODE -ne 0) { throw "Authenticode signing failed" }
& $signtool verify /pa /v $installer
if ($LASTEXITCODE -ne 0) { throw "Authenticode verification failed" }
Write-Host "Signed and verified TTG Creative Studio installer."
