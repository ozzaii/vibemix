# SPDX-License-Identifier: Apache-2.0
"""English-only runtime guard tests."""

from __future__ import annotations

from vibemix.agent.language_guard import (
    english_only_violation_matches,
    violates_english_only,
)


def test_allows_english_with_grounding_citation() -> None:
    text = "That low end is moving clearly [aud:rms@12.0]."

    assert english_only_violation_matches(text) == ()
    assert not violates_english_only(text)


def test_blocks_obvious_turkish_dj_chat() -> None:
    matches = english_only_violation_matches("Süper drop abi, çok iyi.")

    assert "phrase:çok iyi" in matches
    assert "turkish_chars:süper" in matches
    assert violates_english_only("Süper drop abi, çok iyi.")


def test_blocks_ascii_turkish_opener_phrase() -> None:
    matches = english_only_violation_matches("Evet, cok iyi, devam.")

    assert "opener:evet" in matches
    assert "phrase:cok iyi" in matches
    assert any(match.startswith("tokens:") for match in matches)


def test_allows_turkish_character_artist_name_in_english_sentence() -> None:
    text = "That Barış Manço synth color sits nicely over the break."

    assert english_only_violation_matches(text) == ()


def test_single_ambiguous_ascii_word_does_not_suppress() -> None:
    assert english_only_violation_matches("That is a super tight groove.") == ()
