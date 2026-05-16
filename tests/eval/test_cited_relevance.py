# SPDX-License-Identifier: Apache-2.0
"""Phase 27-02 — cited-relevance pure-logic tests + cost-guard verification.

No API calls; tests for the API-backed path are deferred to a cassette-
backed integration suite (KAAN-ACTION-LEGAL.md tracks cassette generation).
"""

from __future__ import annotations

import numpy as np

from scripts.eval.cited_relevance import (
    MIN_STRIPPED_WORDS,
    cosine,
    strip_citations,
)


def test_strip_citations_removes_all_tag_types() -> None:
    """All four citation forms (ev / track / mix / emote) are stripped."""
    text = (
        "Yeah [ev:KICK_SWAP@1] the mid kicks [track:abc123] "
        "filter sweep [mix:open_high] -- emote check [emote:laugh]."
    )
    stripped = strip_citations(text)
    assert "[ev:" not in stripped
    assert "[track:" not in stripped
    assert "[mix:" not in stripped
    assert "[emote:" not in stripped
    # Surrounding prose is preserved.
    assert "the mid kicks" in stripped
    assert "filter sweep" in stripped


def test_strip_citations_idempotent_on_clean_text() -> None:
    """Text without any citation tags is returned unchanged."""
    clean = "Just a regular sentence without any citation tags at all."
    assert strip_citations(clean) == clean


def test_strip_citations_handles_empty_string() -> None:
    assert strip_citations("") == ""


def test_cosine_perfect_match_returns_one() -> None:
    v = np.array([1.0, 0.0, 0.0])
    assert cosine(v, v) == 1.0


def test_cosine_orthogonal_returns_zero() -> None:
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine(a, b) == 0.0


def test_cosine_zero_vector_guard() -> None:
    """Zero vector input returns 0.0 (no NaN, no ZeroDivisionError)."""
    a = np.zeros(768)
    b = np.ones(768)
    assert cosine(a, b) == 0.0
    assert cosine(b, a) == 0.0
    assert cosine(a, a) == 0.0


def test_cosine_typical_768_dim() -> None:
    """Two close-but-not-identical 768-dim vectors return cosine in (0, 1)."""
    rng = np.random.default_rng(seed=27)
    a = rng.normal(size=768).astype(np.float32)
    b = a + 0.1 * rng.normal(size=768).astype(np.float32)
    c = cosine(a, b)
    assert 0.5 < c < 1.0, c


def test_min_stripped_words_floor_is_eight() -> None:
    """MIN_STRIPPED_WORDS guard threshold is 8 per Pitfall P45."""
    assert MIN_STRIPPED_WORDS == 8


def test_short_response_after_strip_falls_below_threshold() -> None:
    """A response with citations + only 3 substantive words must not pass the floor.

    This is the contract relevance_score relies on to early-exit with 0.0
    BEFORE invoking the embedding API (cost guard).
    """
    short = "Yeah [ev:KICK@1] [track:abc]."
    stripped = strip_citations(short).strip()
    assert len(stripped.split()) < MIN_STRIPPED_WORDS


def test_long_response_after_strip_passes_threshold() -> None:
    """A response with substantive prose around citations passes the floor."""
    long = (
        "The mid kicks just dropped [ev:KICK_SWAP@1] and the energy "
        "in the room is climbing fast right now."
    )
    stripped = strip_citations(long).strip()
    assert len(stripped.split()) >= MIN_STRIPPED_WORDS
