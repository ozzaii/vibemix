# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 02 — cited-relevance filter (EVAL-05) + substance metric (EVAL-04).

Two Pitfall mitigations:

- **P45 (cited-but-irrelevant):** ``relevance_score`` strips citation tags
  from the response, then computes a deterministic local token-cosine against
  the evidence payload. Pitfall P45 early-exits with 0.0 when the stripped
  response is < 8 words.
- **P44 (lenient F1):** ``useful_response_ratio`` and
  ``per_event_class_substance`` measure WHAT FRACTION of events got a
  substantive response (per-event substance >= 0.5 OR Flash pass),
  surfacing the "judge says pass but the response was vague" failure mode
  that pure F1 misses.

Public surface (pure-logic):
    - strip_citations(text) -> str
    - cosine(a, b) -> float (zero-vector guard)
    - useful_response_ratio(verdicts) -> float
    - per_event_class_substance(verdicts, event_classes) -> dict[str, float]

Async compatibility surface:
    - relevance_score(response_text, evidence_payload, client=None) -> float
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import numpy as np

_CITATION_RE = re.compile(r"\[(?:ev|track|mix|emote):[^\]]*\]")
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)

# Pitfall P45 floor: responses with fewer words than this (after citation
# strip) cannot anchor — return 0.0 without invoking the API (cost guard).
MIN_STRIPPED_WORDS = 8

# Per-event-class substance gate threshold (per CONTEXT EVAL-04 +
# Pitfall P44). NOTE: this is the PER-EVENT axis threshold; the GATE
# threshold for the ratio is 0.65 (CONTEXT EVAL-04). Different numbers;
# do not conflate.
SUBSTANCE_AXIS_THRESHOLD = 0.5


def strip_citations(text: str) -> str:
    """Remove all citation tags from ``text``. Preserves surrounding prose."""
    return _CITATION_RE.sub("", text)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity with zero-vector guard."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _token_counts(text: str) -> Counter[str]:
    return Counter(
        tok
        for tok in _TOKEN_RE.findall(text.lower())
        if len(tok) > 1 and tok not in _STOPWORDS
    )


def _token_cosine(a_text: str, b_text: str) -> float:
    """Sparse cosine over local token-count vectors."""
    a = _token_counts(a_text)
    b = _token_counts(b_text)
    if not a or not b:
        return 0.0
    dot = sum(float(count) * float(b.get(tok, 0)) for tok, count in a.items())
    if dot == 0.0:
        return 0.0
    na = sum(float(count) ** 2 for count in a.values()) ** 0.5
    nb = sum(float(count) ** 2 for count in b.values()) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def relevance_score(
    response_text: str,
    evidence_payload: str,
    client: Any | None = None,
) -> float:
    """Return cosine similarity between stripped response and evidence payload.

    Returns 0.0 when:
      - stripped response is < 8 words (Pitfall P45 min-8-words floor), OR
      - evidence_payload is empty.

    Otherwise returns a deterministic local token-cosine score in [0, 1].
    ``client`` is accepted only for old call-site compatibility and is not used.
    """
    _ = client
    stripped = strip_citations(response_text).strip()
    if len(stripped.split()) < MIN_STRIPPED_WORDS:
        return 0.0
    if not evidence_payload.strip():
        return 0.0
    return _token_cosine(stripped, evidence_payload)


def useful_response_ratio(verdicts: list[dict[str, Any]]) -> float:
    """Compute the ratio of "useful" verdicts (substance >= 0.5 OR Flash pass).

    Per Pitfall P44: this metric is orthogonal to F1 — a response can be
    "correct" (matches a ground-truth event) but vague ("yeah" with a
    citation pasted on). useful_response_ratio surfaces that failure mode
    that pure F1 misses.

    Returns 0.0 for an empty list (NaN-safe).
    """
    if not verdicts:
        return 0.0
    useful = 0
    for v in verdicts:
        pro_substance = v.get("pro", {}).get("substance", 0.0) if v.get("pro") else 0.0
        flash_pass = v.get("flash", {}).get("pass", False) if v.get("flash") else False
        if pro_substance >= SUBSTANCE_AXIS_THRESHOLD or flash_pass:
            useful += 1
    return useful / len(verdicts)


def per_event_class_substance(
    verdicts: list[dict[str, Any]], event_classes: list[str]
) -> dict[str, float]:
    """Return substance ratio per event type (excluding HEARTBEAT).

    Per Pitfall P44 "per-event-class substance" requirement: DROP /
    PHRASE_BOUNDARY / KICK_SWAP substance regressions surface as
    per-class ratios so the scorecard catches them even when the overall
    ratio passes.

    HEARTBEAT events are exempt (excluded from both numerator + denominator).
    """
    out: dict[str, float] = {}
    for cls in event_classes:
        if cls == "HEARTBEAT":
            continue
        cls_verdicts = [
            v for v in verdicts if v.get("event_type") == cls
        ]
        if not cls_verdicts:
            out[cls] = 0.0
            continue
        out[cls] = useful_response_ratio(cls_verdicts)
    return out
