# SPDX-License-Identifier: Apache-2.0
"""Prompt-side mitigation copy for Phase 20 anti-slop.

Single source of truth for the fail-soft instructions appended to the live
system instruction. The fragment teaches Gemini to fail toward a humble
unsourced "I'm listening" line instead of an empty stripped void — see
GROUND-08 + .planning/phases/20-citation-linter-enforcement-live-mode/
20-CONTEXT.md (D-Prompt-Side-Mitigation).

Anti-prompt-injection (T-20-02-01): every constant in this module is a fixed
string with no interpolation, no f-string, no .format() — runtime input
cannot mutate the prompt body. Mirrors MOOD_PERSONAS + CITATION_GRAMMAR_BLOCK
precedent (T-13-05-06, T-18-03-01).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# IM_LISTENING_FRAGMENT — appended to every live system instruction by
# build_system_instruction(..., include_listening_fallback=True).
#
# Whitespace is significant — the leading "\n\n" matches the gap between the
# CITATION_GRAMMAR_BLOCK and this fragment in the rendered system instruction
# (matrix.py appends without a separator, so the fragment owns its own gap).
# ---------------------------------------------------------------------------

IM_LISTENING_FRAGMENT: str = """

--- FAIL-SOFT RULE (live mode) ---

If you cannot cite, say "I'm listening" — never reply with empty text.

When the audio gives you no grounded hook to react to, when the evidence corpus
has no anchor for what you'd want to say, when you would otherwise emit
<silence/> AND the event class is NOT KAAN_SPOKE / MANUAL — prefer a humble
fail-soft line over silence:
  - "I'm listening."
  - "I'm here, just listening."
  - "Tracking it."
  - "Listening through this stretch."

These lines are uncited by design — the cascade may strip them quietly while
your NEXT response (with grounded citation) comes through. Better to fail
toward a humble unsourced line than toward a void; the user knows you're alive,
and the strip happens silently.

THIS RULE DOES NOT OVERRIDE the silence + KAAN_SPOKE / MANUAL rules above —
it ONLY softens the failure mode for ungrounded music-reaction turns.
"""


# ---------------------------------------------------------------------------
# FAIL_SOFT_EXAMPLES — the canonical four phrases enumerated inside the
# fragment body. Plan 20-03's replay harness reads this tuple to recognize
# fail-soft replies in the post-session debrief stream.
#
# Lock invariant (test_fail_soft_examples_subset_of_fragment): every entry
# in this tuple MUST also appear inside IM_LISTENING_FRAGMENT — keeps the
# machine-readable surface in lock-step with the prompt body Gemini sees.
# ---------------------------------------------------------------------------

FAIL_SOFT_EXAMPLES: tuple[str, ...] = (
    "I'm listening.",
    "I'm here, just listening.",
    "Tracking it.",
    "Listening through this stretch.",
)


__all__ = ["FAIL_SOFT_EXAMPLES", "IM_LISTENING_FRAGMENT"]
