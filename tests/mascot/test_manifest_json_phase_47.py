"""MASCOT-01 smoke test — assert tauri/ui/assets/mascot/manifest.json
contains all 23 Phase 47 family entries with correct shape."""
import json
from pathlib import Path

MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "tauri"
    / "ui"
    / "assets"
    / "mascot"
    / "manifest.json"
)

PHASE_47_CLIPS = {
    "base_idle",
    "base_breathe",
    "base_sway",
    "emotion_joy",
    "emotion_trust",
    "emotion_surprise",
    "emotion_anticipation",
    "emotion_focus",
    "prep_kick",
    "prep_breakdown",
    "prep_drop",
    "prep_layer",
    "prep_mix",
    "react_kick_swap",
    "react_sub_layer",
    "react_breakdown",
    "react_reentry",
    "react_phrase_boundary",
    "react_distortion_climb",
    "react_acid_line",
    "react_mix_in",
    "react_mix_out",
    "react_hype_peak",
}


def test_manifest_is_valid_json():
    json.loads(MANIFEST.read_text())


def test_phase_47_has_23_clips():
    data = json.loads(MANIFEST.read_text())
    clip_names = {a["clip"] for a in data["animations"]}
    assert PHASE_47_CLIPS.issubset(clip_names), (
        f"missing Phase 47 clips: {PHASE_47_CLIPS - clip_names}"
    )


def test_every_phase_47_entry_has_required_fields():
    data = json.loads(MANIFEST.read_text())
    phase_47_entries = [
        a for a in data["animations"] if a["clip"] in PHASE_47_CLIPS
    ]
    assert len(phase_47_entries) == 23
    for entry in phase_47_entries:
        assert "file" in entry, f"{entry['clip']} missing file"
        assert "clip" in entry, "missing clip key"
        assert "states" in entry, f"{entry['clip']} missing states"
        assert entry["file"].startswith("animations/"), (
            f"{entry['clip']} file path wrong"
        )
        assert entry["file"].endswith(".glb"), (
            f"{entry['clip']} file extension wrong"
        )
        assert entry["clip"] in entry["states"], (
            f"{entry['clip']} state binding missing self-reference"
        )


def test_phase_47_clip_name_matches_slot_stem():
    data = json.loads(MANIFEST.read_text())
    for entry in data["animations"]:
        if entry["clip"] in PHASE_47_CLIPS:
            expected_file = f"animations/{entry['clip']}.glb"
            assert entry["file"] == expected_file, (
                f"{entry['clip']} file path mismatch — expected {expected_file}, got {entry['file']}"
            )


def test_legacy_v2_entries_preserved():
    """Regression guard — v2.0 character-animation entries stay untouched."""
    data = json.loads(MANIFEST.read_text())
    v2_files = {a["file"] for a in data["animations"]}
    for required in (
        "animations/sleep_normally.glb",
        "animations/indoor_swing.glb",
        "animations/bass_beats.glb",
        "animations/funny_dancing_01.glb",
    ):
        assert required in v2_files, f"v2.0 entry {required} missing — regression"


def test_character_field_preserved():
    data = json.loads(MANIFEST.read_text())
    assert data.get("character") == "character.glb"
