# SPDX-License-Identifier: Apache-2.0
"""Harmonic key normalization — the load-bearing pure function for Phase 59+.

Rekordbox XML carries ``Tonality`` as musical notation (``Am`` / ``F#m`` /
``Cm`` — confirmed in the fixture), NOT Camelot codes. Every ``key:`` citation
the coach reasons on therefore depends on ``to_camelot()`` existing BEFORE any
harmonic prompt: ``DeckTrack.key`` keeps the raw tag, ``DeckTrack.camelot`` is
the normalized code the coach actually reasons on.

Contract mirrors ``track_resolver``'s honest-unknown discipline (PROJECT core
value, "trust the audio"): ``to_camelot`` degrades to ``None`` (→
``key=unknown``) on empty / odd / out-of-range input — it NEVER raises and
NEVER guesses a Camelot code.

Scope: Phase 59 shipped ``to_camelot``. Phase 60 adds ``is_clash`` /
``compatible`` / ``semitone_distance`` (the deterministic Camelot-wheel clash
table the LLM merely narrates) ON TOP of this normalizer — the LLM never
computes intervals, it only narrates the verdict the code already proved.

Table source: Camelot wheel canonical mapping
[mixedinkey.com/camelot-wheel + dj.studio/blog/camelot-wheel].
"""

from __future__ import annotations

import re

# Musical notation → Camelot. The 24-entry wheel with enharmonic aliases.
_MUSICAL_TO_CAMELOT: dict[str, str] = {
    # minors (inner wheel, "A")
    "Abm": "1A",
    "G#m": "1A",
    "Ebm": "2A",
    "D#m": "2A",
    "Bbm": "3A",
    "A#m": "3A",
    "Fm": "4A",
    "Cm": "5A",
    "Gm": "6A",
    "Dm": "7A",
    "Am": "8A",
    "Em": "9A",
    "Bm": "10A",
    "F#m": "11A",
    "Gbm": "11A",
    "C#m": "12A",
    "Dbm": "12A",
    # majors (outer wheel, "B")
    "B": "1B",
    "F#": "2B",
    "Gb": "2B",
    "Db": "3B",
    "C#": "3B",
    "Ab": "4B",
    "G#": "4B",
    "Eb": "5B",
    "D#": "5B",
    "Bb": "6B",
    "A#": "6B",
    "F": "7B",
    "C": "8B",
    "G": "9B",
    "D": "10B",
    "A": "11B",
    "E": "12B",
}

# Open Key ("Nm" minor / "Nd" major) → Camelot. A fixed rotation of the wheel
# anchored at OpenKey 1m == Camelot 8A, 1d == 8B:
#   camelot_number = ((openkey_number - 1 + 7) % 12) + 1
_OPEN_KEY_TO_CAMELOT: dict[str, str] = {
    f"{n}{ok_letter}": f"{((n - 1 + 7) % 12) + 1}{cam_letter}"
    for n in range(1, 13)
    for ok_letter, cam_letter in (("m", "A"), ("d", "B"))
}

# Already-Camelot recognizer: 1..12 followed by A or B.
_CAMELOT_RE = re.compile(r"^(1[0-2]|[1-9])[AB]$")
# Open-key recognizer: 1..12 followed by m (minor) or d (major), case-insensitive.
_OPEN_KEY_RE = re.compile(r"^(1[0-2]|[1-9])[md]$")


def to_camelot(raw: str | None) -> str | None:
    """Normalize a key tag to Camelot.

    Accepts three input forms — musical notation (``"Am"`` / ``"F#m"``),
    Camelot (``"8A"``), and open-key (``"1m"`` / ``"1d"``) — and returns the
    Camelot code (e.g. ``"8A"``). Returns ``None`` on empty / unrecognized /
    out-of-range input.

    NEVER raises: an odd or absent tag degrades to ``None`` (→ ``key=unknown``)
    rather than fabricating a Camelot code. This honest-unknown discipline is
    the anti-slop contract — a false-confident key is the exact hallucination
    class Phase 59 closes by construction.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    upper = s.upper()
    if _CAMELOT_RE.match(upper):  # already Camelot — passthrough, upper-cased
        return upper
    if s in _MUSICAL_TO_CAMELOT:  # musical notation (case-sensitive note names)
        return _MUSICAL_TO_CAMELOT[s]
    if _OPEN_KEY_RE.match(s.lower()):  # open-key form ("1m" / "1d")
        return _OPEN_KEY_TO_CAMELOT[s.lower()]
    return None  # unrecognized → honest None, never a guess


# =====================================================================
# Phase 60 (HARMONIC-01) — the deterministic Camelot-wheel clash predicate.
#
# The Camelot wheel IS the circle of fifths relabeled: each +1 hour (same
# letter) is +7 semitones in pitch. Re-deriving the tonic pitch-class per
# Camelot number gives the same-letter hour-distance → pitch-class semitone
# distance table below (verified computation, 60-RESEARCH §Pattern 1):
#   hour 0 → 0 semitones  (same key)               → SAFE
#   hour 1 → perfect fifth (5/7 st)                → SAFE  (adjacent ±1)
#   hour 2 → 2 semitones  (+2 energy move)         → SAFE
#   hour 3 → 3 semitones                           → NEITHER (drift; silent)
#   hour 4 → 4 semitones                           → NEITHER (drift; silent)
#   hour 5 → 1 SEMITONE                            → CLASH
#   hour 6 → 6 semitones  (tritone)                → CLASH
#   hour 7 → 1 SEMITONE   (== the +7 dominant)     → CLASH
#
# The critical, counter-intuitive fact: an adjacent ±1 Camelot move (8A→9A)
# is a perfect FIFTH and SAFE — the one-semitone disaster is two melodic
# tracks overlapping, which in same-letter terms is an hour-distance of 5 or
# 7. The LLM NEVER computes this; it only narrates the verdict the code
# already proved. Pure, side-effect-free, never raises — mirrors to_camelot.
# Table source: circle-of-fifths derivation cross-checked against
# [mixedinkey.com/camelot-wheel + dj.studio/blog/camelot-wheel].
# =====================================================================

# Same-letter hour-distances that produce a 1-semitone (5/7) or tritone (6)
# dissonance — the ONLY same-letter relationships that genuinely clash on a
# melodic overlap. Deliberately NARROW (conservative-by-default, HARMONIC-03).
_CLASH_HOURS = frozenset({5, 6, 7})
# Safe same-letter relationships: same key (0), adjacent perfect fifth (1),
# +2 energy move (2). Hours 3/4 are the intentional silent "neither" zone.
_SAFE_HOURS = frozenset({0, 1, 2})

# Same-letter hour-distance → pitch-class semitone distance (the verified
# table above). Only same-letter pairs sit on a single semitone ring; the
# coach narrates "N semitone(s) apart" straight off this without the LLM
# doing key math.
_HOUR_TO_SEMITONES: dict[int, int] = {0: 0, 1: 5, 2: 2, 3: 3, 4: 4, 5: 1, 6: 6}


def _parse(code: str | None) -> tuple[int, str] | None:
    """``"8A"`` → ``(8, "A")``; honest ``None`` on anything ``to_camelot``
    wouldn't emit.

    Normalizes the raw via ``to_camelot`` FIRST so musical / open-key forms
    resolve, then matches the shipped ``_CAMELOT_RE`` recognizer and splits
    into ``(number, letter)``. Never raises.
    """
    normalized = to_camelot(code)  # resolve musical / open-key / Camelot forms
    if normalized is None:
        return None
    m = _CAMELOT_RE.match(normalized)  # reuse the shipped recognizer
    if not m:
        return None
    return int(m.group(1)), normalized[-1]


def _hour_distance(n1: int, n2: int) -> int:
    """Circular distance on the 12-hour Camelot wheel, range 0..6."""
    d = abs(n1 - n2) % 12
    return min(d, 12 - d)


def semitone_distance(a: str | None, b: str | None) -> int | None:
    """Same-letter pitch-class semitone distance between two Camelot codes.

    Returns the semitone interval (0..6) via the verified hour→semitone
    table so the coach can narrate "1 semitone apart" without the LLM
    computing intervals. Cross-letter pairs (no single same-letter ring) and
    any ``None`` / garbage input return ``None``. Never raises.
    """
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return None
    (na, la), (nb, lb) = pa, pb
    if la != lb:
        return None  # cross-letter — not on a single same-letter semitone ring
    return _HOUR_TO_SEMITONES[_hour_distance(na, nb)]


def compatible(a: str | None, b: str | None) -> bool:
    """True iff ``a`` and ``b`` can ride a long melodic overlap cleanly.

    SAFE cases: same key, adjacent ±1 (perfect fifth), +2 energy move
    (same-letter hours ``_SAFE_HOURS``), relative major/minor (same number,
    swapped letter), and the exact ±1 cross-letter diagonal. Everything else
    — the clash band and the hours-3/4 drift "neither" zone — returns False.
    Honest ``None``-in → False. Pure, never raises.
    """
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return False
    (na, la), (nb, lb) = pa, pb
    if la == lb:
        return _hour_distance(na, nb) in _SAFE_HOURS
    # different letters
    if na == nb:
        return True  # relative major/minor — same notes, mood swap. SAFE.
    # only the exact ±1 cross-letter diagonal is treated SAFE (conservative);
    # wider cross-letter pairs stay in the silent "neither" zone.
    return _hour_distance(na, nb) == 1


def is_clash(a: str | None, b: str | None) -> bool:
    """True iff ``a`` and ``b`` are an UNAMBIGUOUS dissonant clash worth
    flagging.

    Deliberately NARROW (conservative-by-default, HARMONIC-03): only the
    same-letter 1-semitone / tritone band (``_CLASH_HOURS`` = hours 5/6/7)
    fires. Cross-letter pairs and any ``None`` / garbage input return False —
    we never flag what we can't prove dissonant. The LLM narrates this
    verdict; it NEVER computes it. Pure, never raises.
    """
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return False  # honest unknown — no clash claim (anti-slop)
    (na, la), (nb, lb) = pa, pb
    if la != lb:
        return False  # cross-letter: not in the unambiguous clash band
    return _hour_distance(na, nb) in _CLASH_HOURS
