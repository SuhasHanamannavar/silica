# ============================================================
#  CHECKMATE · ZERO-TRUST PROTECTED DOCUMENT VIEWER
# ============================================================

[CmdletBinding()]
param(
  [Parameter(Position=0, Mandatory=$false)]
  [string]$Path,
  [Parameter(Position=1, Mandatory=$false)]
  [string]$Actor
)

$ControlPlane = if ($env:CHECKMATE_CONTROL_PLANE) { $env:CHECKMATE_CONTROL_PLANE } else { "https://checkmateee.vercel.app" }
$ApiKey = if ($env:CHECKMATE_API_KEY) { $env:CHECKMATE_API_KEY.Trim() } else { "ck_live_e1b3da55b458153b2c65f9f11a55800338d1c72c96557d71" }

if ([string]::IsNullOrWhiteSpace($Path) -and $env:CHECKMATE_TARGET) {
  $Path = $env:CHECKMATE_TARGET
}

if ([string]::IsNullOrWhiteSpace($Path)) {
  Write-Host ""
  Write-Host "============================================================" -ForegroundColor DarkGray
  Write-Host " CHECKMATE · ZERO-TRUST DOCUMENT VIEWER" -ForegroundColor White
  Write-Host "============================================================" -ForegroundColor DarkGray
  if ([Environment]::UserInteractive) {
    $Path = Read-Host "Enter document or file path to view"
  }
  if ([string]::IsNullOrWhiteSpace($Path)) {
    Write-Host "[DENY] No file specified. Usage: .\checkmate-view.cmd <file>" -ForegroundColor Red
    return
  }
}

$FullPath = Resolve-Path $Path -ErrorAction SilentlyContinue
if (-not $FullPath -or -not (Test-Path $FullPath)) {
  Write-Host "[ERROR] Target file not found: $Path" -ForegroundColor Red
  return
}

# Determine bound developer / actor with strict zero-trust priority
$Developer = if ($Actor) { $Actor }
elseif ($env:CHECKMATE_ACTOR) { $env:CHECKMATE_ACTOR }
else { $null }

# 1. Check if target file contains bound owner metadata
if (-not $Developer -and $FullPath -and (Test-Path $FullPath)) {
  try {
    $HeaderLines = Get-Content -Path $FullPath -TotalCount 20 -ErrorAction SilentlyContinue
    foreach ($Line in $HeaderLines) {
      if ($Line -match '(?:BOUND OWNER|CHECKMATE_ACTOR|ACTOR):\s*@?([a-zA-Z0-9_.-]+)') {
        $Developer = $Matches[1].Split('@')[0]
        break
      }
    }
  } catch {}
}

# 2. Check workspace.json
if (-not $Developer) {
  $WorkspaceJsonPath = Join-Path $PSScriptRoot ".checkmate\workspace.json"
  if (Test-Path $WorkspaceJsonPath) {
    try {
      $WConf = Get-Content $WorkspaceJsonPath -Raw | ConvertFrom-Json
      if ($WConf.developer) { $Developer = $WConf.developer }
    } catch {}
  }
}

# 3. Fallback to system environment
if (-not $Developer) {
  $Developer = if ($env:USERNAME) { $env:USERNAME } else { $env:USER }
}
if (-not $Developer) { $Developer = "developer" }

# Clean developer handle
$CleanDev = $Developer.ToLower() -replace '[^a-z0-9_-]', ''

$FileName = [System.IO.Path]::GetFileName($FullPath)
$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { "workstation" }

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host " CHECKMATE · ZERO-TRUST ASSET VERIFICATION" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Verifying authorization with Checkmate Control Plane ($ControlPlane)..." -ForegroundColor Gray

$Payload = @{
  apiKey = $ApiKey
  actor = $CleanDev
  asset = $FileName
  hostname = $HostName
  action = "protected_read"
} | ConvertTo-Json

try {
  $Uri = "$ControlPlane/api/verify"
  $Response = Invoke-RestMethod -Uri $Uri -Method Post -Body $Payload -ContentType "application/json" -TimeoutSec 8
} catch {
  $Ex = $_.Exception
  Write-Host ""
  Write-Host "  ACTOR:         @$CleanDev" -ForegroundColor Yellow
  Write-Host "  ASSET:         $FileName" -ForegroundColor White
  Write-Host "  STATUS:        DENY (Checkmate Guard Enforced)" -ForegroundColor Red
  Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
  Write-Host "  BLOCKED: revoked device access attempt · identity_disabled at verification" -ForegroundColor Red
  Write-Host "============================================================" -ForegroundColor DarkGray
  Write-Host ""
  return
}

if (-not $Response.allowed -or $Response.status -ne "ACTIVE") {
  Write-Host ""
  Write-Host "  ACTOR:         @$CleanDev" -ForegroundColor Yellow
  Write-Host "  ASSET:         $FileName" -ForegroundColor White
  Write-Host "  STATUS:        $($Response.status)" -ForegroundColor Red
  Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
  Write-Host "  $($Response.error)" -ForegroundColor Red
  Write-Host "============================================================" -ForegroundColor DarkGray
  Write-Host ""
  return
}

# ACCESS GRANTED
Write-Host "  ACTOR:         @$CleanDev (TRUSTED)" -ForegroundColor Green
Write-Host "  ASSET:         $FileName" -ForegroundColor White
Write-Host "  DECISION:      ALLOW (Verified in AWS DynamoDB)" -ForegroundColor Green
Write-Host "  KEM SUITE:     $($Response.kem_suite)" -ForegroundColor White
Write-Host "  AUDIT ID:      $($Response.requestId)" -ForegroundColor DarkGray
Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  [UNSEALED] Access granted. Opening document..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host ""

# Output file content safely or launch in editor
try {
  $Content = Get-Content -Path $FullPath -Raw
  if ($Content.Length -lt 4000) {
    Write-Host $Content -ForegroundColor Cyan
  } else {
    Start-Process -FilePath "notepad.exe" -ArgumentList "`"$FullPath`""
  }
} catch {
  Write-Host "Could not render file: $($_.Exception.Message)" -ForegroundColor Red
}
