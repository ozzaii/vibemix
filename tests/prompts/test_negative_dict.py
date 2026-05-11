# SPDX-License-Identifier: Apache-2.0
"""PROMPT-02: Negative dictionary — ~40 banned phrases across 3 buckets.

Buckets per CONTEXT §Negative dictionary:
- Generic AI tells: "as an AI", "delve", "leverage", "synergy", etc.
- Empty hype: "amazing", "awesome", "incredible", "great mix", etc.
- Slop framings: "in this dynamic world", "at the intersection of", etc.
"""

from __future__ import annotations

import re

from vibemix.prompts.negative_dict import NEGATIVE_PHRASES, NEGATIVE_REGEX


def test_negative_dict_01_at_least_forty_phrases() -> None:
    """≥40 banned phrases — covers the three buckets (CONTEXT §Negative dictionary)."""
    assert len(NEGATIVE_PHRASES) >= 40, (
        f"NEGATIVE_PHRASES has only {len(NEGATIVE_PHRASES)} entries — need ≥40"
    )


def test_negative_dict_02_is_tuple() -> None:
    """Tuple (immutable) — runtime guarantee against mutation."""
    assert isinstance(NEGATIVE_PHRASES, tuple)


def test_negative_dict_03_no_duplicates() -> None:
    """No duplicate phrases (case-insensitive)."""
    lowered = [p.lower() for p in NEGATIVE_PHRASES]
    assert len(lowered) == len(set(lowered)), "NEGATIVE_PHRASES contains duplicates"


def test_negative_dict_04_covers_generic_ai_tells() -> None:
    """Generic AI tells bucket — at least 5 representative phrases present."""
    expected = ["as an AI", "delve", "leverage", "synergy", "robust"]
    lowered = [p.lower() for p in NEGATIVE_PHRASES]
    for needle in expected:
        assert needle.lower() in lowered, f"missing AI-tell phrase: {needle!r}"


def test_negative_dict_05_covers_empty_hype() -> None:
    """Empty hype bucket — at least 5 representative phrases present."""
    expected = ["amazing", "awesome", "incredible", "fantastic", "wonderful"]
    lowered = [p.lower() for p in NEGATIVE_PHRASES]
    for needle in expected:
        assert needle.lower() in lowered, f"missing empty-hype phrase: {needle!r}"


def test_negative_dict_06_covers_slop_framings() -> None:
    """Slop framings bucket — at least 3 multi-word slop phrases present."""
    expected = [
        "in this dynamic world",
        "at the intersection of",
        "navigate the landscape",
    ]
    lowered = [p.lower() for p in NEGATIVE_PHRASES]
    for needle in expected:
        assert needle.lower() in lowered, f"missing slop framing: {needle!r}"


def test_negative_dict_07_regex_compiled_case_insensitive() -> None:
    """NEGATIVE_REGEX is a compiled regex with IGNORECASE flag."""
    assert isinstance(NEGATIVE_REGEX, re.Pattern)
    assert NEGATIVE_REGEX.flags & re.IGNORECASE


def test_negative_dict_08_regex_matches_each_phrase_case_insensitive() -> None:
    """Every phrase in NEGATIVE_PHRASES is matched by NEGATIVE_REGEX (case-insensitive)."""
    for phrase in NEGATIVE_PHRASES:
        # Embed in a sentence so word-boundary checks don't trip on bare phrase
        sentence = f"yo {phrase} man"
        assert NEGATIVE_REGEX.search(sentence), f"NEGATIVE_REGEX missed: {phrase!r}"
        # Case insensitivity — uppercased should also match
        assert NEGATIVE_REGEX.search(sentence.upper()), f"NEGATIVE_REGEX missed UPPER: {phrase!r}"


def test_negative_dict_09_regex_passes_clean_text() -> None:
    """NEGATIVE_REGEX returns no match on clean DJ-friend text."""
    clean = "that 303 squelch hit hard 4 bars in"
    assert NEGATIVE_REGEX.search(clean) is None
