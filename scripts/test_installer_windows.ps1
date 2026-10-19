# Test actual Windows installer installation/uninstallation on disposable CI host.
# This script does not perform signing, publish a release or install on ATHENA.
$ErrorActionPreference = "Stop"

function Invoke-BoundedInstallerStep {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string]$Arguments,
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][int]$TimeoutSeconds
    )
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -PassThru
    try {
        if (!$process.WaitForExit($TimeoutSeconds * 1000)) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw "$Label exceeded bounded $TimeoutSeconds-second CI deadline"
        }
        if ($process.ExitCode -ne 0) {
            throw "$Label failed with exit code $($process.ExitCode)"
        }
    } finally {
        $process.Dispose()
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $projectRoot "dist\installer\TTG-Creative-Studio-Core-Setup.exe"
if (!(Test-Path -LiteralPath $installer)) { throw "No compiled Creative Studio installer" }
$target = Join-Path $env:RUNNER_TEMP "TTG-Creative-Studio-Installed"
if (Test-Path -LiteralPath $target) { throw "Refusing to overwrite existing installation test directory" }
$installArgs = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR="' + $target + '"'
Invoke-BoundedInstallerStep -FilePath $installer -Arguments $installArgs -Label "Installer" -TimeoutSeconds 180
$app = Join-Path $target "TTG Creative Studio.exe"
$uninstaller = Join-Path $target "unins000.exe"
if (!(Test-Path -LiteralPath $app)) { throw "Actual installed executable missing" }
if (!(Test-Path -LiteralPath $uninstaller)) { throw "Uninstaller missing" }
Invoke-BoundedInstallerStep -FilePath $app -Arguments "--self-check" -Label "Installed app smoke" -TimeoutSeconds 90
# The installed GUI must actually open, edit a native layer, save, export
# a nonblank image and capture its window. Evidence is kept outside the
# installed app directory so uninstallation cannot erase the proof.
$proof = Join-Path $env:RUNNER_TEMP "studio-installed-gui-proof-windows"
if (Test-Path -LiteralPath $proof) { throw "Existing GUI proof path; will not overwrite" }
New-Item -ItemType Directory -Path $proof -ErrorAction Stop | Out-Null
$guiArg = '--qualify-gui "' + $proof + '"'
Invoke-BoundedInstallerStep -FilePath $app -Arguments $guiArg -Label "Installed GUI qualification" -TimeoutSeconds 120
& python -B (Join-Path $projectRoot "scripts\verify_frozen_gui_proof.py") $proof
if ($LASTEXITCODE -ne 0) { throw "Installed GUI proof has invalid artifacts or hashes" }

Invoke-BoundedInstallerStep -FilePath $uninstaller -Arguments "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" -Label "Uninstaller rollback" -TimeoutSeconds 180
if (Test-Path -LiteralPath $app) { throw "Installer left application executable after uninstall" }
Write-Host "Physical Windows runner: install, executable smoke and uninstall PASS."
