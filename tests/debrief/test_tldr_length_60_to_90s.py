# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-04: TLDR narration text is bounded to 150-220 words (≈60-90s @ Achird WPM).

Real Gemini calls are out of scope for offline tests — we verify the
deterministic word-budget enforcement and the stripper integration via
mocks. The cross-platform Achird voice MP3 duration smoke is verified in
the manual smoke checklist (Plan 29-08).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief.tldr import (
    DebriefGenerationError,
    _truncate_to_word_budget,
    generate_tldr_text,
)


def _gemini_text_response(text: str):
    return SimpleNamespace(text=text)


def test_word_budget_truncation_at_220():
    """Long output truncated at sentence boundary within 220 words."""
    # Build 250 words, sentence-separated.
    sentences = [
        f"This is sentence number {i} with citation [ev:M@1]." for i in range(50)
    ]  # ~5 wpm × 50 = 250 words
    text = " ".join(sentences)
    truncated = _truncate_to_word_budget(text, max_words=220)
    assert len(truncated.split()) <= 220
    # Must end on sentence boundary.
    assert truncated.rstrip().endswith(".")


def test_word_budget_short_input_returned_verbatim():
    text = "Short sentence [ev:M@1]. Another [track:t1]."
    out = _truncate_to_word_budget(text, max_words=220)
    assert out == text


def test_generate_tldr_text_strips_uncited_sentences():
    """The Gemini-returned text is filtered by the stripper."""
    response_text = (
        "First sentence [ev:M@1]. "
        "Uncited gibberish in the middle. "
        "Final cited [track:t1]."
    )
    client = MagicMock()
    client.models.generate_content.return_value = _gemini_text_response(response_text)
    out = generate_tldr_text(client, ["chapter1"], "cited critique")
    assert "[ev:M@1]" in out
    assert "[track:t1]" in out
    assert "Uncited gibberish" not in out


def test_generate_tldr_text_raises_when_all_stripped():
    """All-uncited Gemini output → DebriefGenerationError."""
    client = MagicMock()
    client.models.generate_content.return_value = _gemini_text_response(
        "Random one. Random two. Random three."
    )
    with pytest.raises(DebriefGenerationError) as ei:
        generate_tldr_text(client, ["c"], "cited")
    assert ei.value.reason == "tldr_generation_failed"


def test_generate_tldr_text_raises_on_empty_response():
    client = MagicMock()
    client.models.generate_content.return_value = _gemini_text_response("")
    with pytest.raises(DebriefGenerationError):
        generate_tldr_text(client, ["c"], "cited")


def test_generate_tldr_text_raises_on_gemini_exception():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("network down")
    with pytest.raises(DebriefGenerationError) as ei:
        generate_tldr_text(client, ["c"], "cited")
    assert ei.value.reason == "tldr_generation_failed"
    assert "network down" in ei.value.message


def test_generate_tldr_text_truncates_long_narration():
    """When Gemini returns > 220 words, output is truncated."""
    long_sentences = " ".join(
        f"Cited sentence number {i} [ev:M@1]." for i in range(60)
    )
    client = MagicMock()
    client.models.generate_content.return_value = _gemini_text_response(long_sentences)
    out = generate_tldr_text(client, ["c"], "cited")
    assert len(out.split()) <= 220
