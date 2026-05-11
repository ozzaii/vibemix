# SPDX-License-Identifier: Apache-2.0
"""Post-hoc slop filter — final guard between the LLM stream and the TTS path.

If any banned phrase from ``NEGATIVE_PHRASES`` matches the accumulated text,
the entire turn is replaced with the literal ``<silence/>`` token and the
matching phrase list is returned. The ``dj_cohost.llm_node`` consumer then
short-circuits TTS (no playback) and logs a ``slop_suppressed`` event with
the matches.

Strategy: suppress whole turn (CONTEXT §Filter post-processing — "cheaper,
blunter, can be relaxed in Phase 14 polish"). NOT in-place rewrite.
"""

from __future__ import annotations

from vibemix.prompts.negative_dict import NEGATIVE_REGEX

SILENCE_TOKEN = "<silence/>"


def filter_for_slop(text: str) -> tuple[str, list[str]]:
    """Check ``text`` for any banned phrase and suppress if found.

    Returns:
        ``(filtered_text, matches)`` where:
        - If any banned phrase matches → ``(<silence/>, [list_of_matched_phrases])``.
        - If no match → ``(text, [])`` (passes through unchanged).
        - If text is exactly ``<silence/>`` → ``(<silence/>, [])`` (already silenced).

    Word-boundary semantics: ``amazingly`` does NOT match ``amazing``.
    Match is case-insensitive.
    """
    if not text:
        return text, []
    # Already-silent payload — passes through (avoid double-flagging).
    if text.strip() == SILENCE_TOKEN:
        return SILENCE_TOKEN, []
    matches = NEGATIVE_REGEX.findall(text)
    if matches:
        return SILENCE_TOKEN, list(matches)
    return text, []
