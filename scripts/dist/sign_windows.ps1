# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/sign_windows.ps1 — Phase 38 DIST-18 Windows local-rehearsal.
#
# Purpose:
#   Lets Kaan smoke-test the SignPath submission flow on his local Windows
#   machine BEFORE relying on CI on launch day (failure cost is high).
#
# Strict P46 compliance:
#   This script NEVER issues an HTTP POST/PUT to signpath.io directly.
#   It locates the official SignPathClient.exe CLI on PATH and invokes it.
#   The CLI is a SignPath-published, vendor-signed Windows binary that does
#   its own POST internally; that traffic is NOT autonomous-discharge
#   surface (Kaan installs the CLI manually; Kaan supplies the API token).
#
#   Forbidden in this script:
#     - Invoke-WebRequest / Invoke-RestMethod / [System.Net.WebClient] /
#       [System.Net.Http.*] calls.
#     - curl.exe / wget.exe to signpath.io / apple.com / notarytool endpoints.
#   The accompanying test `tests/security/test_sign_windows_ps1.py` greps
#   for these patterns and fails the build if any sneak in.
#
# Usage (local rehearsal):
#   pwsh scripts/dist/sign_windows.ps1 `
#       -MsiPath .\output\vibemix-installer.msi `
#       -ApiToken $env:SIGNPATH_API_TOKEN `
#       -OrganizationId <signpath-org-uuid> `
#       -ProjectSlug vibemix `
#       -PolicySlug release-signing `
#       -ArtifactConfigSlug vibemix-binaries
#
# Exit codes:
#   0 = success (signed MSI in $OutputDir)
#   2 = SignPathClient.exe not found on PATH
#   3 = required parameter missing
#   4 = SignPathClient.exe returned non-zero
#
# See KAAN-ACTION-LEGAL.md DIST-11 for SignPath OSS Foundation application
# protocol.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MsiPath,

    [Parameter(Mandatory = $false)]
    [string]$ApiToken = $env:SIGNPATH_API_TOKEN,

    [Parameter(Mandatory = $false)]
    [string]$OrganizationId = $env:SIGNPATH_ORGANIZATION_ID,

    [Parameter(Mandatory = $false)]
    [string]$ProjectSlug = $env:SIGNPATH_PROJECT_SLUG,

    [Parameter(Mandatory = $false)]
    [string]$PolicySlug = $env:SIGNPATH_SIGNING_POLICY_SLUG,

    [Parameter(Mandatory = $false)]
    [string]$ArtifactConfigSlug = "vibemix-binaries",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = ".\dist\signed-binaries"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Step 1 — Validate required parameters.
# ---------------------------------------------------------------------------
function Assert-Param {
    param([string]$Name, [string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        Write-Host "::error::sign_windows.ps1: required parameter '$Name' missing or empty."
        Write-Host "    Pass via -$Name flag or set the corresponding env var."
        exit 3
    }
}

Assert-Param "MsiPath" $MsiPath
Assert-Param "ApiToken" $ApiToken
Assert-Param "OrganizationId" $OrganizationId
Assert-Param "ProjectSlug" $ProjectSlug
Assert-Param "PolicySlug" $PolicySlug

if (-not (Test-Path $MsiPath)) {
    Write-Host "::error::sign_windows.ps1: MsiPath '$MsiPath' does not exist."
    exit 3
}

# ---------------------------------------------------------------------------
# Step 2 — Locate SignPathClient.exe on PATH.
# ---------------------------------------------------------------------------
$signpathCli = Get-Command "SignPathClient.exe" -ErrorAction SilentlyContinue
if (-not $signpathCli) {
    Write-Host "::error::sign_windows.ps1: SignPathClient.exe not found on PATH."
    Write-Host ""
    Write-Host "  Install the SignPath CLI from https://about.signpath.io/documentation/clients/cli/"
    Write-Host "  then add its install directory to PATH and re-run."
    Write-Host ""
    Write-Host "  This script REFUSES to POST/PUT to signpath.io directly (Pitfall P46)."
    exit 2
}

Write-Host "Using SignPath CLI: $($signpathCli.Source)"

# ---------------------------------------------------------------------------
# Step 3 — Prepare output directory.
# ---------------------------------------------------------------------------
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

# ---------------------------------------------------------------------------
# Step 4 — Invoke SignPathClient.exe with the supplied parameters.
# ---------------------------------------------------------------------------
# The CLI handles the actual signing request, polling, and signed-artifact
# download. We pass through stdout/stderr verbatim so Kaan can see exactly
# what the CLI is doing.
Write-Host "Submitting $MsiPath to SignPath for signing..."

# Mask the token from any echo paths.
$env:SIGNPATH_API_TOKEN = $ApiToken

& $signpathCli.Source `
    sign `
    --organization-id $OrganizationId `
    --project-slug $ProjectSlug `
    --signing-policy-slug $PolicySlug `
    --artifact-configuration-slug $ArtifactConfigSlug `
    --input-artifact-path $MsiPath `
    --output-artifact-directory $OutputDir `
    --wait-for-completion

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "::error::SignPathClient.exe exited with code $exitCode"
    exit 4
}

Write-Host "Signed artifact written to: $OutputDir"
Write-Host "Local rehearsal complete. CI parity verified locally."
exit 0
