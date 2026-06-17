$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $projectRoot "build_exe.ps1")
Write-Host ""
& (Join-Path $projectRoot "build_installer.ps1")
