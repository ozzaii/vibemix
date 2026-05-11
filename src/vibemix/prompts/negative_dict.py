# SPDX-License-Identifier: Apache-2.0
"""Negative dictionary — phrases that, if uttered by the LLM, mark the
output as AI slop. Used by:

1. ``vibemix.prompts.matrix`` — every cell prompt enumerates these as bans.
2. ``vibemix.prompts.filter.filter_for_slop`` — post-hoc regex check on the
   final accumulated LLM text; if any phrase matches, the entire turn is
   replaced with ``<silence/>`` and a ``slop_suppressed`` event is logged.

Three buckets per CONTEXT §Negative dictionary:

- **Generic AI tells** — phrasings real DJ friends never use ("as an AI",
  "delve", "leverage", "synergy").
- **Empty hype** — content-free praise ("amazing", "awesome", "incredible").
- **Slop framings** — corporate-AI sentence frames ("in this dynamic world",
  "navigate the landscape").
"""

from __future__ import annotations

import re

# Order: AI tells first (~16), empty hype (~16), slop framings (~8). Total = 40.
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
