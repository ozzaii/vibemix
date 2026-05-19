# SPDX-License-Identifier: Apache-2.0
#
# scripts/win/build_local.ps1 — Single-command Windows installer build.
#
# Mirrors .github/workflows/release.yml::build-windows so Kaan can produce
# the same artifact locally inside a Parallels VM (or any Windows host)
# when GH Actions is unavailable (billing lock, runner outage, etc).
#
# Output: installer\windows\output\vibemix-installer.exe  (unsigned)
#
# Usage (from repo root, inside the Win VM):
#   pwsh scripts\win\build_local.ps1
#
# Prereqs the script auto-checks (and fails fast with install hint if missing):
#   - Python 3.12 (matches PYTHON_VERSION in release.yml)
#   - Node 20+
#   - Rust toolchain (cargo + rustc)
#   - Inno Setup 6 (ISCC.exe)
#
# This script does NOT install prereqs. The first-time setup line is:
#   winget install Python.Python.3.12 OpenJS.NodeJS.LTS Rustlang.Rustup JRSoftware.InnoSetup

$ErrorActionPreference = "Stop"

function Test-Tool($name, $cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[build_local] MISSING: $name" -ForegroundColor Red
        Write-Host "[build_local] Install hint: $hint"
        exit 2
    }
    Write-Host "[build_local] ok: $name"
}

Write-Host "[build_local] === prereq check ==="
Test-Tool "Python 3.12" "python" "winget install Python.Python.3.12"
Test-Tool "Node"       "npm"    "winget install OpenJS.NodeJS.LTS"
Test-Tool "Rust"       "cargo"  "winget install Rustlang.Rustup ; rustup default stable"
Test-Tool "uv"         "uv"     "winget install astral-sh.uv"

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    Write-Host "[build_local] MISSING: Inno Setup 6 (ISCC.exe not at $iscc)" -ForegroundColor Red
    Write-Host "[build_local] Install hint: winget install JRSoftware.InnoSetup --version 6.4.0"
    exit 2
}
Write-Host "[build_local] ok: Inno Setup 6"

# Move to repo root regardless of where the script is invoked from.
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot
Write-Host "[build_local] repo root: $repoRoot"

Write-Host "[build_local] === Stage 1: VC++ Redist (PyInstaller dep) ==="
New-Item -ItemType Directory -Force -Path installer\windows\redist | Out-Null
$vcredist = "installer\windows\redist\vc_redist.x64.exe"
if (-not (Test-Path $vcredist)) {
    Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile $vcredist
}
Write-Host "[build_local] vc_redist.x64.exe ready"

Write-Host "[build_local] === Stage 2: PyInstaller sidecar ==="
uv sync --frozen
uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec
if (-not (Test-Path "dist\vibemix\vibemix.exe")) {
    Write-Host "[build_local] FAIL: PyInstaller did not produce dist\vibemix\vibemix.exe" -ForegroundColor Red
    exit 3
}

Write-Host "[build_local] === Stage 3: Tauri frontend + cargo bundle ==="
Push-Location tauri
npm ci
npm run build
Pop-Location

Push-Location tauri\src-tauri
cargo tauri build
Pop-Location

Write-Host "[build_local] === Stage 4: Inno Setup compile (unsigned) ==="
& $iscc /Sno="echo skipping local sign for `$f" installer\windows\vibemix-installer.iss

$installer = "installer\windows\output\vibemix-installer.exe"
if (-not (Test-Path $installer)) {
    Write-Host "[build_local] FAIL: ISCC did not produce $installer" -ForegroundColor Red
    exit 4
}

Write-Host ""
Write-Host "[build_local] === DONE ===" -ForegroundColor Green
Write-Host "[build_local] artifact: $installer"
Write-Host "[build_local]   size:  $((Get-Item $installer).Length / 1MB | ForEach-Object { '{0:N1} MB' -f $_ })"
Write-Host ""
Write-Host "[build_local] Next: drag $installer onto a clean Win 11 snapshot"
Write-Host "[build_local]       (Parallels: revert to clean-postinstall snapshot first)"
Write-Host "[build_local]       Stopwatch the full first-launch flow; target ≤60s per INSTALL-05."
Write-Host "[build_local]       Record result in KAAN-ACTION-LEGAL.md::INSTALL-VM-RUN sign-off block."
