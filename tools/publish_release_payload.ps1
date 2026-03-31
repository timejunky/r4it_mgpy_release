param(
  [Parameter(Mandatory = $true)][string]$SourceDir,
  [string]$ReleaseRoot = (Join-Path $PSScriptRoot '..\manifestguard'),
  [string]$Repository = 'timejunky/r4it_mgpy_release',
  [string]$Branch = 'release',
  [string]$Notes = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-ManifestFile {
  param(
    [Parameter(Mandatory = $true)][string]$TargetRoot,
    [Parameter(Mandatory = $true)][string]$WheelName,
    [Parameter(Mandatory = $true)][string]$WheelHash,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Branch,
    [Parameter(Mandatory = $true)][string]$RelativeRoot,
    [string]$Notes = ''
  )

  $wheelUrl = "https://raw.githubusercontent.com/$Repository/$Branch/$RelativeRoot/$WheelName"
  $manifest = [ordered]@{
    version = $Version
    wheel_url = $wheelUrl
    sha256 = $WheelHash
    python_requires = '>=3.10'
    notes = $Notes
  }

  $manifestPath = Join-Path $TargetRoot 'manifest.json'
  $manifest | ConvertTo-Json -Depth 4 | Out-File -LiteralPath $manifestPath -Encoding utf8
  Write-Host "Manifest URL root: $RelativeRoot" -ForegroundColor DarkGray
  Write-Host "Wheel URL: $wheelUrl" -ForegroundColor DarkGray
}

function Copy-ItemIfDifferent {
  param(
    [Parameter(Mandatory = $true)][string]$SourcePath,
    [Parameter(Mandatory = $true)][string]$DestinationPath
  )

  $resolvedSource = [System.IO.Path]::GetFullPath($SourcePath)
  $resolvedDestination = [System.IO.Path]::GetFullPath($DestinationPath)
  if ($resolvedSource -eq $resolvedDestination) {
    return
  }

  Copy-Item -LiteralPath $resolvedSource -Destination $resolvedDestination -Force
}

$resolvedSource = (Resolve-Path -LiteralPath $SourceDir).Path
$resolvedReleaseRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\manifestguard'))
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
$latestRoot = Join-Path $resolvedReleaseRoot 'latest'
$versionRoot = Join-Path $resolvedReleaseRoot $version

foreach ($targetRoot in @($latestRoot, $versionRoot)) {
  New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
  Copy-ItemIfDifferent -SourcePath $wheel.FullName -DestinationPath (Join-Path $targetRoot $wheel.Name)
  if (Test-Path -LiteralPath $releaseJson) {
    Copy-ItemIfDifferent -SourcePath $releaseJson -DestinationPath (Join-Path $targetRoot 'release.json')
  }
  if (Test-Path -LiteralPath $shaFile) {
    Copy-ItemIfDifferent -SourcePath $shaFile -DestinationPath (Join-Path $targetRoot 'SHA256SUMS.txt')
  }
}

$wheelHash = (Get-FileHash -LiteralPath $wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not (Test-Path -LiteralPath $shaFile)) {
  $shaLine = "$wheelHash  $($wheel.Name)"
  foreach ($targetRoot in @($latestRoot, $versionRoot)) {
    Set-Content -LiteralPath (Join-Path $targetRoot 'SHA256SUMS.txt') -Value $shaLine -Encoding utf8
  }
}

Write-ManifestFile -TargetRoot $latestRoot -WheelName $wheel.Name -WheelHash $wheelHash -Version $version -Repository $Repository -Branch $Branch -RelativeRoot "manifestguard/latest" -Notes $Notes
Write-ManifestFile -TargetRoot $versionRoot -WheelName $wheel.Name -WheelHash $wheelHash -Version $version -Repository $Repository -Branch $Branch -RelativeRoot "manifestguard/$version" -Notes $Notes

Write-Host "Prepared release payload in $resolvedReleaseRoot" -ForegroundColor Green
Write-Host "Published folders: latest, $version" -ForegroundColor DarkGray