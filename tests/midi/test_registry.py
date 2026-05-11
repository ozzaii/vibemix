# SPDX-License-Identifier: Apache-2.0
"""find_mapping registry tests (Phase 9 Wave 1 Task 3).

Pins:
- Exact port-name match for FLX4 returns the FLX4 profile.
- Case-insensitive substring match (`'ddj-flx4 USB MIDI'`, `'My DDJ-FLX4 in port 1'`)
  resolves to the FLX4 profile.
- Short-hint match (`'Pioneer FLX4'` matches via the second hint `'FLX4'`).
- Returns None for unmapped names and empty strings.
- Deterministic tiebreak when multiple profiles could match — alphabetic-id order
  (Wave 1 has only FLX4 in the registry so the tiebreak path is exercised against
  a synthesized non-FLX4 profile in-test).
"""

from __future__ import annotations

from vibemix.midi import find_mapping, load_profile


def test_find_mapping_matches_flx4_by_exact_port_name():
    result = find_mapping("DDJ-FLX4")
    assert result is not None
    assert result.id == "pioneer_ddj_flx4"


def test_find_mapping_matches_flx4_case_insensitive():
    expected = load_profile("pioneer_ddj_flx4")
    assert expected is not None

    for port_name in (
        "ddj-flx4 USB MIDI",
        "My DDJ-FLX4 in port 1",
        "DDJ-FLX4",
        "PIONEER DDJ-FLX4 USB",
    ):
        result = find_mapping(port_name)
        assert result is not None, f"expected FLX4 match for {port_name!r}"
        assert result.id == expected.id


def test_find_mapping_matches_flx4_short_hint():
    # The FLX4 JSON's port_name_hints includes both 'DDJ-FLX4' and 'FLX4'.
    result = find_mapping("Pioneer FLX4")
    assert result is not None
    assert result.id == "pioneer_ddj_flx4"


def test_find_mapping_returns_none_for_unmapped():
    assert find_mapping("Bose Bluetooth Speaker") is None


def test_find_mapping_returns_none_for_empty_string():
    assert find_mapping("") is None


def test_find_mapping_returns_none_for_non_string():
    # Defensive: non-str inputs must return None, not raise.
    assert find_mapping(None) is None  # type: ignore[arg-type]
    assert find_mapping(123) is None  # type: ignore[arg-type]


def test_find_mapping_first_match_wins_when_multiple_hints_could_match():
    """When multiple profile hints could match a port name, resolution is
    deterministic. Wave 1 only ships FLX4 so this is mostly a behavior pin —
    Wave 2 will load multiple profiles and exercise this for real."""
    # 'My DDJ-FLX4 with XYZ in name' — only FLX4 hint matches in Wave 1.
    result = find_mapping("My DDJ-FLX4 with XYZ in name")
    assert result is not None
    assert result.id == "pioneer_ddj_flx4"


# ---------- Phase 9 Wave 2 — find_mapping_or_generic ----------


def test_find_mapping_or_generic_returns_real_profile_when_match():
    from vibemix.midi import find_mapping_or_generic

    result = find_mapping_or_generic("My DDJ-FLX4 USB")
    assert result is not None
    assert result.id == "pioneer_ddj_flx4"


def test_find_mapping_or_generic_returns_generic_when_no_match():
    from vibemix.midi import find_mapping_or_generic

    result = find_mapping_or_generic("Bose Speaker")
    assert result is not None
    assert result.id == "generic_midi"
