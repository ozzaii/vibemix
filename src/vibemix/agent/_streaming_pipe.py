# SPDX-License-Identifier: Apache-2.0
"""Streaming-pipe gate primitives for ``DJCoHostAgent.llm_node``.

The pipe yields chunks to TTS as fast as the LLM emits them. The gate
here is the single guard that runs BEFORE the first yield to keep two
classes of bad opener from reaching the listener:

  * **Silence-token openers** — the LLM emitted ``<silence/>`` as the
    head; the whole turn must be suppressed (post-stream silence gate is
    the authority and will not re-emit, so deferring at the chunk gate
    keeps us byte-identical to "never spoke a word").

  * **Slop-prefix openers** — head starts with a never-opens phrase
    ("as an AI", "here's the thing", "fundamentally", …). These are the
    AI-tells + slop-framings + stop-slop additions from
    :mod:`vibemix.prompts.negative_dict`. The post-stream
    :func:`vibemix.prompts.filter.filter_for_slop` is the authority on
    suppressing the FULL response, but once chunks reach TTS they cannot
    be unspoken — so the chunk gate must catch the prefix BEFORE we let
    the first chunk out.

:func:`can_yield_chunks` is the unified gate. It accepts the accumulated
text-so-far and returns ``True`` iff the prefix is safe AND unambiguous —
i.e. (a) does not match any banned prefix AND (b) is long enough that no
banned prefix could still be forming. Until the gate clears, chunks
accumulate in the LLM stream consumer's local buffer; once it clears,
the buffer flushes and all subsequent chunks pass through verbatim.

This replaces the earlier sentence-boundary-buffering design (Plan
41-04). That design waited for terminal punctuation before yielding,
which hid LLM TTFT behind buffer-then-yield but added a 500ms-2s wait
for the first audible word AND failed entirely for single-sentence
responses (the EOS defer in the old ``find_sentence_end``: a period at
the last buffer position never resolved without a next chunk that never
arrived). The chunk-by-chunk yield is strictly faster perceived TTFT
and gracefully handles short single-sentence responses.

The slop-prefix subset is INTENTIONALLY narrower than the full
``NEGATIVE_PHRASES`` list. The 16 "Empty hype" phrases ("amazing",
"killer", "love it") are NOT here — they can legitimately open a real
DJ-friend reaction; the post-stream filter still catches them on the
trailing text. The head gate's subset is the union of (a) "Generic AI
tells" (idx < 16) + (b) "Slop framings" (idx 32..40) + (c) "Stop-slop
additions" (idx >= 40, lifted from ``hardikpandya/stop-slop`` MIT).

:func:`find_sentence_end` and :func:`passes_head_gate` are kept for
backward compatibility (test imports, ``vibemix.agent`` ``__init__``
re-export). They are no longer called from ``llm_node``.
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


# ---- Speed-gate (chunk-by-chunk yield) ----

# Pre-compute max prefix length so we can short-circuit ``can_yield_chunks``
# once the accumulated text is unambiguously past any banned prefix.
_MAX_GATED_PREFIX_LEN: int = max(
    (len(p) for p in _HEAD_SLOP_PREFIXES),
    default=0,
)
_MAX_GATED_PREFIX_LEN = max(_MAX_GATED_PREFIX_LEN, len(SILENCE_TOKEN))


def can_yield_chunks(text: str) -> bool:
    """Return True iff the accumulated ``text`` is safe to flush to TTS.

    Two-part check (cheap; called inside the per-chunk consumer loop):

    1. **Locked match** — if (after ``lstrip``) the text starts with the
       silence-token OR any banned slop prefix, return ``False``.
       Adding more chunks cannot un-match a ``startswith`` hit, so this
       result is permanent for the turn — the post-stream silence/slop
       gate is the authority and will suppress the full response.

    2. **Still-disambiguating** — if the stripped text is SHORTER than
       any banned prefix that ``startswith`` it (i.e. the text could
       still grow into a banned prefix on the next chunk), return
       ``False``. The caller defers this round, the chunk goes into the
       accumulator, and the gate is re-checked when more chars arrive.

    When neither condition holds, the prefix is unambiguous and safe —
    the caller flushes its accumulator to TTS and switches to direct
    chunk-by-chunk yield for the rest of the stream.

    Args:
        text: Accumulated text from the LLM stream so far.

    Returns:
        True when the prefix is safe AND long enough to be unambiguous.
    """
    stripped = text.lstrip()
    if not stripped:
        # No content yet (pure whitespace) — defer; nothing to flush.
        return False

    # Locked-match check (permanent fail for the turn).
    if stripped.startswith(SILENCE_TOKEN):
        return False
    lowered = stripped.lower()
    for prefix in _HEAD_SLOP_PREFIXES:
        if lowered.startswith(prefix):
            return False

    # Short-circuit: once the accumulated text is longer than the longest
    # gated prefix, no prefix can still be forming. Safe.
    if len(stripped) >= _MAX_GATED_PREFIX_LEN:
        return True

    # Still-disambiguating check: any banned prefix that the current text
    # is a strict prefix of? If yes, defer — the next chunk might land
    # the matching character.
    if len(stripped) < len(SILENCE_TOKEN) and SILENCE_TOKEN.startswith(stripped):
        return False
    for prefix in _HEAD_SLOP_PREFIXES:
        if len(lowered) < len(prefix) and prefix.startswith(lowered):
            return False

    return True


def last_balanced_position(text: str) -> int:
    """Return the largest ``i`` such that ``text[:i]`` has every ``[``
    matched by a later ``]``.

    The chunk-by-chunk yield uses this to clip mid-stream chunks at the
    boundary of an unclosed citation: e.g. ``"Killer drop [ev:kick@2.5"``
    yields up to position 12 (``"Killer drop "``), holding the
    half-citation in the consumer's accumulator until the next chunk
    closes the bracket. This keeps TTS from receiving a bare ``"[ev:"``
    fragment and trying to speak it.

    Only ``[`` / ``]`` count for depth (citations use square brackets;
    parentheticals like ``(the groove)`` do not). Mirrors
    :func:`find_sentence_end` bracket semantics.

    Args:
        text: Accumulated text from the LLM stream.

    Returns:
        The position ``i`` such that ``text[:i]`` has no unclosed ``[``.
        Returns ``len(text)`` when every bracket is closed.
    """
    depth = 0
    last_balanced = 0
    for i, ch in enumerate(text):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
            if depth == 0:
                last_balanced = i + 1
        elif depth == 0:
            last_balanced = i + 1
    return last_balanced
