# Phase 33 / Plan 33-08 — Fresh-Windows-VM rehearsal scaffold.
#
# Provisioning skeleton for Windows 10 / 11 install-rehearsal VMs. Real
# execution is Kaan-action — disk space + a Windows license + a fresh
# ISO are required. CI calls the orchestrator in --dry-run mode only.
#
# HARD GUARDS:
#   1. The $env:INSTALL_REHEARSAL_REAL env var must equal "1".
#   2. The ISO URLs below are placeholders. Kaan fills them in on the
#      machine that runs the real provisioning (autonomous agents do
#      NOT autonomously download Windows ISOs).
#
# Usage:
#   pwsh ./win_vm_setup.ps1                          # dry-run, exit 0
#   $env:INSTALL_REHEARSAL_REAL=1; pwsh ./win_vm_setup.ps1  # real run

$ErrorActionPreference = "Stop"

$matrix = @(
    @{ Name = "windows-10"; Iso = "<KAAN: paste Win10 ISO URL>" }
    @{ Name = "windows-11"; Iso = "<KAAN: paste Win11 ISO URL>" }
)

Write-Host "[33-08] Fresh-Windows-VM rehearsal scaffold"
foreach ($vm in $matrix) {
    Write-Host "[33-08]   - $($vm.Name)"
}

if ($env:INSTALL_REHEARSAL_REAL -ne "1") {
    Write-Host "[33-08] INSTALL_REHEARSAL_REAL != 1 - dry-run mode."
    Write-Host "[33-08] Would provision:"
    foreach ($vm in $matrix) {
        Write-Host "  - VBoxManage createvm --name `"$($vm.Name)-vibemix-rehearsal`" --register"
        Write-Host "  - VBoxManage modifyvm `"$($vm.Name)-vibemix-rehearsal`" --memory 4096 --cpus 2"
        Write-Host "  - (would attach ISO: $($vm.Iso))"
    }
    Write-Host "[33-08] Set `$env:INSTALL_REHEARSAL_REAL=1 to actually provision."
    exit 0
}

# Real-run path — Kaan flipped the env var on a Windows host.
foreach ($vm in $matrix) {
    $name = "$($vm.Name)-vibemix-rehearsal"
    Write-Host "[33-08] Provisioning $name"
    if ($vm.Iso -like "<KAAN*") {
        Write-Host "[33-08] ISO URL is a placeholder — fill in win_vm_setup.ps1 first."
        exit 1
    }
    # See KAAN-ACTION-LEGAL.md INSTALL-VM-RUN for the full provisioning
    # contract. This script intentionally does NOT shell out further in
    # autonomous mode.
}
Write-Host "[33-08] Matrix provisioned (placeholder)."
