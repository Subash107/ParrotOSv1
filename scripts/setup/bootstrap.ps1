[CmdletBinding()]
param(
  [switch]$AddHosts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$reportsDir = Join-Path $projectRoot "reports"
$hostsPath = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
$hostAliases = @(
  "app.acme.local",
  "api.acme.local",
  "admin.acme.local",
  "storage.acme.local"
)
$hostLine = "127.0.0.1 {0}" -f ($hostAliases -join " ")

function Write-Step {
  param([string]$Message)
  Write-Host "[acme-bootstrap] $Message"
}

function Find-Command {
  param([string[]]$Names)
  foreach ($name in $Names) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) {
      return $cmd
    }
  }
  return $null
}

function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Step "Project root: $projectRoot"
if (-not (Test-Path -LiteralPath $reportsDir)) {
  New-Item -ItemType Directory -Path $reportsDir | Out-Null
  Write-Step "Created reports directory."
} else {
  Write-Step "Reports directory already exists."
}

$requiredTools = @(
  @{ Label = "docker"; Command = (Find-Command @("docker")); Required = $true },
  @{ Label = "python"; Command = (Find-Command @("python", "py")); Required = $true }
)

$optionalTools = @(
  @{ Label = "git"; Command = (Find-Command @("git")) },
  @{ Label = "bash"; Command = (Find-Command @("bash")) }
)

$missing = @()
foreach ($tool in $requiredTools) {
  if ($tool.Command) {
    Write-Step ("Found {0}: {1}" -f $tool.Label, $tool.Command.Source)
  } else {
    $missing += $tool.Label
    Write-Step ("Missing required tool: {0}" -f $tool.Label)
  }
}

foreach ($tool in $optionalTools) {
  if ($tool.Command) {
    Write-Step ("Found optional tool {0}: {1}" -f $tool.Label, $tool.Command.Source)
  } else {
    Write-Step ("Optional tool not found: {0}" -f $tool.Label)
  }
}

if ($missing.Count -gt 0) {
  throw "Install the missing required tools before continuing: $($missing -join ', ')"
}

Push-Location $projectRoot
try {
  docker compose config | Out-Null
  Write-Step "Docker Compose configuration is valid."
} finally {
  Pop-Location
}

$hostsContent = if (Test-Path -LiteralPath $hostsPath) {
  Get-Content -LiteralPath $hostsPath -Raw
} else {
  ""
}

$missingAliases = @()
foreach ($alias in $hostAliases) {
  if ($hostsContent -notmatch ("(?im)^\s*127\.0\.0\.1\s+.*\b{0}\b" -f [regex]::Escape($alias))) {
    $missingAliases += $alias
  }
}

if ($AddHosts -and $missingAliases.Count -gt 0) {
  if (-not (Test-Admin)) {
    throw "Re-run bootstrap.ps1 in an elevated PowerShell session to update the hosts file."
  }

  Add-Content -LiteralPath $hostsPath -Value "`r`n$hostLine"
  Write-Step "Added local host aliases to $hostsPath."
  $missingAliases = @()
}

if ($missingAliases.Count -gt 0) {
  Write-Step "Missing hosts aliases: $($missingAliases -join ', ')"
  Write-Step "Add this line to $hostsPath or rerun with -AddHosts:"
  Write-Host $hostLine
} else {
  Write-Step "Local hosts aliases are present."
}

Write-Step "Bootstrap check complete."
Write-Step "Next command: docker compose up --build"
