"""Sanity tests for scripts/mascot/check_bundle_size.sh (VIS-04 Plan 43-05).

Pins the wrapper's contract:
  - script exists + executable
  - delegates to the Phase 31 gate (no duplicated 25 MB cap logic)
  - per-clip 400 KB - 1200 KB band constants match CONTEXT §VIS-04
  - script is invokable end-to-end; produces both Tier 1 + Tier 2 sections in stdout

Tier 2 may legitimately exit non-zero while the prep_*.glb placeholders
are still in place (~44-56 KB each, below the 400 KB floor). The CI
gate behaviour after §VIS-04 Kaan-discharge is: PASS once real Mixamo
retargets land all 5 slots in the 400 KB - 1200 KB band.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "mascot" / "check_bundle_size.sh"


def test_bundle_script_exists_and_executable():
    """Script file exists on disk + has the user-execute bit set."""
    assert _SCRIPT.exists(), f"missing: {_SCRIPT}"
    # POSIX execute bit (user level — `os.X_OK` checks all three).
    mode = _SCRIPT.stat().st_mode
    assert mode & 0o100, (
        f"{_SCRIPT} not executable; run `chmod +x` (mode={oct(mode)})"
    )


def test_bundle_script_delegates_to_phase31_gate():
    """Body references the existing Phase 31 25 MB cap script (no duplication)."""
    body = _SCRIPT.read_text(encoding="utf-8")
    assert "check_mascot_glb_size.sh" in body, (
        "wrapper must delegate to scripts/check_mascot_glb_size.sh "
        "instead of re-implementing the 25 MB cap"
    )


def test_per_clip_band_constants_match_context():
    """CONTEXT §VIS-04 band: 400 KB minimum, 1200 KB (1.2 MB) maximum."""
    body = _SCRIPT.read_text(encoding="utf-8")
    # Min floor — 400 * 1024.
    assert "400 * 1024" in body, "min band 400 * 1024 missing from wrapper"
    # Max ceiling — 1200 * 1024.
    assert "1200 * 1024" in body, "max band 1200 * 1024 missing from wrapper"


def test_bundle_script_invokable_and_prints_both_tiers():
    """End-to-end smoke: script runs; stdout names both Tier 1 and Tier 2.

    We do NOT assert exit 0: the prep_*.glb placeholders are intentionally
    sub-400 KB until §VIS-04 Kaan-discharge replaces them. Tier 2 must
    legitimately fail with exit 2 today. Exit 1 (Tier 1 fail) would be a
    regression — but exit 2 is the expected placeholder state.
    """
    result = subprocess.run(
        ["bash", str(_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=_REPO_ROOT,
    )
    # Tier 1 must pass (delegated 25 MB cap is well within budget today).
    # Tier 2 fails on placeholders (exit 2) or passes after discharge (exit 0).
    assert result.returncode in (0, 2), (
        f"unexpected exit code {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "Tier 1" in result.stdout, "stdout missing Tier 1 header"
    assert "Tier 2" in result.stdout, "stdout missing Tier 2 header"


def test_mixamo_clip_sources_manifest_present_and_documents_five_slots():
    """MIXAMO-CLIP-SOURCES.md exists + names all 5 vibemix slots + Neon Rebel."""
    manifest = _REPO_ROOT / "scripts" / "mascot" / "MIXAMO-CLIP-SOURCES.md"
    assert manifest.exists(), f"missing: {manifest}"
    body = manifest.read_text(encoding="utf-8")
    # 5 vibemix slot filenames must each appear in the manifest.
    for slot in (
        "prep_settle.glb",
        "prep_head_turn_left.glb",
        "prep_head_turn_right.glb",
        "prep_lean_in_hyped.glb",
        "prep_lean_in_neutral.glb",
    ):
        assert slot in body, f"manifest missing slot {slot!r}"
    # The rig name Kaan picks against ("Neon Rebel") must be named.
    assert "Neon Rebel" in body, "manifest must name the Neon Rebel rig"
    # The Pioneer-CDJ headbob aesthetic constraint must be surfaced.
    assert "Pioneer" in body and "CDJ" in body and "headbob" in body, (
        "manifest must surface the Pioneer-CDJ-headbob aesthetic constraint "
        "for the celebrate clip selection"
    )


def test_mixamo_manifest_documents_5_source_clips():
    """5 Mixamo source clip labels (Idle / Talk_short / Talk_long / Celebrate / Headbob)."""
    manifest = _REPO_ROOT / "scripts" / "mascot" / "MIXAMO-CLIP-SOURCES.md"
    body = manifest.read_text(encoding="utf-8")
    for label in ("Idle", "Talk_short", "Talk_long", "Celebrate", "Headbob"):
        assert label in body, f"manifest missing Mixamo source label {label!r}"
