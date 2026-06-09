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


@pytest.mark.parametrize(
    "phrase",
    [
        "here's the thing",
        "let me be clear",
        "at the end of the day",
        "fundamentally",
        "circle back",
        "the stakes are high",
    ],
)
def test_filter_09_stop_slop_additions_trigger_suppression(phrase: str) -> None:
    """Stop-slop bucket (hardikpandya/stop-slop, MIT) phrases also suppress."""
    text, matches = filter_for_slop(f"Yo, {phrase}, that drop hit")
    assert text == "<silence/>"
    assert len(matches) >= 1


@pytest.mark.parametrize(
    "clean_text",
    [
        "really feeling that kick",
        "just let it breathe",
        "actually try the low-pass",
        "honestly that breakdown's clean",
        "literally chef's kiss",
        "simply hold the loop",
    ],
)
def test_filter_10_natural_adverbs_do_not_false_positive(clean_text: str) -> None:
    """Natural DJ-friend speech with common adverbs must NOT trigger whole-turn
    suppression — the curation rule for stop-slop additions is "multi-word or
    professorial-only" so single-word adverbs like 'really'/'just'/'actually'
    stay author-side, not runtime."""
    text, matches = filter_for_slop(clean_text)
    assert text == clean_text, f"false positive on natural speech: matches={matches}"
    assert matches == []


# ---------------------------------------------------------------------------
# Assistant-voice / AI self-disclosure coverage (default-slop-sweep finding)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "I am here to help you read this set",  # expanded form of banned "I'm here to help"
        "I do not have a clear read on that kick yet",  # expanded "I don't have"
    ],
)
def test_filter_11_expanded_contraction_forms_caught(text: str) -> None:
    """A banned phrase stored as a contraction ("I'm here to help") must ALSO
    suppress its expanded surface form ("I am here to help"). The regex was
    contraction-blind (literal re.escape), so the model could defeat the
    backstop with a one-token expansion. ONE generalizing normalization closes
    this for every existing phrase."""
    out, matches = filter_for_slop(text)
    assert out == "<silence/>", f"expanded assistant-voice slipped: {text!r}"
    assert len(matches) >= 1


@pytest.mark.parametrize(
    "text",
    [
        "I'm an AI but that kick hits",
        "I am an AI, here's what I hear",
        "as a language model I can tell the lows are stacking",
    ],
)
def test_filter_12_ai_self_disclosure_family_caught(text: str) -> None:
    """AI self-disclosure variants must suppress — "as an AI" was banned but the
    close siblings ("I'm an AI", "I am an AI", "as a language model") slipped.
    Catastrophic immersion-break if ever voiced; never natural DJ-friend speech."""
    out, matches = filter_for_slop(text)
    assert out == "<silence/>", f"AI self-disclosure slipped: {text!r}"
    assert len(matches) >= 1


@pytest.mark.parametrize(
    "clean",
    [
        "I can't get enough of this groove",  # can't->cannot, not banned
        "that drop just hit, I'm loving the bassline",  # I'm->I am, "I am loving" not banned
        "it's not letting up, the energy is wild",  # it's->it is, not banned
    ],
)
def test_filter_13_contraction_normalization_no_false_positive(clean: str) -> None:
    """The contraction normalization must NOT false-positive on natural speech
    whose expanded form is not banned — and the ORIGINAL text (not the
    normalized form) passes through unchanged."""
    out, matches = filter_for_slop(clean)
    assert out == clean, f"false positive on natural speech: matches={matches}"
    assert matches == []
