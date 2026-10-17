# Local Creative Studio image understanding — operator-controlled and standalone.
# Requires an installed llama.cpp vision-capable server and GGUF plus projector.
# Does not install software, download models, invoke Hunter or start services in the background.
param(
    [Parameter(Mandatory=$true)][string]$ServerExecutable,
    [Parameter(Mandatory=$true)][string]$Checkpoint,
    [Parameter(Mandatory=$true)][string]$VisionProjector,
    [string]$ModelId = "creative-vision-local",
    [ValidateRange(0,100)][int]$GpuLayers = 24
)
$ErrorActionPreference = "Stop"
foreach ($item in @($ServerExecutable, $Checkpoint, $VisionProjector)) {
    if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
        throw "Creative Studio vision startup blocked: missing file $item"
    }
}
$application = (Resolve-Path -LiteralPath $ServerExecutable).Path
$model = (Resolve-Path -LiteralPath $Checkpoint).Path
$projector = (Resolve-Path -LiteralPath $VisionProjector).Path
if ($model -eq $projector) { throw "The checkpoint and projector must be different files." }
if (-not $ModelId -or $ModelId.Length -gt 120 -or $ModelId -notmatch '^[a-zA-Z0-9._-]+$') {
    throw "Model ID must be a nonempty, simple local identifier."
}
$existing = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existing) { throw "Port 8000 is already in use. Refusing to start another vision server." }
Write-Host "Starting owner-controlled local Creative Studio VLM. Press Ctrl+C to stop."
Write-Host "Checkpoint SHA-256: $((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash)"
Write-Host "Vision projector SHA-256: $((Get-FileHash -LiteralPath $projector -Algorithm SHA256).Hash)"
Write-Host "Serving only on 127.0.0.1:8000. No remote access or background schedule."
& $application --host 127.0.0.1 --port 8000 --model $model --mmproj $projector --n-gpu-layers $GpuLayers --ctx-size 4096 --alias $ModelId
if ($LASTEXITCODE -ne 0) { throw "Local vision-server process failed: $LASTEXITCODE" }
