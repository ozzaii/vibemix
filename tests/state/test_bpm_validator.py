# SPDX-License-Identifier: Apache-2.0
"""validate_bpm coverage (Phase 6 Wave 2).

CONTEXT D-LOCKED §BPM Half/Double Validator. Per-profile snap to bpm_range.
Zero/negative inputs short-circuit to (0.0, False) — defensive guard for
estimate_bpm's "no signal" marker.

Test fixtures load the canonical 5 shipped profiles via load_profile.
"""

from __future__ import annotations

import pytest

from vibemix.state.genre import load_profile, validate_bpm


@pytest.fixture
def techno():
    """techno: bpm_range=[125, 175]"""
    return load_profile("techno")


@pytest.fixture
def house():
    """house: bpm_range=[118, 130]"""
    return load_profile("house")


@pytest.fixture
def pop():
    """pop: bpm_range=[95, 130]"""
    return load_profile("pop")


@pytest.fixture
def dnb():
    """drum_and_bass: bpm_range=[165, 180]"""
    return load_profile("drum_and_bass")


@pytest.fixture
def disco():
    """disco: bpm_range=[110, 125]"""
    return load_profile("disco")


# ---------- Defensive no-signal shortcuts ----------


def test_zero_bpm_short_circuits(techno):
    assert validate_bpm(0.0, techno) == (0.0, False)


def test_negative_bpm_short_circuits(techno):
    """Defensive: estimate_bpm can theoretically emit negative on math glitch."""
    assert validate_bpm(-5.0, techno) == (0.0, False)


# ---------- In-range pass-through ----------


def test_in_range_pass_through_techno(techno):
    bpm, corrected = validate_bpm(128.0, techno)
    assert bpm == 128.0
    assert corrected is False


def test_in_range_pass_through_at_lo_boundary(techno):
    # 125.0 is exactly at lo (inclusive)
    assert validate_bpm(125.0, techno) == (125.0, False)


def test_in_range_pass_through_at_hi_boundary(techno):
    # 175.0 is exactly at hi (inclusive)
    assert validate_bpm(175.0, techno) == (175.0, False)


# ---------- Half-detected, double-corrected ----------


def test_half_detected_doubles_techno(techno):
    """63 BPM autocorr on a 126 BPM techno track → snap to 126."""
    bpm, corrected = validate_bpm(63.0, techno)
    assert bpm == 126.0
    assert corrected is True


def test_techno_62_NOT_corrected_doubled_falls_below_range(techno):
    """62*2=124, which is BELOW techno's 125 lo. So no half-snap fires —
    return raw. Documents the boundary case in 06-CONTEXT.md."""
    bpm, corrected = validate_bpm(62.0, techno)
    assert bpm == 62.0
    assert corrected is False


def test_drum_and_bass_85_doubles_to_170(dnb):
    """85*2=170, inside D&B 165-180 → corrected."""
    assert validate_bpm(85.0, dnb) == (170.0, True)


def test_disco_60_doubles_to_120(disco):
    """60*2=120, inside disco 110-125 → corrected."""
    assert validate_bpm(60.0, disco) == (120.0, True)


# ---------- Double-detected, halve-corrected ----------


def test_double_detected_halves_techno(techno):
    """250/2 = 125 — exactly at techno's lo boundary."""
    assert validate_bpm(250.0, techno) == (125.0, True)


def test_double_detected_halves_pop(pop):
    """200/2 = 100, inside pop's 95-130 range."""
    assert validate_bpm(200.0, pop) == (100.0, True)


def test_drum_and_bass_350_halves_to_175(dnb):
    """350/2 = 175 inside D&B's 165-180 range."""
    assert validate_bpm(350.0, dnb) == (175.0, True)


# ---------- Out-of-range pass-through (downstream gate filters) ----------


def test_house_140_NOT_corrected_doubled_above_halved_below(house):
    """140 above range (118-130); 140*2=280 above; 140/2=70 below. Return raw."""
    bpm, corrected = validate_bpm(140.0, house)
    assert bpm == 140.0
    assert corrected is False


def test_techno_30_NOT_corrected_both_directions_out_of_range(techno):
    """30 < 125; 30*2=60 < 125; 30/2=15 < 125. Return raw."""
    assert validate_bpm(30.0, techno) == (30.0, False)


def test_was_corrected_flag_false_on_in_range(techno):
    """Confirm the corrected flag is False whenever the input passes through."""
    bpm, corrected = validate_bpm(150.0, techno)
    assert bpm == 150.0
    assert corrected is False
