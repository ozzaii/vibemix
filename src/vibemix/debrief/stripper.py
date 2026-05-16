# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-07 hard gate — sentence-level cited-critique filter.

Reuses the Phase 18 locked grammar :data:`EVIDENCE_CITATION_RE`. Sentences
without ≥ 1 citation match are dropped. The stripper is THE last line of
defense between Gemini output and the renderer; every text field that the
user will read passes through here before persistence.

Plan 29-07 wires this into tldr.py + drills.py + main.py orchestrator so
no text reaches the UI without a citation in every sentence.
"""

from __future__ import annotations

import logging
import re

from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE

__all__ = [
    "UncitedSentencesFound",
    "assert_all_cited",
    "strip_uncited_sentences",
]

logger = logging.getLogger(__name__)

# Sentence boundary — ASCII end-of-sentence punctuation followed by whitespace.
# Conservative split: keeps abbreviations like "Mr." intact at the cost of
# occasionally not splitting a missing-space typo. The cost is acceptable.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class UncitedSentencesFound(Exception):
    """Raised by :func:`assert_all_cited` when stripper would have dropped > 0.

    Used by tldr.py + drills.py as a post-strip guard so the orchestrator
    can surface a typed :class:`DebriefError` instead of shipping empty
    text.
    """

    def __init__(self, reason: str = "uncited_sentences"):
        super().__init__(reason)
        self.reason = reason


def strip_uncited_sentences(text: str) -> tuple[str, int]:
    """Drop every sentence in ``text`` that lacks a ``[source:body]`` citation.

    Returns ``(filtered_text, stripped_count)``.

    Sentence split is on the ASCII end-of-sentence punctuation; trailing
    whitespace is normalized to single spaces in the rejoined output. Empty
    input → ``("", 0)``.

    Each dropped sentence is logged at INFO level for debugging.
    """
    if not text or not text.strip():
        return ("", 0)
    sentences = _SENTENCE_BOUNDARY.split(text.strip())
    kept: list[str] = []
    dropped = 0
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        if EVIDENCE_CITATION_RE.search(s_strip):
            kept.append(s_strip)
        else:
            dropped += 1
            logger.info("[debrief] stripped uncited: %r", s_strip)
    return (" ".join(kept), dropped)


def assert_all_cited(text: str) -> None:
    """Raise :class:`UncitedSentencesFound` if any sentence lacks a citation.

    Use as a post-strip guard in tldr.py / drills.py so empty / mostly-empty
    outputs surface as a typed error rather than shipping silent gaps.
    """
    if not text or not text.strip():
        # Empty is a degenerate case — orchestrator handles separately.
        return
    sentences = _SENTENCE_BOUNDARY.split(text.strip())
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        if not EVIDENCE_CITATION_RE.search(s_strip):
            raise UncitedSentencesFound("uncited_sentences")
