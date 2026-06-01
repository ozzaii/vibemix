# SPDX-License-Identifier: Apache-2.0
"""TTS-only cleanup for model output.

Raw response artifacts may keep citation atoms such as ``[aud:rms@12.0]`` as
grounding receipts. Audience-facing text and MOSS speech should not carry those
bracket tokens; structured citation chips carry the visible receipt instead.
"""

from __future__ import annotations

import re

from vibemix.agent.emote_parser import strip_emote_tags
from vibemix.state import EVIDENCE_CITATION_RE

_HSPACE_RE = re.compile(r"[ \t\f\v]+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r" +([,.;:!?])")


def strip_citations_for_tts(text: str, *, normalize: bool = False) -> str:
    """Remove grounding citation atoms from TTS text only."""
    raw = text or ""
    if not EVIDENCE_CITATION_RE.search(raw):
        if normalize:
            return re.sub(r"\s+", " ", raw).strip()
        return raw

    cleaned = EVIDENCE_CITATION_RE.sub(" ", raw)
    cleaned = _HSPACE_RE.sub(" ", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    if not cleaned.strip():
        return ""
    if normalize:
        return re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def model_text_for_tts(text: str, *, normalize: bool = False) -> str:
    """Strip internal voice controls and citations from text headed to TTS."""
    spoken_text, _ = strip_emote_tags(text, normalize=normalize)
    return strip_citations_for_tts(spoken_text, normalize=normalize)
