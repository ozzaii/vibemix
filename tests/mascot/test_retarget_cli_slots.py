"""MASCOT-02 smoke test — assert scripts/mascot/retarget_to_neon_rebel.py
knows about all 28 slots across 5 families. Pure static-import test;
does NOT invoke gltf-pipeline or Mixamo."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts" / "mascot"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import retarget_to_neon_rebel as mod  # noqa: E402


def test_slot_families_has_5_families():
    assert set(mod.SLOT_FAMILIES.keys()) == {
        "legacy_prep", "base", "emotion", "anticipation", "reaction"
    }


def test_28_total_slots():
    all_slots = [s for fam in mod.SLOT_FAMILIES.values() for s in fam["slots"]]
    assert len(all_slots) == 28


def test_per_family_slot_counts():
    counts = {f: len(info["slots"]) for f, info in mod.SLOT_FAMILIES.items()}
    assert counts == {
        "legacy_prep": 5,
        "base": 3,
        "emotion": 5,
        "anticipation": 5,
        "reaction": 10,
    }


def test_legacy_prep_slots_preserved_verbatim():
    assert set(mod.SLOT_FAMILIES["legacy_prep"]["slots"]) == {
        "prep_settle",
        "prep_head_turn_left",
        "prep_head_turn_right",
        "prep_lean_in_hyped",
        "prep_lean_in_neutral",
    }


def test_new_anticipation_family_distinct_from_legacy():
    """Phase 47 anticipation family adds NEW prep_* slots, NOT aliasing legacy_prep."""
    assert set(mod.SLOT_FAMILIES["anticipation"]["slots"]) == {
        "prep_kick", "prep_breakdown", "prep_drop", "prep_layer", "prep_mix"
    }
    legacy = set(mod.SLOT_FAMILIES["legacy_prep"]["slots"])
    new = set(mod.SLOT_FAMILIES["anticipation"]["slots"])
    assert legacy.isdisjoint(new)


def test_reaction_family_includes_hype_peak():
    """react_hype_peak is the README hero render anchor — MUST exist."""
    assert "react_hype_peak" in mod.SLOT_FAMILIES["reaction"]["slots"]


def test_per_family_size_bands():
    assert mod.SLOT_FAMILIES["base"]["size_band_kb"] == (200, 600)
    assert mod.SLOT_FAMILIES["emotion"]["size_band_kb"] == (300, 900)
    assert mod.SLOT_FAMILIES["anticipation"]["size_band_kb"] == (400, 1200)
    assert mod.SLOT_FAMILIES["reaction"]["size_band_kb"] == (400, 1200)
    assert mod.SLOT_FAMILIES["legacy_prep"]["size_band_kb"] == (400, 1200)


def test_valid_slots_total():
    assert len(mod.VALID_SLOTS) == 28


def test_verify_size_band_for_slot_per_family():
    # base 200-600 KB
    assert mod.verify_size_band_for_slot("base_idle", 300 * 1024) is True
    assert mod.verify_size_band_for_slot("base_idle", 700 * 1024) is False
    # emotion 300-900 KB
    assert mod.verify_size_band_for_slot("emotion_joy", 500 * 1024) is True
    assert mod.verify_size_band_for_slot("emotion_joy", 200 * 1024) is False
    # reaction 400-1200 KB
    assert mod.verify_size_band_for_slot("react_hype_peak", 800 * 1024) is True
    assert mod.verify_size_band_for_slot("react_hype_peak", 100 * 1024) is False
