# SPDX-License-Identifier: Apache-2.0
#
# Stage the Windows Tauri app payload consumed by Inno Setup and SignPath.
# Run after:
#   1. uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec
#   2. cargo tauri build --no-bundle

param(
    [string]$OutputDir = "dist\windows-app",
    [string]$TauriReleaseDir = "tauri\src-tauri\target\release",
    [string]$SidecarTriple = "x86_64-pc-windows-msvc"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$appExe = Join-Path $TauriReleaseDir "vibemix.exe"
$sidecarDir = Join-Path "tauri\src-tauri\binaries" "vibemix-core-$SidecarTriple"
$sidecarExe = Join-Path $sidecarDir "vibemix-core-$SidecarTriple.exe"

if (-not (Test-Path $appExe)) {
    throw "Tauri app executable missing: $appExe"
}
if (-not (Test-Path $sidecarExe)) {
    throw "Windows sidecar executable missing: $sidecarExe"
}

if (Test-Path $OutputDir) {
    Remove-Item -Recurse -Force $OutputDir
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Copy-Item -Force $appExe (Join-Path $OutputDir "vibemix.exe")

# Tauri's Windows resource_dir() is the executable directory. Keep the same
# relative resource layout that sidecar.rs resolves at runtime.
$payloadBinaries = Join-Path $OutputDir "binaries"
New-Item -ItemType Directory -Force -Path $payloadBinaries | Out-Null
Copy-Item -Recurse -Force $sidecarDir (Join-Path $payloadBinaries "vibemix-core-$SidecarTriple")

# Preserve top-level runtime DLLs if the Windows Tauri build emits any.
Get-ChildItem -Path $TauriReleaseDir -File -Filter "*.dll" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Copy-Item -Force $_.FullName (Join-Path $OutputDir $_.Name)
    }

Write-Host "[stage_app_payload] staged: $OutputDir"
Write-Host "[stage_app_payload] app:     $(Join-Path $OutputDir 'vibemix.exe')"
Write-Host "[stage_app_payload] sidecar: $(Join-Path $payloadBinaries ('vibemix-core-' + $SidecarTriple))"
