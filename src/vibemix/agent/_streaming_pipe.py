# SPDX-License-Identifier: Apache-2.0
"""Plan 41-04 LAT-04 — sentence-boundary detector + head-gate primitives.

Two private helpers feeding ``DJCoHostAgent.llm_node``'s streaming
pipe-through refactor:

  * :func:`find_sentence_end` — bracket-depth-aware sentence-boundary
    scanner. Periods (or other terminal punctuation) at bracket depth > 0
    do NOT trigger boundaries — citations like ``[ev:kick@2.5]`` carry a
    literal ``.`` that the legacy regex ``[.!?]\\s`` would mis-fire on
    (Pitfall 1 — locked in 41-04-PLAN ``<refactor_blueprint>``).

  * :func:`passes_head_gate` — quick prefix check before yielding the head
    to TTS. Two rejections:
      - Silence-token prefix (the LLM emitted ``<silence/>`` as the head
        — the whole turn must be suppressed; the matching gate also runs
        post-stream on the full text).
      - A subset of the slop-PREFIX list (banned phrases that can ONLY
        appear as openers — e.g. "as an AI", "in this dynamic world").

The head gate is intentionally NARROWER than the full :mod:`vibemix.prompts.filter`
post-hoc filter. The full filter runs on the trailing text after the stream
completes — it catches slop that appears mid-/end-response. The head gate
is a fast PREFIX check; it MUST be cheap (called inside the per-chunk
accumulator loop). When in doubt about a phrase that could legitimately
appear mid-sentence (e.g. "amazing" — the post-hoc filter rejects, but a
head opening with "Amazing groove" is borderline), defer to the post-hoc
filter and let the trailing-slop cancel-with-silence-pad handle it.

Subset choice (locked):
  All 16 "Generic AI tells" + all 8 "Slop framings" — these are framings a
  real DJ friend NEVER opens with, so a prefix match is high-confidence
  slop. The 16 "Empty hype" phrases are NOT in the head subset — "amazing"
  / "killer" / "love it" can legitimately open a real reaction; the
  post-hoc full filter still catches them on the trailing text.
"""

from __future__ import annotations

from vibemix.prompts.negative_dict import NEGATIVE_PHRASES

# ---- Public constants ----

SENTENCE_BOUNDARY_CHARS: str = ".!?…"
"""Terminal punctuation that ends a sentence at bracket depth 0.

Includes single-codepoint U+2026 (``…``) AND ASCII triplet handling — a
period inside ``...`` triggers via the per-character scan; the trailing
whitespace-required guard prevents premature mid-ellipsis fires.
"""

MIN_HEAD_LEN: int = 20
"""Minimum head length before a boundary fires.

A4 mitigation: ``"Yo."`` / ``"Yeah."`` / ``"vb."`` / ``"Dr."`` / ``"2.5K"``
are common turn-openers + Turkish/abbreviation hits that would yield a
near-empty head if we fired immediately. 20 chars is a heuristic floor —
roughly "a short phrase with at least one noun + verb".
"""

SILENCE_TOKEN: str = "<silence/>"
"""Sentinel emitted by the LLM when no reaction is warranted.

Mirrors :data:`vibemix.agent.dj_cohost.SILENCE_TOKEN` and
:data:`vibemix.prompts.filter.SILENCE_TOKEN` — kept as a local constant so
this module is self-contained (no circular import on dj_cohost).
"""


# ---- Head-gate slop subset (locked — see module docstring) ----

# Lowercased prefixes. Match is case-insensitive via str.lower() comparison
# on the stripped head. The subset is deliberately SHORTER than the full
# NEGATIVE_PHRASES tuple — see module docstring.
_HEAD_SLOP_PREFIXES: tuple[str, ...] = tuple(
    p.lower()
    for p in NEGATIVE_PHRASES
    # First 16 phrases = "Generic AI tells"; last 8 = "Slop framings".
    # Indices 16..31 = "Empty hype" (skipped — see module docstring).
    if NEGATIVE_PHRASES.index(p) < 16 or NEGATIVE_PHRASES.index(p) >= 32
)


def find_sentence_end(text: str, start: int = 0) -> int | None:
    """Return the index AFTER the first sentence-end at bracket depth 0.

    Args:
        text: Accumulated text from the LLM stream.
        start: Scan offset (so callers can resume past a previously found
            boundary without re-scanning the prefix).

    Returns:
        The index ``i`` such that ``text[:i]`` is the head sentence
        (terminal punctuation + trailing whitespace included), or ``None``
        when no boundary is found.

        Returns ``None`` when:
          - No terminal punctuation in ``text[start:]``.
          - All punctuation is inside brackets ``[ ]`` (depth > 0).
          - Punctuation has no trailing whitespace AND is at end of buffer
            (defer-to-next-chunk — avoids "2.5K" / "Dr." mis-fires).
          - The would-be head index is below :data:`MIN_HEAD_LEN`.

    Bracket-depth semantics:
        Only ``[`` / ``]`` count for depth (the citation grammar uses
        square brackets). ``(`` / ``{`` are NOT tracked — they appear in
        prose (parentheticals like "(the groove)") and a period inside
        a parenthetical is still a sentence boundary.
    """
    depth = 0
    n = len(text)
    for i in range(start, n):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in SENTENCE_BOUNDARY_CHARS:
            # Require trailing whitespace (space / newline / tab) OR a non-
            # ambiguous next-character — defer when the period sits at
            # end-of-buffer with nothing after it (might be "2.5K" / "Dr."
            # with the rest arriving in the next chunk).
            if i + 1 >= n:
                # End of buffer — defer to next chunk.
                continue
            nxt = text[i + 1]
            if nxt in " \n\t":
                # idx = i + 2 (past the whitespace) so the head includes it
                # and the tail starts at the next sentence cleanly.
                idx = i + 2
                if idx >= MIN_HEAD_LEN:
                    return idx
                # Short head — continue scanning for a later boundary
                # that satisfies MIN_HEAD_LEN. Don't return None yet — a
                # subsequent boundary in the same accum may still fire.
                continue
            # Non-whitespace follows (e.g. "5K", "K!"). Continue scanning.
    return None


def passes_head_gate(head: str) -> bool:
    """Return True if ``head`` is safe to yield speculatively to TTS.

    Two rejections:

    1. **Silence-token prefix** — the LLM opened with ``<silence/>`` (after
       optional leading whitespace). The whole turn is a suppress; don't
       yield anything.

    2. **Slop prefix** — head starts (after lstrip) with one of the
       :data:`_HEAD_SLOP_PREFIXES`. Locked subset = "Generic AI tells" +
       "Slop framings"; "Empty hype" phrases like "amazing" are NOT in
       this subset (handled by the post-hoc full filter on trailing text).

    Args:
        head: The candidate first-sentence head string. May contain
            leading/trailing whitespace.

    Returns:
        True when the head clears both gates. False when either rejection
        fires.
    """
    stripped = head.lstrip()
    if stripped.startswith(SILENCE_TOKEN):
        return False
    lowered = stripped.lower()
    for prefix in _HEAD_SLOP_PREFIXES:
        if lowered.startswith(prefix):
            return False
    return True
