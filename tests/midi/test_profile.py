# SPDX-License-Identifier: Apache-2.0
"""ControllerProfile + JSON loader + pioneer_ddj_flx4.json tests (Phase 9 Wave 1).

Covers:
- Frozen-dataclass identity (raises FrozenInstanceError on attribute set).
- ``load_profile`` returns None on unknown name (sentinel for "no controller mapping").
- ``load_profile('pioneer_ddj_flx4')`` returns a ControllerProfile with the
  expected `id` / `display_name` / `port_name_hints` / `decks`.
- ``list_profiles()`` returns sorted profile stems including FLX4.
- Hand-written schema validator rejects missing `id`, empty `port_name_hints`,
  unknown `axis`, out-of-range `cc`.
- DDJ-FLX4 JSON encodes the v4 ``_CC_MAP`` (13 entries) + the live-discovered
  relative jog-move CCs + ``_NOTE_MAP`` (12 entries) — every (channel, cc) and
  (channel, note) pair must appear with matching field/kind.
- Axis assignments match v4 semantics (unipolar for vol/eq, bipolar for
  tempo/filter/xfader).
"""

from __future__ import annotations

import dataclasses

import pytest

from vibemix.midi import list_profiles, load_profile
from vibemix.midi.profile import _parse_profile

# v4 maps — re-stated here so test breaks if either v4 OR JSON drifts.
_V4_CC_MAP = {
    (0, 0x13): ("A", "vol"),
    (1, 0x13): ("B", "vol"),
    (0, 0x07): ("A", "eq_hi"),
    (1, 0x07): ("B", "eq_hi"),
    (0, 0x0B): ("A", "eq_mid"),
    (1, 0x0B): ("B", "eq_mid"),
    (0, 0x0F): ("A", "eq_low"),
    (1, 0x0F): ("B", "eq_low"),
    (0, 0x00): ("A", "tempo"),
    (1, 0x00): ("B", "tempo"),
    (6, 0x17): ("A", "filter"),
    (6, 0x18): ("B", "filter"),
    (6, 0x1F): ("M", "xfader"),
}
_LIVE_JOG_CC_MAP = {
    (0, 0x21): ("A", "jog"),
    (1, 0x21): ("B", "jog"),
    # Live FLX4 proof on 2026-06-01 emitted B-jog ticks on ch1/CC34
    # alongside jog-touch note54. Keep the original CC33 and accept this
    # additive hardware variant so product snapshots do not drop the move.
    (1, 0x22): ("B", "jog"),
}
_V4_NOTE_MAP = {
    (0, 0x0B): ("A", "play"),
    (1, 0x0B): ("B", "play"),
    (0, 0x0C): ("A", "cue"),
    (1, 0x0C): ("B", "cue"),
    (0, 0x60): ("A", "sync"),
    (1, 0x60): ("B", "sync"),
    (0, 0x36): ("A", "jog_touch"),
    (1, 0x36): ("B", "jog_touch"),
    (0, 0x10): ("A", "loop_in"),
    (1, 0x10): ("B", "loop_in"),
    (0, 0x11): ("A", "loop_out"),
    (1, 0x11): ("B", "loop_out"),
}


# ---------- ControllerProfile dataclass ----------


def test_controller_profile_is_frozen_dataclass():
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.id = "mutated"


# ---------- load_profile / list_profiles ----------


def test_load_profile_unknown_returns_none():
    assert load_profile("nonexistent_xyz") is None


def test_load_profile_pioneer_ddj_flx4_returns_profile():
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    assert profile.id == "pioneer_ddj_flx4"
    assert profile.display_name == "Pioneer DDJ-FLX4"
    assert "DDJ-FLX4" in profile.port_name_hints
    assert profile.decks == ("A", "B")


def test_list_profiles_includes_flx4():
    names = list_profiles()
    assert names == sorted(names), "list_profiles() must return sorted names"
    assert "pioneer_ddj_flx4" in names
    # Wave 2 shipped 10 controllers; Phase 97 / ONBOARD-03 added the Hercules
    # Inpulse 300 MK2 sibling (11th profile). Per-controller pins live in
    # tests/midi/test_profiles_all_controllers.py.
    assert len(names) == 11


# ---------- Schema validator: required-field + range checks ----------


def _baseline_payload() -> dict:
    return {
        "id": "test_profile",
        "display_name": "Test Profile",
        "port_name_hints": ["TEST"],
        "decks": ["A", "B"],
        "controls": {
            "vol_a": {
                "kind": "cc",
                "channel": 0,
                "cc": 19,
                "axis": "unipolar",
                "deck": "A",
                "field": "vol",
            },
        },
        "buttons": {
            "play_a": {"kind": "play", "channel": 0, "note": 11, "deck": "A"},
        },
    }


def test_schema_validator_rejects_missing_id():
    payload = _baseline_payload()
    del payload["id"]
    with pytest.raises(ValueError) as exc:
        _parse_profile(payload)
    msg = str(exc.value)
    assert "id" in msg and "required" in msg


def test_schema_validator_rejects_empty_port_name_hints():
    payload = _baseline_payload()
    payload["port_name_hints"] = []
    with pytest.raises(ValueError) as exc:
        _parse_profile(payload)
    msg = str(exc.value)
    assert "port_name_hints" in msg and "non-empty" in msg


def test_schema_validator_rejects_unknown_axis():
    payload = _baseline_payload()
    payload["controls"]["vol_a"]["axis"] = "tripolar"
    with pytest.raises(ValueError) as exc:
        _parse_profile(payload)
    msg = str(exc.value)
    assert "unipolar" in msg
    assert "bipolar" in msg
    assert "relative" in msg


def test_schema_validator_rejects_cc_out_of_range():
    payload = _baseline_payload()
    payload["controls"]["vol_a"]["cc"] = 200
    with pytest.raises(ValueError) as exc:
        _parse_profile(payload)
    msg = str(exc.value)
    assert "0..127" in msg


# ---------- DDJ-FLX4 JSON byte-equivalence to v4 maps ----------


def test_pioneer_ddj_flx4_json_encodes_v4_cc_map_byte_equivalent():
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None

    # Build (channel, cc) -> (deck or 'M', field) lookup from the JSON.
    json_lookup: dict[tuple[int, int], tuple[str, str]] = {}
    for binding in profile.controls.values():
        deck_key = binding.deck if binding.deck is not None else "M"
        json_lookup[(binding.channel, binding.cc)] = (deck_key, binding.field)

    for v4_key, v4_val in _V4_CC_MAP.items():
        assert v4_key in json_lookup, f"DDJ-FLX4 JSON missing v4 CC entry {v4_key} → {v4_val}"
        assert json_lookup[v4_key] == v4_val, (
            f"DDJ-FLX4 JSON CC entry {v4_key} = {json_lookup[v4_key]} drifted from v4 = {v4_val}"
        )
    for jog_key, jog_val in _LIVE_JOG_CC_MAP.items():
        assert jog_key in json_lookup, (
            f"DDJ-FLX4 JSON missing live jog CC entry {jog_key} -> {jog_val}"
        )
        assert json_lookup[jog_key] == jog_val
    # JSON must not introduce extra CC entries beyond the v4 map + hardware-
    # sniffed relative jog ticks.
    assert set(json_lookup.keys()) == set(_V4_CC_MAP.keys()) | set(_LIVE_JOG_CC_MAP.keys())


def test_pioneer_ddj_flx4_json_buttons_section_lists_all_v4_notes():
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None

    json_lookup: dict[tuple[int, int], tuple[str, str]] = {}
    for binding in profile.buttons.values():
        deck_key = binding.deck if binding.deck is not None else "M"
        json_lookup[(binding.channel, binding.note)] = (deck_key, binding.kind)

    for v4_key, v4_val in _V4_NOTE_MAP.items():
        assert v4_key in json_lookup, f"DDJ-FLX4 JSON missing v4 note entry {v4_key} → {v4_val}"
        assert json_lookup[v4_key] == v4_val, (
            f"DDJ-FLX4 JSON note {v4_key} = {json_lookup[v4_key]} drifted from v4 = {v4_val}"
        )
    assert set(json_lookup.keys()) == set(_V4_NOTE_MAP.keys())


def test_pioneer_ddj_flx4_json_axis_assignments_match_v4_semantics():
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None

    # Lookup by field+deck.
    by_field: dict[tuple[str, str], str] = {}  # (deck, field) -> axis
    for binding in profile.controls.values():
        deck_key = binding.deck if binding.deck is not None else "M"
        by_field[(deck_key, binding.field)] = binding.axis

    # Unipolar: vol + eq_hi + eq_mid + eq_low (knob position 0..127, no center).
    for deck in ("A", "B"):
        assert by_field[(deck, "vol")] == "unipolar"
        assert by_field[(deck, "eq_hi")] == "unipolar"
        assert by_field[(deck, "eq_mid")] == "unipolar"
        assert by_field[(deck, "eq_low")] == "unipolar"
    # Bipolar: tempo + filter + xfader (center=64).
    for deck in ("A", "B"):
        assert by_field[(deck, "tempo")] == "bipolar"
        assert by_field[(deck, "filter")] == "bipolar"
        assert by_field[(deck, "jog")] == "relative"
    assert by_field[("M", "xfader")] == "bipolar"
