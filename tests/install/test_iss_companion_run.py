"""Validate vibemix-installer.iss has Phase 49 companion entries.

Phase 49 Plan 04 — INSTALL-02 + INSTALL-04 + INSTALL-07.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ISS = ROOT / "installer" / "windows" / "vibemix-installer.iss"


def _read() -> str:
    return ISS.read_text()


def test_iss_exists():
    assert ISS.exists()


def test_files_section_copies_companion_dir():
    text = _read()
    # Each companion file gets an explicit Source: entry.
    for fname in ("fetch_drivers.ps1", "audio_config.py", "driver_manifest.json", "onboarding_copy.json", "uninstall.ps1"):
        assert fname in text, f"[Files] section missing entry for {fname}"
    assert "installer\\companion" in text or "installer/companion" in text


def test_run_section_invokes_fetch_drivers():
    text = _read()
    assert "fetch_drivers.ps1" in text
    # The [Run] entry must include the silent + waituntilterminated flags
    # so the wizard can pace its own progress UI.
    assert "waituntilterminated" in text
    assert "runhidden" in text
    assert "-Auto" in text


def test_uninstall_run_section_present():
    text = _read()
    assert "[UninstallRun]" in text
    assert "uninstall.ps1" in text
    # Preserve-default mode — uninstall.ps1 invoked WITHOUT -Clean flag.
    # We check that the [UninstallRun] line containing uninstall.ps1 does
    # NOT contain "-Clean".
    in_uninstall_run = False
    for line in text.splitlines():
        if "[UninstallRun]" in line:
            in_uninstall_run = True
            continue
        if line.startswith("[") and in_uninstall_run:
            break
        if in_uninstall_run and "uninstall.ps1" in line:
            assert "-Clean" not in line, "Preserve-default invariant: [UninstallRun] must NOT pass -Clean"


def test_vb_cable_license_dialog_present():
    text = _read()
    assert "CheckVbCableLicense" in text
    assert "VB-CABLE" in text or "VB-Audio" in text
    # The dialog must be wired into InitializeSetup.
    assert "InitializeSetup" in text


def test_existing_appid_preserved():
    """Regression guard — Phase 18 AppId must not have been touched."""
    text = _read()
    assert "A6B12C53-4F19-4D8B-9E2A-7C5F1E8D3B4F" in text
