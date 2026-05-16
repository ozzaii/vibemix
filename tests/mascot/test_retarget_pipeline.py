"""Sanity tests for the Mixamo → Neon Rebel retarget pipeline (VIS-04).

These pin the scaffold contract — CLI argv, size-band predicate, slot
mapping, rig path. They do NOT invoke `npx gltf-pipeline` (no npm at
test time). The real skeleton-remap implementation is filled in during
§VIS-04 Kaan-discharge per `KAAN-ACTION-LEGAL.md`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Add repo root so `scripts.mascot.retarget_to_neon_rebel` resolves regardless
# of how pytest is invoked.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def test_module_imports_cleanly():
    """Test 1: import the module's load-bearing public surface."""
    from scripts.mascot.retarget_to_neon_rebel import (  # noqa: F401
        NEON_REBEL_RIG_PATH,
        SLOT_MAPPINGS,
        main,
        retarget,
        compress_draco,
        verify_size_band,
    )


def test_neon_rebel_rig_path_resolves_to_existing_character_glb():
    """Test 2: NEON_REBEL_RIG_PATH points at the locked rig file on disk."""
    from scripts.mascot.retarget_to_neon_rebel import NEON_REBEL_RIG_PATH

    assert isinstance(NEON_REBEL_RIG_PATH, Path)
    assert NEON_REBEL_RIG_PATH.name == "character.glb"
    # File exists on disk (this is the Neon Rebel rig per 43-07).
    assert NEON_REBEL_RIG_PATH.exists(), (
        f"Neon Rebel rig missing at {NEON_REBEL_RIG_PATH}; "
        f"Plan 43-05 depends on the locked rig being present."
    )


def test_verify_size_band_accepts_in_band_size():
    """Test 3: 500 KB is in the 400KB-1.2MB band."""
    from scripts.mascot.retarget_to_neon_rebel import verify_size_band

    assert verify_size_band(500_000) is True


def test_verify_size_band_rejects_out_of_band_sizes():
    """Test 4: both below-400KB and above-1.2MB are rejected."""
    from scripts.mascot.retarget_to_neon_rebel import verify_size_band

    # Below 400KB floor.
    assert verify_size_band(200_000) is False
    # Above 1.2MB ceiling.
    assert verify_size_band(2_000_000) is False


def test_dry_run_lists_all_five_slot_mappings(capsys):
    """Test 5: `main(["--dry-run"])` exits 0 and prints all 5 planned retargets."""
    from scripts.mascot.retarget_to_neon_rebel import SLOT_MAPPINGS, main

    rc = main(["--dry-run"])
    assert rc == 0

    out = capsys.readouterr().out
    # All 5 Mixamo source labels surface.
    for mapping in SLOT_MAPPINGS:
        assert mapping.mixamo_label in out, (
            f"dry-run missed Mixamo label {mapping.mixamo_label!r}"
        )
        assert mapping.output_slot in out, (
            f"dry-run missed slot {mapping.output_slot!r}"
        )
    # Per-clip band surfaces (debug aid for Kaan).
    assert "400" in out and "1200" in out


def test_really_with_missing_source_exits_nonzero_with_clear_stderr(
    tmp_path, capsys
):
    """Test 6: `--really --source <missing>` exits non-zero; stderr mentions the missing file."""
    from scripts.mascot.retarget_to_neon_rebel import main

    missing = tmp_path / "does_not_exist.glb"
    rc = main(
        [
            "--really",
            "--source",
            str(missing),
            "--slot",
            "prep_settle",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert rc != 0

    err = capsys.readouterr().err
    # Stderr names the missing source file path explicitly.
    assert str(missing) in err or missing.name in err or "missing" in err.lower()


def test_slot_mappings_cover_the_five_context_slots():
    """Slot taxonomy invariant: 5 mappings, names match CONTEXT §VIS-04 exactly."""
    from scripts.mascot.retarget_to_neon_rebel import SLOT_MAPPINGS

    slots = {m.output_slot for m in SLOT_MAPPINGS}
    assert slots == {
        "prep_settle",
        "prep_head_turn_left",
        "prep_head_turn_right",
        "prep_lean_in_hyped",
        "prep_lean_in_neutral",
    }
    labels = {m.mixamo_label for m in SLOT_MAPPINGS}
    assert labels == {"Idle", "Talk_short", "Talk_long", "Celebrate", "Headbob"}


def test_script_runs_as_subprocess_dry_run():
    """Smoke: `python scripts/mascot/retarget_to_neon_rebel.py --dry-run` exits 0."""
    script_path = (
        _REPO_ROOT / "scripts" / "mascot" / "retarget_to_neon_rebel.py"
    )
    assert script_path.exists()
    result = subprocess.run(
        [sys.executable, str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"dry-run subprocess failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # All 5 slot names appear in stdout.
    for slot in (
        "prep_settle",
        "prep_head_turn_left",
        "prep_head_turn_right",
        "prep_lean_in_hyped",
        "prep_lean_in_neutral",
    ):
        assert slot in result.stdout, f"subprocess dry-run missed {slot}"
