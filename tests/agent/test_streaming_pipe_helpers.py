# SPDX-License-Identifier: Apache-2.0
"""Plan 41-04 Task 1 — _streaming_pipe helpers unit tests (LAT-04).

Pins:
  * find_sentence_end is bracket-depth-aware (Pitfall 1 — citation periods
    at depth > 0 don't trigger boundaries).
  * find_sentence_end requires trailing whitespace (defer-to-next-chunk on
    end-of-buffer punctuation — avoids premature yield when the period is
    actually inside a number / abbreviation / next-chunk-arrives token).
  * MIN_HEAD_LEN (=20) skips short heads — A4 mitigation against "vb." /
    "Dr." / "2.5K" emitted as a turn opener.
  * passes_head_gate rejects silence-token + slop prefixes synchronously.

The full slop filter (NEGATIVE_REGEX) runs post-stream on the trailing
text — the head gate is a fast PREFIX check ONLY. See module docstring of
_streaming_pipe for the subset-choice rationale.
"""

from __future__ import annotations

import pytest

from vibemix.agent._streaming_pipe import (
    MIN_HEAD_LEN,
    SENTENCE_BOUNDARY_CHARS,
    SILENCE_TOKEN,
    find_sentence_end,
    passes_head_gate,
)


# ---------- find_sentence_end ----------


def test_no_boundary_returns_none() -> None:
    """Bare clause with no terminal punctuation → None."""
    assert find_sentence_end("Killer drop incoming") is None


def test_period_with_whitespace_returns_index() -> None:
    """Period+space at depth 0 past MIN_HEAD_LEN → index after the period+space."""
    text = "Track sounds great. The next one..."
    idx = find_sentence_end(text)
    assert idx is not None
    # idx must point past 'great.' so accum[:idx] yields the head sentence.
    assert text[:idx] == "Track sounds great. "
    # Tail starts at "The next one..."
    assert text[idx:].startswith("The next one")


def test_period_inside_citation_no_match() -> None:
    """Period inside a [ev:...] citation → depth > 0, ignored (Pitfall 1)."""
    # Period inside [ev:kick@2.5] — bracket-depth = 1 — must NOT trigger.
    # The trailing "hit hard" has no terminal punctuation either.
    assert find_sentence_end("Killer drop [ev:kick@2.5] hit hard") is None


def test_multiple_citations_period_after() -> None:
    """Citations followed by a real boundary period → match after the bracket closes."""
    text = "Hits [ev:foo@1.2] [track:bar]. Next."
    idx = find_sentence_end(text)
    assert idx is not None
    # Head must include the closing bracket and the period+space.
    head = text[:idx]
    assert head.endswith("]. ") or head.endswith("].")
    assert "[ev:foo@1.2]" in head
    assert "[track:bar]" in head


def test_min_head_len_skips_short() -> None:
    """Short heads (< MIN_HEAD_LEN) skipped — A4 Turkish abbreviation mitigation."""
    # "Yo." = 3 chars, "Yeah." = 5 chars — both below MIN_HEAD_LEN=20.
    assert find_sentence_end("Yo. Yeah.") is None


def test_min_head_len_fires_at_threshold() -> None:
    """Period at or past MIN_HEAD_LEN → boundary fires."""
    text = "This is a longer head sentence. Tail."
    idx = find_sentence_end(text)
    assert idx is not None
    # Head length must be >= MIN_HEAD_LEN.
    assert idx >= MIN_HEAD_LEN
    assert "longer head sentence" in text[:idx]


def test_ellipsis_unicode_triggers() -> None:
    """Single-codepoint ellipsis (…) at depth 0 → boundary."""
    text = "Building up the energy now…  Boom."
    idx = find_sentence_end(text)
    assert idx is not None
    assert "energy now" in text[:idx]


def test_no_trailing_whitespace_defers() -> None:
    """Period at end-of-buffer with NO trailing whitespace → defer to next chunk."""
    # The period is here, but no whitespace follows. We defer — next chunk
    # may show " " (boundary) OR "5K" (number — no boundary).
    assert find_sentence_end("Track sounds great.") is None


def test_question_mark_triggers() -> None:
    """'?' is in SENTENCE_BOUNDARY_CHARS."""
    text = "Are you feeling this groove yet? Yeah."
    idx = find_sentence_end(text)
    assert idx is not None
    assert text[:idx].rstrip().endswith("?")


def test_exclamation_triggers() -> None:
    """'!' is in SENTENCE_BOUNDARY_CHARS."""
    text = "That drop was massive! Next track up."
    idx = find_sentence_end(text)
    assert idx is not None
    assert text[:idx].rstrip().endswith("!")


def test_sentence_boundary_chars_constant() -> None:
    """SENTENCE_BOUNDARY_CHARS export covers the documented punctuation set."""
    for ch in ".!?…":
        assert ch in SENTENCE_BOUNDARY_CHARS


# ---------- passes_head_gate ----------


def test_silence_token_prefix_rejected() -> None:
    """Bare silence-token prefix → reject (no audible output)."""
    assert passes_head_gate(f"{SILENCE_TOKEN}blah") is False


def test_silence_token_whitespace_prefix_rejected() -> None:
    """Leading whitespace before silence-token is still a reject."""
    assert passes_head_gate(f"  {SILENCE_TOKEN}blah") is False


def test_clean_text_passes() -> None:
    """Plain clean text → pass."""
    assert passes_head_gate("Killer drop. ") is True


def test_slop_prefix_rejected() -> None:
    """Slop banned prefix (any case) → reject."""
    # 'as an AI' is in NEGATIVE_PHRASES; head gate also rejects it.
    assert passes_head_gate("As an AI model, I think the drop is...") is False


def test_empty_string_passes() -> None:
    """Empty head string is benign — no slop matches, no silence token.

    (Caller-side find_sentence_end never yields an empty head; this test
    pins the contract for callers that build heads from other sources.)
    """
    assert passes_head_gate("") is True
