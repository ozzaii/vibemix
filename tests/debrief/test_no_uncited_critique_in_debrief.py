# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-07 hard gate (unit-level) — stripper drops uncited sentences.

End-to-end variant in tests/debrief/test_no_uncited_critique_in_debrief_e2e.py
arrives with Plan 29-07; this file covers the building-block behavior.
"""

from __future__ import annotations

import pytest

from vibemix.debrief import (
    UncitedSentencesFound,
    assert_all_cited,
    strip_uncited_sentences,
)


def test_strip_keeps_cited_sentence():
    text = "Drop at [ev:DROP_HIT@01:23] worked. Random filler."
    out, dropped = strip_uncited_sentences(text)
    assert out == "Drop at [ev:DROP_HIT@01:23] worked."
    assert dropped == 1


def test_strip_drops_all_uncited():
    text = "First sentence. Second sentence. Third one."
    out, dropped = strip_uncited_sentences(text)
    assert out == ""
    assert dropped == 3


def test_strip_empty_input():
    assert strip_uncited_sentences("") == ("", 0)
    assert strip_uncited_sentences("   \n  ") == ("", 0)


@pytest.mark.parametrize(
    "source",
    ["ev", "track", "mix", "aud", "midi", "screen", "tend"],
)
def test_strip_accepts_all_7_ebnf_sources(source: str):
    text = f"This works [{source}:something@1.0]."
    out, dropped = strip_uncited_sentences(text)
    assert out == text  # sentence preserved
    assert dropped == 0


def test_strip_logs_dropped_sentence(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="vibemix.debrief.stripper")
    text = "Cited [ev:A@1]. Uncited line."
    strip_uncited_sentences(text)
    assert any("stripped uncited" in r.message for r in caplog.records)


def test_assert_all_cited_raises_on_uncited():
    text = "Cited [ev:A@1]. Uncited."
    with pytest.raises(UncitedSentencesFound) as ei:
        assert_all_cited(text)
    assert ei.value.reason == "uncited_sentences"


def test_assert_all_cited_passes_when_all_cited():
    text = "First [ev:A@1]. Second [track:t1]."
    assert_all_cited(text)  # does not raise


def test_no_uncited_critique_in_synthetic_debrief():
    """Hard gate at the building-block level. The synthetic debrief
    output below contains a mix of cited / uncited sentences; after
    stripper passes, there must be ZERO uncited sentences left.
    """
    synthetic_drill_text = (
        "DJ played mid-EQ boost too long [ev:MIX_MOVE@01:23]. "
        "Random filler statement without backing. "
        "The crowd lost momentum [ev:HEARTBEAT@01:45]. "
        "More random unsupported claim."
    )
    cleaned, dropped = strip_uncited_sentences(synthetic_drill_text)
    assert dropped == 2
    # After stripping, every remaining sentence must contain a citation.
    assert_all_cited(cleaned)  # MUST NOT raise — this IS the gate
