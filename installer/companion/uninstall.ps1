# uninstall.ps1 — Phase 49 INSTALL-07 (Windows).
#
# Preserve-default uninstall (mirror of uninstall.sh):
#   - Removes %LOCALAPPDATA%\vibemix\cache\
#   - Removes VB-CABLE default-device routing override (via audio_config.py)
# Preserves (unless -Clean):
#   - %APPDATA%\vibemix\recordings\
#   - %APPDATA%\vibemix\debriefs\
#   - %APPDATA%\vibemix\ghost_calibration.json
#
# Logs to %APPDATA%\vibemix\uninstall.log (JSONL).

param(
  [switch]$Clean,
  [switch]$DryRun,
  [switch]$CheckSyntax
)

if ($CheckSyntax) { exit 0 }

$ErrorActionPreference = "Stop"

$DataRoot = $env:VIBEMIX_DATA_ROOT
if (-not $DataRoot) { $DataRoot = Join-Path $env:APPDATA "vibemix" }
$CacheRoot = $env:VIBEMIX_CACHE_ROOT
if (-not $CacheRoot) { $CacheRoot = Join-Path $env:LOCALAPPDATA "vibemix\cache" }
$LogFile = Join-Path $DataRoot "uninstall.log"

if (-not (Test-Path $DataRoot)) {
  New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
}

function Log-Event {
  param([string]$Action, [string]$Target)
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $line = @{ ts = $ts; action = $Action; target = $Target; clean = $Clean.IsPresent } | ConvertTo-Json -Compress
  $line | Add-Content -Path $LogFile -Encoding utf8
}

function Safe-Remove {
  param([string]$Target)
  if (Test-Path $Target) {
    if ($DryRun) {
      Log-Event -Action "dry_run_would_remove" -Target $Target
    } else {
      Remove-Item -Path $Target -Recurse -Force
      Log-Event -Action "removed" -Target $Target
    }
  } else {
    Log-Event -Action "absent" -Target $Target
  }
}

Log-Event -Action "uninstall_started" -Target ""

# Always remove: caches + audio routing
Safe-Remove -Target $CacheRoot

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AudioConfig = Join-Path $ScriptDir "audio_config.py"
if ((Test-Path $AudioConfig) -and (-not $DryRun)) {
  try {
    & python3 $AudioConfig --remove-routing 2>$null | Out-Null
    Log-Event -Action "removed" -Target "audio_routing"
  } catch {
    # best-effort
  }
}

$Preserved = @("recordings", "debriefs", "ghost_calibration.json")
if ($Clean) {
  foreach ($p in $Preserved) {
    Safe-Remove -Target (Join-Path $DataRoot $p)
  }
  Log-Event -Action "clean_uninstall_complete" -Target $DataRoot
} else {
  foreach ($p in $Preserved) {
    Log-Event -Action "preserved" -Target (Join-Path $DataRoot $p)
  }
  Log-Event -Action "default_uninstall_complete" -Target $DataRoot
}

exit 0
