param(
    [Parameter(Mandatory=$true)][string]$Installer
)
$ErrorActionPreference = "Stop"
if (!(Test-Path -LiteralPath $Installer)) { throw "Signed installer file absent" }
$expected = ($env:TTG_STUDIO_EXPECTED_SIGNER_THUMBPRINT -replace '\s','').ToUpperInvariant()
if ($expected -cnotmatch '^[0-9A-F]{40}$') {
    throw "A pinned 40-character approved signing thumbprint is required"
}
$signature = Get-AuthenticodeSignature -LiteralPath $Installer
if ($signature.Status -ne 'Valid') {
    throw "Windows does not trust the installer signature: $($signature.Status)"
}
if ($null -eq $signature.SignerCertificate) {
    throw "The signed installer does not have a signer identity"
}
if ($signature.SignerCertificate.Thumbprint.ToUpperInvariant() -cne $expected) {
    throw "Signer certificate does not match approved certificate thumbprint"
}
if ($signature.SignerCertificate.NotAfter -lt (Get-Date)) {
    throw "The signing certificate has expired"
}
if ($null -eq $signature.TimeStamperCertificate) {
    throw "A trusted timestamping certificate was not attached"
}
Write-Host "Authenticode valid; approved signer and timestamp verified."
