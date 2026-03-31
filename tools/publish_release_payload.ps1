param(
  [Parameter(Mandatory = $true)][string]$SourceDir,
  [string]$ReleaseRoot = (Join-Path $PSScriptRoot '..\manifestguard\latest'),
  [string]$Repository = 'timejunky/r4it_mgpy_release',
  [string]$Branch = 'release',
  [string]$Notes = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$resolvedSource = (Resolve-Path -LiteralPath $SourceDir).Path
$resolvedReleaseRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\manifestguard\latest'))
if ($ReleaseRoot) {
  $resolvedReleaseRoot = [System.IO.Path]::GetFullPath($ReleaseRoot)
}

$wheel = Get-ChildItem -LiteralPath $resolvedSource -Filter 'manifestguard-*.whl' | Select-Object -First 1
if (-not $wheel) {
  throw "No manifestguard wheel found in $resolvedSource"
}

$version = $wheel.BaseName.Split('-')[1]
$releaseJson = Join-Path $resolvedSource 'release.json'
$shaFile = Join-Path $resolvedSource 'SHA256SUMS.txt'

New-Item -ItemType Directory -Force -Path $resolvedReleaseRoot | Out-Null
Copy-Item -LiteralPath $wheel.FullName -Destination (Join-Path $resolvedReleaseRoot $wheel.Name) -Force
if (Test-Path -LiteralPath $releaseJson) {
  Copy-Item -LiteralPath $releaseJson -Destination (Join-Path $resolvedReleaseRoot 'release.json') -Force
}
if (Test-Path -LiteralPath $shaFile) {
  Copy-Item -LiteralPath $shaFile -Destination (Join-Path $resolvedReleaseRoot 'SHA256SUMS.txt') -Force
}

$wheelHash = (Get-FileHash -LiteralPath $wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$wheelUrl = "https://raw.githubusercontent.com/$Repository/$Branch/manifestguard/latest/$($wheel.Name)"
$manifest = [ordered]@{
  version = $version
  wheel_url = $wheelUrl
  sha256 = $wheelHash
  python_requires = '>=3.10'
  notes = $Notes
}

$manifestPath = Join-Path $resolvedReleaseRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Out-File -LiteralPath $manifestPath -Encoding utf8

Write-Host "Prepared release payload in $resolvedReleaseRoot" -ForegroundColor Green
Write-Host "Wheel URL: $wheelUrl" -ForegroundColor DarkGray