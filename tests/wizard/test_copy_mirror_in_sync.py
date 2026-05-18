"""Test that tauri/ui/src/wizard/copy.json mirrors installer/companion/onboarding_copy.json.

Phase 49 Plan 03 — invariant: copy.json mirror MUST stay in sync with the
canonical onboarding_copy.json source-of-truth. If they diverge, the wizard
UI shows stale strings (or imports a non-existent field).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "installer" / "companion" / "onboarding_copy.json"
MIRROR = ROOT / "tauri" / "ui" / "src" / "wizard" / "copy.json"


def test_mirror_exists():
    assert MIRROR.exists(), f"copy.json mirror missing at {MIRROR}. Run scripts/build/sync_wizard_copy.sh"


def test_mirror_matches_canonical():
    canonical = json.loads(CANONICAL.read_text())
    mirror = json.loads(MIRROR.read_text())
    assert canonical == mirror, "copy.json mirror is stale. Run scripts/build/sync_wizard_copy.sh"


def test_required_fields_present_in_canonical():
    d = json.loads(CANONICAL.read_text())
    for step in ("welcome", "forewarning", "driver_fetch", "format_check"):
        assert step in d["steps"], f"missing step {step!r}"
    assert "uninstall" in d
    assert d["steps"]["welcome"]["primary_cta"], "welcome.primary_cta empty"
    assert d["steps"]["forewarning"]["mac_title"], "forewarning.mac_title empty"
    assert d["steps"]["forewarning"]["win_title"], "forewarning.win_title empty"
    assert d["steps"]["format_check"]["success"], "format_check.success empty"
    assert d["uninstall"]["title"], "uninstall.title empty"
