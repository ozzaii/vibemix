# SPDX-License-Identifier: Apache-2.0
"""Negative dictionary — phrases that, if uttered by the LLM, mark the
output as AI slop. Used by:

1. ``vibemix.prompts.matrix`` — every cell prompt enumerates these as bans.
2. ``vibemix.prompts.filter.filter_for_slop`` — post-hoc regex check on the
   final accumulated LLM text; if any phrase matches, the entire turn is
   replaced with ``<silence/>`` and a ``slop_suppressed`` event is logged.

Four buckets per CONTEXT §Negative dictionary + the stop-slop additions:

- **Generic AI tells** — phrasings real DJ friends never use ("as an AI",
  "delve", "leverage", "synergy").
- **Empty hype** — content-free praise ("amazing", "awesome", "incredible").
- **Slop framings** — corporate-AI sentence frames ("in this dynamic world",
  "navigate the landscape").
- **Stop-slop additions** — essay-voice / corporate-AI tells lifted from
  ``hardikpandya/stop-slop`` @ ``8da1f030`` (MIT). See
  ``.claude/skills/stop-slop/references/phrases.md`` for the full upstream
  list. Only multi-word phrases or distinctively professorial single words
  are lifted here — single adverbs like "really", "just", "actually",
  "honestly" stay author-side because they would false-positive on natural
  DJ-friend speech and nuke whole reactions (whole-turn suppression policy
  in ``filter_for_slop``).
"""

from __future__ import annotations

import re

# Order: AI tells (16), empty hype (16), slop framings (8), stop-slop (23). Total = 63.
NEGATIVE_PHRASES: tuple[str, ...] = (
    # Generic AI tells (16)
    "as an AI",
    "I don't have",
    "I'm here to help",
    "let me know",
    "feel free",
    "happy to assist",
    "delve",
    "leverage",
    "synergy",
    "robust",
    "seamless",
    "comprehensive",
    "elevate",
    "unleash",
    "tapestry",
    "multifaceted",
    # Empty hype (16)
    "amazing",
    "awesome",
    "incredible",
    "fantastic",
    "great mix",
    "wonderful",
    "superb",
    "outstanding",
    "impressive",
    "love it",
    "killing it",
    "nailed it",
    "epic",
    "legendary",
    "phenomenal",
    "magnificent",
    # Slop framings (8)
    "in this dynamic world",
    "at the intersection of",
    "navigate the landscape",
    "unlock the potential",
    "in today's fast-paced",
    "in the realm of",
    "world of possibilities",
    "journey of discovery",
    # Stop-slop additions (23) — hardikpandya/stop-slop @ 8da1f030, MIT.
    # Throat-clearing openers
    "here's the thing",
    "the uncomfortable truth",
    "let me be clear",
    "let me walk you through",
    # Emphasis crutches
    "let that sink in",
    "make no mistake",
    "this matters because",
    "here's why that matters",
    # Filler phrases
    "at its core",
    "it's worth noting",
    "at the end of the day",
    "in a world where",
    "the reality is",
    # Professorial adverbs (DJ friends never reach for these — safe to filter)
    "fundamentally",
    "inherently",
    "interestingly",
    "crucially",
    # Business jargon
    "circle back",
    "double down",
    "game-changer",
    "on the same page",
    # Vague declaratives
    "the implications are significant",
    "the stakes are high",
)

# Compiled regex: word-boundary + alternation, case-insensitive.
# Word boundary semantics: ``\b`` is a unicode-aware word boundary in re.
# - "amazing" matches "Amazing!" but NOT "amazingly" (right boundary breaks).
# - Multi-word phrases like "as an AI" use spaces, which are non-word chars,
#   so boundary checks naturally work at start/end of each phrase.
NEGATIVE_REGEX: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in NEGATIVE_PHRASES) + r")\b",
    re.IGNORECASE,
)
