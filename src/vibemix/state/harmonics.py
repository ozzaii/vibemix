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

Scope: Phase 59 ships ``to_camelot`` ONLY. Phase 60 will consume ``is_clash`` /
``compatible`` (the deterministic Camelot-wheel clash table the LLM merely
narrates) ON TOP of this normalizer — those functions are NOT defined here yet.

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
