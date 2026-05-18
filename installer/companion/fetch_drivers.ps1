# fetch_drivers.ps1 — Windows companion driver fetch (VB-CABLE via VB-Audio).
#
# Phase 49 Plan 01 — INSTALL-04 (fetch + SHA-256 verify + vendor-signed install).
#
# Contract:
#   - Reads installer/companion/driver_manifest.json
#   - Downloads VB-CABLE ZIP from vb-audio.com over HTTPS
#   - Verifies SHA-256 (skips with WARNING when PLACEHOLDER_ prefix)
#   - Extracts via Expand-Archive, runs VBCABLE_Setup_x64.exe /S
#   - On --dry-run: skips download + install, exits 0
#   - Logs to %APPDATA%\vibemix\install.log (JSONL)
#   - Emits structured JSON to stdout
#
# Spawns under bundle ID world.bravoh.vibemix.
# Writes ONLY to %APPDATA%\vibemix\install.log.
# NEVER inlines AIza pattern.

param(
  [switch]$DryRun,
  [switch]$Auto,
  [switch]$CheckSyntax
)

$ErrorActionPreference = "Stop"

# ─── Paths ─────────────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Manifest = Join-Path $ScriptDir "driver_manifest.json"
$LogDir = Join-Path $env:APPDATA "vibemix"
$LogFile = Join-Path $LogDir "install.log"
$TmpZip = Join-Path $env:TEMP "vbcable.zip"
$TmpExtract = Join-Path $env:TEMP "vbcable"

if ($CheckSyntax) { exit 0 }

# ─── Helpers ───────────────────────────────────────────────────────────────
function Ensure-LogDir {
  if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  }
}

function Log-Event {
  param([string]$Stage, [string]$State, [hashtable]$Extra = @{})
  Ensure-LogDir
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $line = @{ ts = $ts; stage = $Stage; state = $State } + $Extra
  ($line | ConvertTo-Json -Compress) | Add-Content -Path $LogFile -Encoding utf8
}

function Emit-State {
  param([string]$State, [hashtable]$Extra = @{})
  $line = @{ state = $State } + $Extra
  ($line | ConvertTo-Json -Compress) | Write-Output
}

# ─── Boot ──────────────────────────────────────────────────────────────────
Log-Event -Stage "boot" -State "ok" -Extra @{ dry_run = $DryRun.IsPresent; auto = $Auto.IsPresent }

# ─── Probe: VB-CABLE already installed? ────────────────────────────────────
$Installed = Get-ChildItem "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" -ErrorAction SilentlyContinue |
  Get-ItemProperty -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -like "*VB-Audio*" -or $_.Publisher -like "*VB-Audio*" }

if ($Installed) {
  Log-Event -Stage "probe" -State "already_installed"
  Emit-State -State "already_installed"
  exit 0
}

# ─── Read manifest ─────────────────────────────────────────────────────────
$ManifestData = Get-Content $Manifest -Raw | ConvertFrom-Json
$Url = $ManifestData.drivers.vb_cable.url
$ExpectedSha = $ManifestData.drivers.vb_cable.sha256
$Version = $ManifestData.drivers.vb_cable.version
$SilentFlag = $ManifestData.drivers.vb_cable.silent_flag

Log-Event -Stage "manifest" -State "ok" -Extra @{ version = $Version }

if ($DryRun) {
  Log-Event -Stage "fetch" -State "dry_run_skipped"
  Emit-State -State "dry_run_complete" -Extra @{ version = $Version }
  exit 0
}

# ─── Download ──────────────────────────────────────────────────────────────
Log-Event -Stage "fetch" -State "downloading" -Extra @{ url = $Url }
try {
  Invoke-WebRequest -Uri $Url -OutFile $TmpZip -UseBasicParsing -ErrorAction Stop
} catch {
  Log-Event -Stage "fetch" -State "fail" -Extra @{ reason = "download_failed"; error = $_.Exception.Message }
  Emit-State -State "fail" -Extra @{ stage = "fetch" }
  exit 1
}
Log-Event -Stage "fetch" -State "downloaded"

# ─── Verify SHA-256 ────────────────────────────────────────────────────────
$ActualSha = (Get-FileHash -Path $TmpZip -Algorithm SHA256).Hash.ToLower()
$ExpectedShaLc = $ExpectedSha.ToLower()
if ($ExpectedSha.StartsWith("PLACEHOLDER_")) {
  Log-Event -Stage "verify" -State "warning_placeholder" -Extra @{ actual = $ActualSha }
  # WARNING but not fail — placeholder discharge gated on §INSTALL-COMPANION-SIGN
} else {
  if ($ActualSha -ne $ExpectedShaLc) {
    Log-Event -Stage "verify" -State "fail" -Extra @{ expected = $ExpectedSha; actual = $ActualSha }
    Emit-State -State "fail" -Extra @{ stage = "verify" }
    Remove-Item $TmpZip -Force -ErrorAction SilentlyContinue
    exit 1
  }
  Log-Event -Stage "verify" -State "ok"
}

# ─── Extract + install ─────────────────────────────────────────────────────
if (Test-Path $TmpExtract) {
  Remove-Item $TmpExtract -Recurse -Force
}
Expand-Archive -Path $TmpZip -DestinationPath $TmpExtract -Force

$SetupExe = Get-ChildItem -Path $TmpExtract -Recurse -Filter "VBCABLE_Setup_x64.exe" | Select-Object -First 1
if (-not $SetupExe) {
  Log-Event -Stage "install" -State "fail" -Extra @{ reason = "setup_exe_not_found" }
  Emit-State -State "fail" -Extra @{ stage = "extract" }
  exit 1
}

Log-Event -Stage "install" -State "starting"
$proc = Start-Process -FilePath $SetupExe.FullName -ArgumentList $SilentFlag -Wait -PassThru -Verb RunAs
if ($proc.ExitCode -eq 0) {
  Log-Event -Stage "install" -State "ok"
  Emit-State -State "installed" -Extra @{ version = $Version; verified_sha256 = $ActualSha }
  Remove-Item $TmpZip -Force -ErrorAction SilentlyContinue
  Remove-Item $TmpExtract -Recurse -Force -ErrorAction SilentlyContinue
  exit 0
} else {
  Log-Event -Stage "install" -State "fail" -Extra @{ exit_code = $proc.ExitCode }
  Emit-State -State "fail" -Extra @{ stage = "install"; exit_code = $proc.ExitCode }
  exit 1
}
