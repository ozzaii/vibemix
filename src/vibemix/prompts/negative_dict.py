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
    # AI self-disclosure variants (2) — complete the "as an AI" concept (the
    # other surface forms a model slips into). Appended at the END so the
    # index-based bucket slicing in agent/_streaming_pipe.py (<16 / >=32) stays
    # valid; landing in the head-gate set (>=32) is intended — a reaction must
    # never OPEN with an AI self-disclosure. The regex below is
    # contraction-tolerant, so "I'm an AI" is caught by the "I am an AI" entry.
    "as a language model",
    "I am an AI",
)

# Contraction/expansion tolerance — a banned phrase must match whether the
# model emits the contracted ("I'm here to help") or expanded ("I am here to
# help") surface form. The old literal ``re.escape`` regex was contraction-
# blind, so a one-token expansion ("I am here to help", "I do not have", "I am
# an AI") silently defeated the backstop (default-slop-sweep finding). One
# generalizing normalization fixes this for EVERY existing phrase at once — it
# is NOT a per-failure phrase ban. (expanded, contracted) pairs:
_CONTRACTION_PAIRS: tuple[tuple[str, str], ...] = (
    ("I am", "I'm"),
    ("I will", "I'll"),
    ("I have", "I've"),
    ("I would", "I'd"),
    ("do not", "don't"),
    ("does not", "doesn't"),
    ("did not", "didn't"),
    ("is not", "isn't"),
    ("are not", "aren't"),
    ("was not", "wasn't"),
    ("were not", "weren't"),
    ("cannot", "can't"),
    ("will not", "won't"),
    ("would not", "wouldn't"),
    ("should not", "shouldn't"),
    ("could not", "couldn't"),
    ("you are", "you're"),
    ("we are", "we're"),
    ("they are", "they're"),
    ("it is", "it's"),
    ("that is", "that's"),
    ("there is", "there's"),
    ("here is", "here's"),
    ("let us", "let's"),
)

_CONTRACTION_RES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(r"\b" + re.escape(contracted) + r"\b", re.IGNORECASE), expanded)
    for expanded, contracted in _CONTRACTION_PAIRS
)


def expand_contractions(text: str) -> str:
    """Canonicalize contractions to their expanded form ("I'm" -> "I am").

    Used only to BUILD ``NEGATIVE_REGEX`` below — the regex itself carries the
    contraction alternation, so consumers (filter_for_slop, reaction-reel
    grade) match raw text directly and downstream text is never mutated.
    """
    for pat, expanded in _CONTRACTION_RES:
        text = pat.sub(expanded, text)
    return text


def _phrase_pattern(phrase: str) -> str:
    """Build a contraction-tolerant regex fragment for one banned phrase: the
    phrase is canonicalized to its expanded form, then each expansion is widened
    to an alternation that also matches the contracted form. So "I'm here to
    help" yields ``(?:I\\ am|I'm) here to help`` and matches either surface."""
    pat = re.escape(expand_contractions(phrase))
    for expanded, contracted in _CONTRACTION_PAIRS:
        esc = re.escape(expanded)
        if esc in pat:
            pat = pat.replace(esc, "(?:" + esc + "|" + re.escape(contracted) + ")")
    return pat


# Compiled regex: word-boundary + alternation, case-insensitive, contraction-
# tolerant (see above). Word boundary semantics: ``\b`` is a unicode-aware word
# boundary in re — "amazing" matches "Amazing!" but NOT "amazingly".
NEGATIVE_REGEX: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(_phrase_pattern(p) for p in NEGATIVE_PHRASES) + r")\b",
    re.IGNORECASE,
)
