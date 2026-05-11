# SPDX-License-Identifier: Apache-2.0
"""PROMPT-02 (post-hoc filter): filter_for_slop suppresses banned LLM output.

Strategy: replace whole turn with `<silence/>` (per CONTEXT — suppress whole
turn is the v1 approach; relax to in-place rewrite in Phase 14 polish).
"""

from __future__ import annotations

import pytest

from vibemix.prompts.filter import filter_for_slop


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------


def test_filter_01_suppresses_banned_phrase_returns_silence_token() -> None:
    """Output containing a banned phrase → ('<silence/>', [matches])."""
    text, matches = filter_for_slop("Amazing mix!")
    assert text == "<silence/>"
    assert "amazing" in [m.lower() for m in matches]


def test_filter_02_clean_text_passes_through_unchanged() -> None:
    """Clean DJ-friend text → (text_unchanged, [])."""
    clean = "that 303 squelch hit hard 4 bars in"
    text, matches = filter_for_slop(clean)
    assert text == clean
    assert matches == []


def test_filter_03_case_insensitive() -> None:
    """Banned-phrase match is case-insensitive."""
    text, matches = filter_for_slop("AMAZING work right there")
    assert text == "<silence/>"
    assert len(matches) >= 1


def test_filter_04_word_boundary_does_not_match_partial() -> None:
    """'amazingly' should NOT match the banned phrase 'amazing' (word boundary)."""
    # 'amazingly' contains 'amazing' as a prefix — but with a word boundary
    # regex the banned 'amazing' shouldn't match 'amazingly'.
    text, matches = filter_for_slop("that drop landed amazingly fast")
    # The literal phrase 'amazing' is bounded; 'amazingly' breaks the right boundary.
    assert text == "that drop landed amazingly fast", f"false positive: matches={matches}"
    assert matches == []


def test_filter_05_multiple_matches_collected() -> None:
    """Multiple banned phrases in one text — all collected in matches list."""
    text, matches = filter_for_slop("Amazing! Awesome! Incredible!")
    assert text == "<silence/>"
    lowered = [m.lower() for m in matches]
    # At least 2 of the 3 hype words match (regex find-all).
    hits = sum(1 for w in ("amazing", "awesome", "incredible") if w in lowered)
    assert hits >= 2


def test_filter_06_empty_input_passes_through() -> None:
    """Empty string → ('', [])."""
    text, matches = filter_for_slop("")
    assert text == ""
    assert matches == []


def test_filter_07_silence_token_passes_through() -> None:
    """If LLM already emitted <silence/>, filter passes it through (no false-positive)."""
    text, matches = filter_for_slop("<silence/>")
    assert text == "<silence/>"
    assert matches == []


@pytest.mark.parametrize(
    "phrase",
    [
        "delve",
        "leverage",
        "synergy",
        "as an AI",
        "in this dynamic world",
        "navigate the landscape",
    ],
)
def test_filter_08_each_bucket_phrase_triggers_suppression(phrase: str) -> None:
    """Each representative phrase from each bucket triggers suppression."""
    text, matches = filter_for_slop(f"Yo, {phrase}, that drop hit")
    assert text == "<silence/>"
    assert len(matches) >= 1
