# SPDX-License-Identifier: Apache-2.0
"""Phase 59 (DECK-01/02) — to_camelot, the load-bearing pure normalizer.

Rekordbox XML carries ``Tonality`` as musical notation (``Am`` / ``F#m`` /
``Cm`` — confirmed in the fixture), NOT Camelot codes. Every ``key:`` citation
the coach reasons on depends on this conversion existing BEFORE any harmonic
prompt (Phase 60). The contract mirrors ``track_resolver``'s honest-unknown
discipline: degrade to ``None`` (→ ``key=unknown``) on empty/odd input —
NEVER raise, NEVER guess a Camelot code.

Phase 59 ships ``to_camelot`` ONLY. ``is_clash`` / ``compatible`` are Phase 60
and MUST NOT leak into this module.
"""

from __future__ import annotations

import pytest

from vibemix.state.harmonics import (
    compatible,
    is_clash,
    semitone_distance,
    to_camelot,
)

# The 24 musical-notation → Camelot pairs (the full wheel, both enharmonic
# spellings where they differ). This is the table-driven oracle.
MUSICAL_TO_CAMELOT_PAIRS = [
    # minors (inner wheel, "A")
    ("Abm", "1A"),
    ("G#m", "1A"),  # enharmonic alias of Abm
    ("Ebm", "2A"),
    ("D#m", "2A"),  # enharmonic alias of Ebm
    ("Bbm", "3A"),
    ("A#m", "3A"),  # enharmonic alias of Bbm
    ("Fm", "4A"),
    ("Cm", "5A"),
    ("Gm", "6A"),
    ("Dm", "7A"),
    ("Am", "8A"),
    ("Em", "9A"),
    ("Bm", "10A"),
    ("F#m", "11A"),
    ("Gbm", "11A"),  # enharmonic alias of F#m
    ("C#m", "12A"),
    ("Dbm", "12A"),  # enharmonic alias of C#m
    # majors (outer wheel, "B")
    ("B", "1B"),
    ("F#", "2B"),
    ("Gb", "2B"),  # enharmonic alias of F#
    ("Db", "3B"),
    ("C#", "3B"),  # enharmonic alias of Db
    ("Ab", "4B"),
    ("G#", "4B"),  # enharmonic alias of Ab
    ("Eb", "5B"),
    ("D#", "5B"),  # enharmonic alias of Eb
    ("Bb", "6B"),
    ("A#", "6B"),  # enharmonic alias of Bb
    ("F", "7B"),
    ("C", "8B"),
    ("G", "9B"),
    ("D", "10B"),
    ("A", "11B"),
    ("E", "12B"),
]


@pytest.mark.parametrize("raw,expected", MUSICAL_TO_CAMELOT_PAIRS)
def test_musical_notation_maps_to_camelot(raw, expected):
    """Every musical-notation tag normalizes to its Camelot code (incl.
    enharmonic aliases: G#m == Abm == 1A)."""
    assert to_camelot(raw) == expected


def test_load_bearing_canonical_pairs():
    """The five RESEARCH-cited anchors, asserted directly as a smoke gate."""
    assert to_camelot("Am") == "8A"
    assert to_camelot("F#m") == "11A"
    assert to_camelot("Cm") == "5A"
    assert to_camelot("Gm") == "6A"
    assert to_camelot("Dm") == "7A"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("8A", "8A"),  # already-Camelot passthrough
        ("8a", "8A"),  # lower-case Camelot upper-cased
        ("12B", "12B"),
        ("1A", "1A"),
        ("10b", "10B"),
        (" 8A ", "8A"),  # whitespace stripped
    ],
)
def test_camelot_input_passes_through_uppercased(raw, expected):
    """A Camelot code in passes through (upper-cased, stripped)."""
    assert to_camelot(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1m", "8A"),  # open-key minor → Camelot (1m == Am == 8A)
        ("1d", "8B"),  # open-key major → Camelot (1d == C == 8B)
        ("6m", "1A"),  # open-key minor 6m == Abm == 1A
        ("6d", "1B"),  # open-key major 6d == B == 1B
        ("12m", "7A"),  # open-key minor 12m == Dm == 7A
        ("12d", "7B"),  # open-key major 12d == F == 7B
    ],
)
def test_open_key_form_maps_to_camelot(raw, expected):
    """Open-key form ('Nm' minor / 'Nd' major) normalizes to Camelot."""
    assert to_camelot(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",  # empty
        None,  # None
        "not-a-key",  # garbage
        "garbage",
        "13A",  # out-of-range Camelot number
        "0A",  # out-of-range (Camelot starts at 1)
        "8C",  # invalid wheel letter
        "Hm",  # not a real note
        "   ",  # whitespace-only
        "13m",  # out-of-range open-key
    ],
)
def test_unrecognized_input_returns_none_never_raises(raw):
    """Empty / None / garbage / out-of-range → None, NEVER raises (honest
    unknown — degrades to key=unknown rather than guessing a Camelot code)."""
    assert to_camelot(raw) is None


# =====================================================================
# Phase 60 (HARMONIC-01) — the deterministic Camelot clash predicate.
# Same table-oracle shape as to_camelot above: module-level (a, b) pair
# lists + parametrized assertions, plus an explicit anchors smoke gate,
# plus a never-raises garbage test.
#
# Verified circle-of-fifths derivation (60-RESEARCH §Pattern 1):
# same-letter hour-distance → pitch-class semitone distance → verdict.
#   hour 0 → 0 st   (same key)             → SAFE
#   hour 1 → 5/7 st (perfect fifth)        → SAFE  (adjacent ±1, bread-and-butter)
#   hour 2 → 2 st   (+2 energy move)       → SAFE
#   hour 3 → 3 st                          → NEITHER (drift; silent)
#   hour 4 → 4 st                          → NEITHER (drift; silent)
#   hour 5 → 1 SEMITONE                    → CLASH
#   hour 6 → 6 st   (tritone)              → CLASH
#   hour 7 → 1 SEMITONE                    → CLASH
# Cross-letter same-number = relative major/minor = SAFE.
# =====================================================================

# CLASH band — same-letter hours {5,6,7}, all keyed off 8A (the 1-semitone /
# tritone dissonance that genuinely fights on a melodic overlap).
CLASH_PAIRS = [
    ("8A", "3A"),  # hour-distance 5 = 1 semitone
    ("8A", "1A"),  # hour-distance 5 = 1 semitone
    ("8A", "2A"),  # hour-distance 6 = tritone
]

# SAFE band — same key, adjacent fifth (±1), +2 energy, relative major/minor.
SAFE_PAIRS = [
    ("5A", "5A"),  # hour-distance 0 = same key
    ("8A", "9A"),  # hour-distance 1 = adjacent perfect fifth
    ("8A", "7A"),  # hour-distance 1 = adjacent perfect fifth (other side)
    ("8A", "10A"),  # hour-distance 2 = +2 energy boost
    ("8A", "6A"),  # hour-distance 2 = -2 energy move (NOT drift)
    ("8A", "8B"),  # relative major/minor — same number, swapped letter
]

# DRIFT / "neither" zone — same-letter hours {3,4}: is_clash False AND
# compatible False (stay SILENT; a wrong key tag here is indistinguishable
# from a real drift, so we say nothing).
DRIFT_PAIRS = [
    ("8A", "5A"),  # hour-distance 3 = drift
    ("8A", "12A"),  # hour-distance 4 = drift
]


@pytest.mark.parametrize("a,b", CLASH_PAIRS)
def test_clash_pairs_flag(a, b):
    """The unambiguous 1-semitone / tritone band (hours 5/6/7) → is_clash True.
    Symmetric — order must not matter."""
    assert is_clash(a, b) is True
    assert is_clash(b, a) is True


@pytest.mark.parametrize("a,b", SAFE_PAIRS + DRIFT_PAIRS)
def test_safe_pairs_never_flag(a, b):
    """SAFE pairs (same / fifth / +2 / relative) AND the drift "neither" zone
    never flag as a clash — NARROW is_clash, conservative-by-default."""
    assert is_clash(a, b) is False
    assert is_clash(b, a) is False


@pytest.mark.parametrize("a,b", SAFE_PAIRS)
def test_compatible_safe_pairs(a, b):
    """SAFE pairs are explicitly asserted compatible."""
    assert compatible(a, b) is True
    assert compatible(b, a) is True


@pytest.mark.parametrize("a,b", DRIFT_PAIRS)
def test_drift_pairs_not_compatible_not_clash(a, b):
    """The drift zone (hours 3/4) is the deliberate silent middle: neither a
    clash nor an asserted-compatible pair."""
    assert is_clash(a, b) is False
    assert compatible(a, b) is False


def test_canonical_clash_safe_anchors():
    """The RESEARCH-cited anchors, asserted directly as a smoke gate."""
    # CLASH
    assert is_clash("8A", "3A") is True  # 1 semitone
    assert is_clash("8A", "1A") is True  # 1 semitone
    # SAFE — the pairs Kaan would happily mix must NOT flag
    assert is_clash("8A", "9A") is False  # adjacent fifth
    assert is_clash("8A", "8B") is False  # relative major/minor
    assert is_clash("8A", "10A") is False  # +2 energy
    assert is_clash("5A", "5A") is False  # same key
    # compatible mirror
    assert compatible("8A", "9A") is True
    assert compatible("8A", "10A") is True
    assert compatible("8A", "8B") is True
    assert compatible("8A", "3A") is False  # clash is not compatible
    assert compatible("8A", "5A") is False  # drift not asserted compatible


@pytest.mark.parametrize(
    "raw_a,raw_b",
    [
        (None, "8A"),
        ("8A", None),
        ("", "8A"),
        ("garbage", "8A"),
        ("not-a-key", "8A"),
        ("13A", "8A"),  # out-of-range Camelot number
        ("0A", "8A"),  # out-of-range (starts at 1)
        ("8C", "8A"),  # invalid wheel letter
        (None, None),
    ],
)
def test_predicate_honest_none_never_raises(raw_a, raw_b):
    """None / empty / garbage / out-of-range in → is_clash and compatible both
    return False, never raise (honest-unknown; we never flag what we can't
    prove dissonant)."""
    assert is_clash(raw_a, raw_b) is False
    assert compatible(raw_a, raw_b) is False


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("8A", "3A", 1),  # hour-distance 5 → 1 semitone
        ("8A", "1A", 1),  # hour-distance 5 → 1 semitone
        ("8A", "2A", 6),  # hour-distance 6 → tritone
        ("8A", "9A", 5),  # hour-distance 1 → perfect fifth (5 st)
        ("8A", "10A", 2),  # hour-distance 2 → +2 semitones
        ("5A", "5A", 0),  # hour-distance 0 → same key
        ("8A", "5A", 3),  # hour-distance 3 → 3 semitones (drift)
        ("8A", "12A", 4),  # hour-distance 4 → 4 semitones (drift)
    ],
)
def test_semitone_distance_anchors(a, b, expected):
    """Same-letter hour-distance → pitch-class semitone distance (the verified
    table). Lets the coach narrate the interval without the LLM computing it."""
    assert semitone_distance(a, b) == expected


@pytest.mark.parametrize(
    "a,b",
    [
        ("8A", "8B"),  # cross-letter — not on a single same-letter ring
        ("8A", "9B"),
        (None, "8A"),
        ("8A", "garbage"),
    ],
)
def test_semitone_distance_cross_letter_or_none_is_none(a, b):
    """Cross-letter or None-in → None (no single same-letter semitone ring)."""
    assert semitone_distance(a, b) is None
