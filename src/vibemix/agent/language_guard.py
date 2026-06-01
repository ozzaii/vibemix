# SPDX-License-Identifier: Apache-2.0
"""Runtime language guard for user-facing co-host speech.

The live prompt asks for English, but prompt text is not a safety boundary.
This module is intentionally conservative: it catches obvious Turkish prose
that should never reach MOSS/TTS, while allowing track and artist names with
Turkish characters to pass when the surrounding sentence is English.
"""

from __future__ import annotations

import re
from typing import Final

_CITATION_RE: Final[re.Pattern[str]] = re.compile(
    r"\[(?:aud|ev|midi|track|screen|mix|key|recall|exemplar|cue|judge):[^\]]+\]"
)
_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+(?:'[A-Za-zÇĞİÖŞÜçğıöşü]+)?")
_TURKISH_CHARS: Final[frozenset[str]] = frozenset("çğıöşüÇĞİÖŞÜ")
_TURKISH_OPENERS: Final[frozenset[str]] = frozenset(
    {
        "abi",
        "bak",
        "dostum",
        "evet",
        "hadi",
        "kanka",
        "knk",
        "lan",
        "simdi",
        "şimdi",
    }
)
_TURKISH_PROSE_TOKENS: Final[frozenset[str]] = _TURKISH_OPENERS | frozenset(
    {
        "akiyor",
        "akıyor",
        "ama",
        "bence",
        "bir",
        "biraz",
        "cok",
        "çok",
        "devam",
        "guzel",
        "güzel",
        "harika",
        "iyi",
        "muthis",
        "müthiş",
        "mukemmel",
        "mükemmel",
        "oldu",
        "sahane",
        "şahane",
        "super",
        "süper",
        "tam",
        "tamam",
    }
)
_TURKISH_PHRASES: Final[tuple[tuple[str, ...], ...]] = (
    ("cok", "iyi"),
    ("çok", "iyi"),
    ("tam", "oldu"),
)


def _normalized_words(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _WORD_RE.finditer(text)]


def english_only_violation_matches(text: str) -> tuple[str, ...]:
    """Return the matched non-English signals that should suppress speech.

    The guard is built for the current product contract ("Sven speaks English").
    It is not a general-purpose language detector; it catches obvious Turkish
    DJ-chat leakage without muting English sentences that mention Turkish names.
    """
    stripped = _CITATION_RE.sub(" ", text or "")
    words = _normalized_words(stripped)
    if not words:
        return ()

    matches: list[str] = []
    first = words[0]
    if first in _TURKISH_OPENERS:
        matches.append(f"opener:{first}")

    for phrase in _TURKISH_PHRASES:
        phrase_len = len(phrase)
        if any(tuple(words[i : i + phrase_len]) == phrase for i in range(len(words))):
            matches.append("phrase:" + " ".join(phrase))

    prose_tokens = [word for word in words if word in _TURKISH_PROSE_TOKENS]
    if len(prose_tokens) >= 2:
        matches.append("tokens:" + ",".join(prose_tokens[:4]))

    has_turkish_char = any(ch in _TURKISH_CHARS for ch in stripped)
    if has_turkish_char and prose_tokens:
        matches.append("turkish_chars:" + prose_tokens[0])

    return tuple(dict.fromkeys(matches))


def violates_english_only(text: str) -> bool:
    """Return True when ``text`` should not be spoken in an English-only session."""
    return bool(english_only_violation_matches(text))
