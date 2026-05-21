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

from vibemix.state.harmonics import to_camelot

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
