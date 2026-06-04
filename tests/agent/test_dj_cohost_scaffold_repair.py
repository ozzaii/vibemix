# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.agent.dj_cohost import (
    _could_be_finished_line_meta_scaffold,
    _grounded_receipt_fallback_line,
    _has_unclosed_bracket_tail,
    repair_finished_headphone_line,
)


def test_final_polish_fragment_after_citation_tail_is_suppressed() -> None:
    raw = "108.0]\n\n4.  **Final Polish (Sven's voice):"

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) is None


def test_dangling_bracket_voice_fragment_is_suppressed() -> None:
    raw = '] to the next phrase, then bring the highs in to lift it." (15 words'

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) is None


def test_colon_star_truncated_quote_fragment_is_suppressed() -> None:
    raw = ':* "This sub is heavy--hold this groove until the phrase breaks at 10'

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) is None


def test_final_polish_wrapper_keeps_quoted_headphone_line() -> None:
    raw = '108.0]\n\n4. **Final Polish (Sven\'s voice): "Hold this until the phrase."'

    assert repair_finished_headphone_line(raw) == "Hold this until the phrase."


def test_orphan_citation_tail_before_clean_line_is_removed() -> None:
    raw = "108.0] Hold this transition until the next phrase."

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) == "Hold this transition until the next phrase."


def test_grounded_cue_receipt_fallback_line_is_citable_and_spoken() -> None:
    fallback = _grounded_receipt_fallback_line(
        {
            "next_suggestion_voice_line": (
                "Forward cue receipt: the next citable phrase boundary is about 4 bars ahead. "
                "Use it as one forward timing nudge for what comes next if the live sound "
                "supports it. Copy this citation exactly: [cue:phrase_boundary@108.0]."
            )
        }
    )

    assert fallback == (
        "Hold this for about 4 bars; make the move on the next phrase. "
        "[cue:phrase_boundary@108.0]"
    )


def test_grounded_cue_receipt_fallback_abstains_without_cue_atom() -> None:
    assert (
        _grounded_receipt_fallback_line(
            {
                "next_suggestion_voice_line": (
                    "Forward read: a darker rolling 9A track pairs next - keeps the build."
                )
            }
        )
        is None
    )


def test_unclosed_citation_tail_is_detected_for_fallback() -> None:
    assert _has_unclosed_bracket_tail(
        "Hold this until the next phrase [cue:phrase_boundary@10"
    )
    assert not _has_unclosed_bracket_tail(
        "Hold this until the next phrase. [cue:phrase_boundary@108.0]"
    )
