# Test actual Windows installer installation/uninstallation on disposable CI host.
# This script does not perform signing, publish a release or install on ATHENA.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $projectRoot "dist\installer\TTG-Creative-Studio-Core-Setup.exe"
if (!(Test-Path -LiteralPath $installer)) { throw "No compiled Creative Studio installer" }
$target = Join-Path $env:RUNNER_TEMP "TTG-Creative-Studio-Installed"
if (Test-Path -LiteralPath $target) { throw "Refusing to overwrite existing installation test directory" }
$installArgs = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR="' + $target + '"'
$install = Start-Process -FilePath $installer -ArgumentList $installArgs -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Inno Setup install failed: $($install.ExitCode)" }
$app = Join-Path $target "TTG Creative Studio.exe"
$uninstaller = Join-Path $target "unins000.exe"
if (!(Test-Path -LiteralPath $app)) { throw "Actual installed executable missing" }
if (!(Test-Path -LiteralPath $uninstaller)) { throw "Uninstaller missing" }
$run = Start-Process -FilePath $app -ArgumentList "--self-check" -Wait -PassThru
if ($run.ExitCode -ne 0) { throw "Installed Creative Studio smoke failed: $($run.ExitCode)" }
# The installed GUI must actually open, edit a native layer, save, export
# a nonblank image and capture its window. Evidence is kept outside the
# installed app directory so uninstallation cannot erase the proof.
$proof = Join-Path $env:RUNNER_TEMP "studio-installed-gui-proof-windows"
if (Test-Path -LiteralPath $proof) { throw "Existing GUI proof path; will not overwrite" }
New-Item -ItemType Directory -Path $proof -ErrorAction Stop | Out-Null
$guiArg = '--qualify-gui "' + $proof + '"'
$ui = Start-Process -FilePath $app -ArgumentList $guiArg -Wait -PassThru
if ($ui.ExitCode -ne 0) { throw "Installed Creative Studio GUI qualification failed: $($ui.ExitCode)" }
& python -B (Join-Path $projectRoot "scripts\verify_frozen_gui_proof.py") $proof
if ($LASTEXITCODE -ne 0) { throw "Installed GUI proof has invalid artifacts or hashes" }

$uninstall = Start-Process -FilePath $uninstaller -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw "Installer rollback/uninstall failed: $($uninstall.ExitCode)" }
if (Test-Path -LiteralPath $app) { throw "Installer left application executable after uninstall" }
Write-Host "Physical Windows runner: install, executable smoke and uninstall PASS."
