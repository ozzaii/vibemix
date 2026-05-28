# SPDX-License-Identifier: Apache-2.0
"""Phase 97 / ONBOARD-03 — Hercules Inpulse 300 vs 300 MK2 disambiguation.

The two profiles ship side-by-side (``hercules_inpulse_300.json`` legacy
+ ``hercules_inpulse_300_mk2.json`` current-gen) and their port_name_hints
overlap as substrings: the legacy 300's ``"DJControl Inpulse 300"`` IS a
substring of the MK2's ``"DJControl Inpulse 300 MK2"``. Under pure
first-match-alphabetic the MK2 port would resolve to the legacy profile
(``hercules_inpulse_300`` sorts before ``hercules_inpulse_300_mk2``).

This test pins the disambiguation. The fix in
``src/vibemix/midi/registry.py::find_mapping`` is longest-hint-wins:
the matching hint with the LONGEST substring picks the profile,
alphabetic-id breaks ties on equal-length matches.

Pitfalls §P3 binding: DJUCED treats the two units as different
controllers via USB ``iSerialNumber``. vibemix can't read iSerialNumber
directly from mido (the port name is the only signal), so we rely on
the port-name-hint disambiguation as a pragmatic stand-in. Real-MK2
hardware ear-pass discharges §LEARN-MK2-DETECTION (P98).
"""

from __future__ import annotations

import pytest

from vibemix.midi.registry import find_mapping


def test_legacy_300_port_resolves_to_legacy_profile() -> None:
    """A pure-300 port name MUST resolve to the legacy 300 profile."""
    profile = find_mapping("DJControl Inpulse 300 MIDI 1")
    assert profile is not None, "legacy 300 port should match a profile"
    assert profile.id == "hercules_inpulse_300", (
        f"legacy 300 port resolved to {profile.id!r}; expected 'hercules_inpulse_300'"
    )


def test_mk2_port_with_full_qualifier_resolves_to_mk2_profile() -> None:
    """A port name carrying 'DJControl Inpulse 300 MK2' MUST resolve to MK2.

    This is the disambiguation case — the legacy 300's hint
    ``"DJControl Inpulse 300"`` IS a substring of this port name, but the
    MK2's hint ``"DJControl Inpulse 300 MK2"`` is LONGER and equally a
    substring. Longest-hint-wins picks the MK2.
    """
    profile = find_mapping("DJControl Inpulse 300 MK2 MIDI 1")
    assert profile is not None, "MK2 port should match a profile"
    assert profile.id == "hercules_inpulse_300_mk2", (
        f"MK2-qualified port resolved to {profile.id!r}; "
        f"expected 'hercules_inpulse_300_mk2'"
    )


def test_mk2_port_with_short_qualifier_resolves_to_mk2_profile() -> None:
    """Short-form 'Inpulse 300 MK2' MUST also resolve to MK2.

    The legacy 300's hint ``"DJControl Inpulse 300"`` is NOT a substring
    of this port name, so only the MK2's ``"Inpulse 300 MK2"`` hint
    matches — trivially picks the MK2.
    """
    profile = find_mapping("Inpulse 300 MK2")
    assert profile is not None
    assert profile.id == "hercules_inpulse_300_mk2"


def test_mk2_port_case_insensitive() -> None:
    """Case-insensitive substring matching: 'mk2' in port name still picks MK2."""
    profile = find_mapping("djcontrol inpulse 300 mk2 midi 1")
    assert profile is not None
    assert profile.id == "hercules_inpulse_300_mk2"


def test_unrelated_port_name_returns_none() -> None:
    """Negative control — a port name with no matching hint returns None."""
    profile = find_mapping("Some Other Controller XYZ-9000")
    assert profile is None


def test_empty_port_name_returns_none() -> None:
    """Empty / non-str port names return None (existing behaviour pin)."""
    assert find_mapping("") is None
    assert find_mapping("   ") is None  # whitespace-only contains no hint


def test_other_pioneer_ports_unaffected_by_disambiguation_fix() -> None:
    """Regression guard — the longest-hint rule must not regress FLX4/RX3 etc."""
    flx4 = find_mapping("Pioneer DDJ-FLX4 MIDI 1")
    assert flx4 is not None
    assert flx4.id == "pioneer_ddj_flx4"
    rx3 = find_mapping("XDJ-RX3 USB MIDI")
    assert rx3 is not None
    assert rx3.id == "pioneer_xdj_rx3"


@pytest.mark.parametrize(
    "port_name,expected_id",
    [
        ("DJControl Inpulse 300 MIDI 1", "hercules_inpulse_300"),
        ("DJControl Inpulse 300 MK2 MIDI 1", "hercules_inpulse_300_mk2"),
        ("Inpulse 300 MK2", "hercules_inpulse_300_mk2"),
        ("Inpulse-300-MK2 MIDI Bridge", "hercules_inpulse_300_mk2"),
        ("DJCONTROL INPULSE 300 MK2", "hercules_inpulse_300_mk2"),  # case-insensitive
        ("DJCONTROL INPULSE 300", "hercules_inpulse_300"),  # case-insensitive
    ],
)
def test_disambiguation_table(port_name: str, expected_id: str) -> None:
    """Parametric table — covers the 6 dispositions the production wire emits."""
    profile = find_mapping(port_name)
    assert profile is not None, f"port {port_name!r} should match"
    assert profile.id == expected_id, (
        f"port {port_name!r} resolved to {profile.id!r}; expected {expected_id!r}"
    )
