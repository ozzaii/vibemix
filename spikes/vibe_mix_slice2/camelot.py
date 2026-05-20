# SPDX-License-Identifier: Apache-2.0
"""Camelot wheel — parse DJ key notations and test harmonic compatibility.

The Camelot wheel encodes key as ``<1-12><A|B>`` (A = minor, B = major).
Two tracks mix harmonically when their codes are:

  * identical                          (8A -> 8A)
  * same letter, adjacent number       (8A -> 7A or 9A; 12 wraps to 1)
  * same number, opposite letter       (8A <-> 8B, relative major/minor)

These are the three "safe" energy-neutral moves every harmonic-mixing guide
teaches. Energy-boost (+7) and other advanced moves are deliberately excluded
at this gate — strict, like the cue conservatism decision.

``parse_camelot`` accepts Camelot codes directly ("8A", "12b") and common
key-name notations ("Am", "C", "F#m", "Bbm", "Abm") incl. enharmonics, since
Rekordbox's Tonality field is not normalized. Unknown / unparseable keys
return ``None`` and are treated as *not* compatible — we never claim a mix is
in-key when we cannot prove it (the anti-slop law applied to ordering).
"""
from __future__ import annotations

import re

# Major key (letter B) -> Camelot number. Enharmonics share a slot.
_MAJOR = {
    "C": 8, "G": 9, "D": 10, "A": 11, "E": 12, "B": 1,
    "F#": 2, "GB": 2, "DB": 3, "C#": 3, "AB": 4, "G#": 4,
    "EB": 5, "D#": 5, "BB": 6, "A#": 6, "F": 7,
}
# Minor key (letter A) -> Camelot number.
_MINOR = {
    "A": 8, "E": 9, "B": 10, "F#": 11, "GB": 11, "C#": 12, "DB": 12,
    "G#": 1, "AB": 1, "D#": 2, "EB": 2, "A#": 3, "BB": 3,
    "F": 4, "C": 5, "G": 6, "D": 7,
}

_CAMELOT_RE = re.compile(r"^\s*(\d{1,2})\s*([ABab])\s*$")
_KEYNAME_RE = re.compile(r"^\s*([A-Ga-g])([#b]?)\s*(m|min|maj|major|minor)?\s*$")


def parse_camelot(key: str | None) -> str | None:
    """Normalize a key string to ``"<n><A|B>"``; return ``None`` if unknown."""
    if not key:
        return None

    m = _CAMELOT_RE.match(key)
    if m:
        num = int(m.group(1))
        letter = m.group(2).upper()
        if 1 <= num <= 12:
            return f"{num}{letter}"
        return None

    m = _KEYNAME_RE.match(key)
    if m:
        note = (m.group(1) + m.group(2)).upper()
        suffix = (m.group(3) or "").lower()
        is_minor = suffix in ("m", "min", "minor")
        table = _MINOR if is_minor else _MAJOR
        num = table.get(note)
        if num is None:
            return None
        return f"{num}{'A' if is_minor else 'B'}"

    return None


def _split(code: str) -> tuple[int, str]:
    return int(code[:-1]), code[-1]


def are_compatible(k1: str | None, k2: str | None) -> bool:
    """True iff the two keys are a safe harmonic mix (see module docstring)."""
    c1, c2 = parse_camelot(k1), parse_camelot(k2)
    if c1 is None or c2 is None:
        return False
    n1, l1 = _split(c1)
    n2, l2 = _split(c2)
    if c1 == c2:
        return True
    if l1 == l2:
        # Adjacent on the 12-hour wheel (12 wraps to 1).
        diff = abs(n1 - n2)
        return diff == 1 or diff == 11
    # Different letter -> only the relative major/minor (same number).
    return n1 == n2
