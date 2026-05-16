"""Unit tests for src/vibemix/midi/map_loader.py — MidiMapLoader registry.

Covers:
- Schema validation on construction (all 10 shipped JSONs pass).
- .load() / .all_maps() / .lookup() public API.
- Canonical FLX4 round-trip lookups (EQ, fader/vol, sync + sync_alt, cue).
- Negative cases: missing id, unmapped event, unsupported msg type, bad JSON.
- T-23-04 mitigation: invalid JSON raises MapValidationError with filename.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.midi.map_loader import (
    CONTROLLERS_DIR,
    MapValidationError,
    MidiMapLoader,
    SCHEMA_PATH,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic mido.Message-like objects (no mido import needed).
# ---------------------------------------------------------------------------


def _cc(channel: int, control: int, value: int = 64) -> MagicMock:
    m = MagicMock()
    m.type = "control_change"
    m.channel = channel
    m.control = control
    m.value = value
    return m


def _note_on(channel: int, note: int, velocity: int = 127) -> MagicMock:
    m = MagicMock()
    m.type = "note_on"
    m.channel = channel
    m.note = note
    m.velocity = velocity
    return m


def _note_off(channel: int, note: int, velocity: int = 0) -> MagicMock:
    m = MagicMock()
    m.type = "note_off"
    m.channel = channel
    m.note = note
    m.velocity = velocity
    return m


def _program_change(channel: int, program: int) -> MagicMock:
    m = MagicMock()
    m.type = "program_change"
    m.channel = channel
    m.program = program
    return m


# ---------------------------------------------------------------------------
# Construction + discovery
# ---------------------------------------------------------------------------


def test_loader_discovers_10_maps():
    loader = MidiMapLoader()
    maps = loader.all_maps()
    assert len(maps) == 10, f"Expected 10 maps, got {len(maps)}: {sorted(maps)}"


def test_loader_expected_ids_present():
    loader = MidiMapLoader()
    ids = set(loader.all_maps().keys())
    expected = {
        "ddj-flx4",
        "ddj-400",
        "ddj-200",
        "ddj-rev1",
        "mc-7000",
        "mc-6000",
        "kontrol-s4",
        "kontrol-s2",
        "mixtrack-platinum-fx",
        "mixtrack-pro-fx",
    }
    assert ids == expected, f"Missing: {expected - ids}; Extra: {ids - expected}"


def test_loader_validates_schema_for_all_shipped_maps():
    """Construction succeeds without raising — implicit schema validation pass."""
    loader = MidiMapLoader()
    # If we reach here, every shipped JSON passed jsonschema.validate.
    for name, m in loader.all_maps().items():
        assert "vendor" in m
        assert "model" in m
        assert "description" in m
        assert "verified" in m
        assert "controls" in m and len(m["controls"]) > 0


def test_loader_schema_path_resolves():
    assert SCHEMA_PATH.exists(), f"schema.json missing at {SCHEMA_PATH}"
    assert CONTROLLERS_DIR.exists(), f"controllers/ missing at {CONTROLLERS_DIR}"


# ---------------------------------------------------------------------------
# .load() — lookup-by-id
# ---------------------------------------------------------------------------


def test_loader_load_returns_dict():
    loader = MidiMapLoader()
    m = loader.load("ddj-flx4")
    assert m["vendor"] == "Pioneer"
    assert m["model"] == "DDJ-FLX4"


def test_loader_load_missing_raises_with_list():
    loader = MidiMapLoader()
    with pytest.raises(KeyError) as excinfo:
        loader.load("nonexistent-controller")
    msg = str(excinfo.value)
    # At least three valid IDs should be surfaced for discoverability.
    valid_count = sum(
        1
        for vid in ["ddj-flx4", "ddj-400", "kontrol-s4", "mc-7000"]
        if vid in msg
    )
    assert valid_count >= 3, f"Expected 3+ valid IDs in error msg, got: {msg}"


# ---------------------------------------------------------------------------
# .lookup() — canonical FLX4 round-trips
# ---------------------------------------------------------------------------


def test_loader_lookup_flx4_eq_low_a():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    # channel 0, cc 0x0F (= 15) → eq_low_a per cohost_v4 line 590.
    assert loader.lookup(cmap, _cc(channel=0, control=0x0F)) == "eq_low_a"


def test_loader_lookup_flx4_eq_low_b():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _cc(channel=1, control=0x0F)) == "eq_low_b"


def test_loader_lookup_flx4_eq_hi_a():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    # channel 0, cc 7 → eq_hi_a.
    assert loader.lookup(cmap, _cc(channel=0, control=7)) == "eq_hi_a"


def test_loader_lookup_flx4_vol_a():
    """FLX4 'fader' for deck A == channel volume == vol_a per cohost_v4 line 587."""
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _cc(channel=0, control=19)) == "vol_a"


def test_loader_lookup_flx4_xfader():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _cc(channel=6, control=31)) == "xfader"


def test_loader_lookup_flx4_sync_a_poc_binding():
    """note 0x60 = 96 is the cohost_v4-captured Sync binding (defensive ship)."""
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_on(channel=0, note=0x60)) == "sync_a"


def test_loader_lookup_flx4_sync_a_alt_mixxx_binding():
    """note 0x58 = 88 is the Mixxx-canonical defensive alt binding (pending verdict)."""
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_on(channel=0, note=0x58)) == "sync_a_alt"


def test_loader_lookup_flx4_cue_a():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_on(channel=0, note=0x0C)) == "cue_a"


def test_loader_lookup_flx4_play_b():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_on(channel=1, note=0x0B)) == "play_b"


def test_loader_lookup_note_off_resolves_same_as_note_on():
    """Semantic events are press-not-release: note_off resolves to the same semantic."""
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_off(channel=0, note=0x0C)) == "cue_a"


# ---------------------------------------------------------------------------
# .lookup() — negative cases
# ---------------------------------------------------------------------------


def test_loader_lookup_unmapped_cc_returns_none():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    # channel 5, cc 99 — unmapped.
    assert loader.lookup(cmap, _cc(channel=5, control=99)) is None


def test_loader_lookup_unmapped_note_returns_none():
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _note_on(channel=2, note=127)) is None


def test_loader_lookup_unsupported_msg_type_returns_none():
    """program_change and other non-cc/note messages return None, never raise."""
    loader = MidiMapLoader()
    cmap = loader.load("ddj-flx4")
    assert loader.lookup(cmap, _program_change(channel=0, program=5)) is None


# ---------------------------------------------------------------------------
# T-23-04 mitigation: bad JSON raises MapValidationError citing filename.
# ---------------------------------------------------------------------------


def test_loader_invalid_json_raises_map_validation_error(tmp_path, monkeypatch):
    """Writing a malformed map under controllers/ MUST fail loader construction
    with MapValidationError citing the filename — pins T-23-04 mitigation.
    """
    fake_controllers = tmp_path / "controllers"
    fake_controllers.mkdir()
    # Copy a valid JSON so the directory has at least one good entry, then add bad.
    good_src = CONTROLLERS_DIR / "ddj-flx4.json"
    (fake_controllers / "ddj-flx4.json").write_text(good_src.read_text())
    bad = fake_controllers / "bad.json"
    # Missing required fields (vendor, controls, etc.)
    bad.write_text(json.dumps({"model": "Bad"}))

    monkeypatch.setattr(
        "vibemix.midi.map_loader.CONTROLLERS_DIR", fake_controllers
    )
    with pytest.raises(MapValidationError) as excinfo:
        MidiMapLoader()
    # The error message must cite the offending filename.
    assert "bad.json" in str(excinfo.value)


def test_loader_malformed_json_text_raises_map_validation_error(
    tmp_path, monkeypatch
):
    """A JSON file with invalid JSON syntax must also surface as MapValidationError."""
    fake_controllers = tmp_path / "controllers"
    fake_controllers.mkdir()
    (fake_controllers / "bad-syntax.json").write_text(
        "{not valid json at all,,,"
    )
    monkeypatch.setattr(
        "vibemix.midi.map_loader.CONTROLLERS_DIR", fake_controllers
    )
    with pytest.raises(MapValidationError) as excinfo:
        MidiMapLoader()
    assert "bad-syntax.json" in str(excinfo.value)
