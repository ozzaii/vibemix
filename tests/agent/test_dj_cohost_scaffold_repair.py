# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.agent.dj_cohost import (
    _could_be_finished_line_meta_scaffold,
    _grounded_receipt_fallback_line,
    _grounded_voice_payload_fallback_line,
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


def test_plain_headphone_line_drops_edge_quote_without_rewriting() -> None:
    raw = '"That cut killed the high-end energy fast; next time, drag the sweep out'

    assert repair_finished_headphone_line(raw) == (
        "That cut killed the high-end energy fast; next time, drag the sweep out"
    )


def test_broken_citation_tail_fragment_is_suppressed() -> None:
    raw = ".1]` (wait, `880.1` is in the grounding refs)."

    assert repair_finished_headphone_line(raw) is None


def test_broken_citation_id_tail_fragment_is_suppressed() -> None:
    raw = "cut_big_twist@612.4] -> wait, the grounding ref is `"

    assert repair_finished_headphone_line(raw) is None


def test_compact_midi_ref_fragment_is_suppressed() -> None:
    raw = "A_filter:_flat_to_cut_big_twist@612"

    assert repair_finished_headphone_line(raw) is None


def test_unclosed_citation_prefix_fragment_is_suppressed() -> None:
    raw = "[midi:A_low:_flat_to_kill_big_twist@"

    assert repair_finished_headphone_line(raw) is None


def test_ground_citation_meta_fragment_is_suppressed() -> None:
    raw = "ground citation:* `[midi:A_low:_flat_to_kill_big_"

    assert repair_finished_headphone_line(raw) is None


def test_grounding_ref_meta_fragment_is_suppressed() -> None:
    raw = "Wait, the exact grounding ref is `"

    assert repair_finished_headphone_line(raw) is None


def test_citation_reasoning_meta_fragment_is_suppressed() -> None:
    raw = "-> Wait, do I have a specific timestamp? No, so omit the citation or keep"

    assert repair_finished_headphone_line(raw) is None


def test_dj_terminology_meta_fragment_is_suppressed() -> None:
    raw = "or similar. * DJ terminology? Yes.Let this sub"

    assert repair_finished_headphone_line(raw) is None


def test_dj_to_dj_meta_fragment_is_suppressed() -> None:
    raw = "-> let's make it punchy, DJ-to-DJ."

    assert repair_finished_headphone_line(raw) is None


def test_meta_tail_after_citation_strip_is_suppressed() -> None:
    raw = "boundary. * *Check"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_headphone_tail_is_suppressed() -> None:
    raw = "That filter cut took a massive bite out of"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_article_tail_is_suppressed() -> None:
    raw = "That sub is riding heavy right now--let it roll before you start pulling the"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_numeric_tail_is_suppressed() -> None:
    raw = "Let the sub ride, then pull back before you bring in that 1"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_bare_that_tail_is_suppressed_after_text_prefix() -> None:
    raw = "text\nLet this sub roll before you start pulling the tempo down for that"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_new_tail_is_suppressed() -> None:
    raw = "That cut hollowed out the top; next time, use that space to drop the new"

    assert repair_finished_headphone_line(raw) is None


def test_incomplete_band_action_tail_is_suppressed() -> None:
    raw = "Keep this sub heavy until the phrase hits at 108, then let the highs"

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) is None


def test_text_prefix_keeps_complete_headphone_line() -> None:
    raw = "text\nLet this sub roll before you start pulling the tempo down."

    assert repair_finished_headphone_line(raw) == (
        "Let this sub roll before you start pulling the tempo down."
    )


def test_refine_option_meta_fragment_is_suppressed() -> None:
    raw = "4. **Refine Option A (incorporating the big twist context and keeping"

    assert repair_finished_headphone_line(raw) is None


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


def test_grounded_voice_payload_fallback_uses_next_suggestion_receipt() -> None:
    fallback = _grounded_voice_payload_fallback_line(
        {
            "next_suggestion_voice_line": (
                "Forward read: Ananta by Crew pairs next - keeps the build. "
                "Hand it as one nudge if it fits the live sound. "
                "Copy these citations exactly: [track:track-42] [mix:next_suggestion=track-42]."
            )
        }
    )

    assert fallback == (
        "Line up Ananta by Crew next to keep this build moving. "
        "[track:track-42] [mix:next_suggestion=track-42]"
    )


def test_grounded_voice_payload_fallback_prefers_cue_receipt() -> None:
    fallback = _grounded_voice_payload_fallback_line(
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
