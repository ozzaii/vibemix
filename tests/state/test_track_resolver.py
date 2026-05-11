# SPDX-License-Identifier: Apache-2.0
"""derive_audible_deck + derive_audible_track ladder coverage.

Pins every branch of v4:1093-1135 (deck) and v4:1138-1159 (track) plus the
xfader_factor 4-tier boundaries for both sides.
"""

from __future__ import annotations

import pytest

from vibemix.state import derive_audible_deck, derive_audible_track

# --------- derive_audible_deck ---------


def test_deck_not_connected_returns_none():
    out = derive_audible_deck({"play": True, "vol": 127}, {"play": True, "vol": 127}, 64, False)
    assert out == ("none", 0.0)


def test_deck_no_play_returns_none():
    # play=False for both decks → both weights = 0.0 → ("none", 0.0).
    out = derive_audible_deck({"play": False, "vol": 127}, {"play": False, "vol": 127}, 64, True)
    assert out == ("none", 0.0)


def test_deck_low_vol_returns_none():
    # vol=10 → vol/127 ≈ 0.079 < 0.1 → weight = 0.0 → ("none", 0.0).
    out = derive_audible_deck({"play": True, "vol": 10}, {"play": True, "vol": 10}, 64, True)
    assert out == ("none", 0.0)


@pytest.mark.parametrize(
    "xfader,expected_factor",
    [
        (0, 1.0),
        (15, 1.0),
        (16, 1.0),  # still < 48 → 1.0 on A
        (47, 1.0),
        (48, 0.7),
        (79, 0.7),
        (80, 0.3),
        (81, 0.3),
        (111, 0.3),
        (112, 0.0),
        (127, 0.0),
    ],
)
def test_deck_xfader_factors_A(xfader, expected_factor):
    # vol=127 (vol/127=1.0), play=True → weight = expected_factor.
    # Push deck B fully silent so the dominant-A branches fire predictably.
    out = derive_audible_deck({"play": True, "vol": 127}, {"play": False, "vol": 0}, xfader, True)
    if expected_factor == 0.0:
        # Both weights are <0.05 → ("none", 0.0).
        assert out == ("none", 0.0)
    elif expected_factor >= 0.7:
        # wa >= 0.7, wb = 0 → ("A", min(1.0, wa)) → ("A", expected_factor).
        # When expected_factor == 1.0, the conf is exactly 1.0.
        assert out[0] == "A"
        assert out[1] == pytest.approx(expected_factor, rel=1e-2)
    else:
        # expected_factor 0.3: wa = 0.3, wb = 0. Then "wa > 0.3" fails (not strictly
        # greater); falls through to "wa > wb" → ("A", max(0.4, wa-wb)) = ("A", 0.4).
        assert out == ("A", 0.4)


@pytest.mark.parametrize(
    "xfader,expected_factor",
    [
        (0, 0.0),
        (15, 0.0),
        (16, 0.3),
        (47, 0.3),
        (48, 0.7),
        (80, 0.7),
        (81, 1.0),
        (111, 1.0),
        (112, 1.0),
        (127, 1.0),
    ],
)
def test_deck_xfader_factors_B(xfader, expected_factor):
    out = derive_audible_deck({"play": False, "vol": 0}, {"play": True, "vol": 127}, xfader, True)
    if expected_factor == 0.0:
        assert out == ("none", 0.0)
    elif expected_factor >= 0.7:
        assert out[0] == "B"
        assert out[1] == pytest.approx(expected_factor, rel=1e-2)
    else:
        # B-factor 0.3 → wb = 0.3, wa = 0; "wb > 0.3" fails (not strict);
        # falls through to "wa > wb" (False) → returns ("B", max(0.4, wb-wa)) = ("B", 0.4).
        assert out == ("B", 0.4)


def test_deck_dominant_A():
    # xfader=0 (full-A factor 1.0) → wa=1.0, wb=0.0 → ("A", min(1.0, 1.0)).
    out = derive_audible_deck({"play": True, "vol": 127}, {"play": False, "vol": 0}, 0, True)
    assert out == ("A", 1.0)


def test_deck_dominant_B():
    # xfader=127 (full-B factor 1.0) → wb=1.0, wa=0.0 → ("B", 1.0).
    out = derive_audible_deck({"play": False, "vol": 0}, {"play": True, "vol": 127}, 127, True)
    assert out == ("B", 1.0)


def test_deck_mix_branch():
    # Both decks full center: xfader=64 (factor 0.7 for both).
    # wa = 1.0 * 0.7 = 0.7; wb = 0.7. Both > 0.2 → ("mix", min(0.5, max(0.7, 0.7))) = ("mix", 0.5).
    out = derive_audible_deck({"play": True, "vol": 127}, {"play": True, "vol": 127}, 64, True)
    assert out == ("mix", 0.5)


def test_deck_fallback_dominant():
    # deck_a vol=80, deck_b vol=30, xfader=64 (factor 0.7 for both).
    # wa = (80/127)*0.7 ≈ 0.441; wb = (30/127)*0.7 ≈ 0.165.
    # wa > 0.3? YES. wb < 0.1? NO (0.165). → skip "A-only" branch.
    # wa > 0.2 AND wb > 0.2? wb = 0.165 → no. → skip "mix" branch.
    # Falls through to wa > wb → ("A", max(0.4, 0.441-0.165)) = ("A", max(0.4, 0.276)) = ("A", 0.4).
    out = derive_audible_deck({"play": True, "vol": 80}, {"play": True, "vol": 30}, 64, True)
    assert out[0] == "A"
    assert out[1] == pytest.approx(0.4, abs=1e-3)


# --------- derive_audible_track ---------


def test_track_not_audible_returns_none_zero():
    assert derive_audible_track("Daft Punk - One More Time", "A", 0.8, False) == (None, 0.0)


def test_track_no_title_returns_none_zero():
    assert derive_audible_track(None, "A", 0.8, True) == (None, 0.0)


def test_track_empty_title_returns_none_zero():
    # `not track_title` catches "" too — same guard.
    assert derive_audible_track("", "A", 0.8, True) == (None, 0.0)


def test_track_deck_none_returns_03():
    out = derive_audible_track("X", "none", 0.0, True)
    assert out == ("X", 0.3)


def test_track_deck_mix_returns_04():
    out = derive_audible_track("X", "mix", 0.5, True)
    assert out == ("X", 0.4)


def test_track_deck_dominant_clamps_to_min_05():
    # deck_confidence=0.2 → clamped to 0.5 (the min(0.85, max(0.5, 0.2)) lower clamp).
    out = derive_audible_track("X", "A", 0.2, True)
    assert out == ("X", 0.5)


def test_track_deck_dominant_passes_through():
    out = derive_audible_track("X", "A", 0.6, True)
    assert out == ("X", 0.6)


def test_track_deck_dominant_clamps_to_max_085():
    # deck_confidence=0.95 → clamped to 0.85 (upper clamp).
    out = derive_audible_track("X", "A", 0.95, True)
    assert out == ("X", 0.85)


def test_track_deck_dominant_B_branch():
    # The dominant-deck branch handles 'B' identically — pin it for coverage.
    out = derive_audible_track("X", "B", 0.7, True)
    assert out == ("X", 0.7)
