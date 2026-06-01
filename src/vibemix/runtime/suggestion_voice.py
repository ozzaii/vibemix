# SPDX-License-Identifier: Apache-2.0
"""Grounded voice receipts for the live next-suggestion engine.

This module does not speak. It creates a prompt line Sven may use when the
existing LLM path decides a recommendation is worth mentioning. The line carries
EvidenceRegistry citations for both the candidate track and the fact that the
live suggestion engine selected it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibemix.state.evidence_registry import EvidenceRegistry

_CITATION_BODY_RE = re.compile(r"^[^\s,\]]+$")
_VOICE_EVENT_TYPES = frozenset({"TRACK_CHANGE", "TRANSITION_OPPORTUNITY"})
_TEXT_ESCAPE = str.maketrans({"[": "(", "]": ")", "\n": " ", "\r": " ", "|": "/"})


def build_next_suggestion_voice_line(
    suggestion: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
) -> str | None:
    """Return a citable prompt receipt for a current suggestion.

    The suggestion is derived state, not live audio proof. We therefore cite:
    ``[track:<id>]`` for the candidate existing in the library and
    ``[mix:next_suggestion=<id>]`` for the runtime selector choosing it. If the
    candidate id cannot be represented in the citation grammar, we abstain.
    """

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if suggestion is None or evidence_registry is None:
        return None

    track_id = _clean_citation_body(suggestion.get("track_id"))
    if track_id is None:
        return None

    mix_key = f"next_suggestion={track_id}"
    evidence_registry.write("track", track_id, 0.0)
    evidence_registry.write("mix", mix_key, 0.0)

    risk_cite = _register_risk_citation(suggestion, evidence_registry)
    title = _clean_text(suggestion.get("title"), fallback="candidate")
    artist = _clean_text(suggestion.get("artist"), fallback="")
    artist_clause = f" by {artist}" if artist else ""
    why = _clean_text(suggestion.get("why"), fallback="")
    why_clause = f"Reason: {why}. " if why else ""

    cite_tail = f"[track:{track_id}] [mix:{mix_key}]"
    if risk_cite is not None:
        cite_tail = f"{cite_tail} {risk_cite}"

    return (
        "Next-suggestion receipt: the live suggestion engine selected "
        f"{title}{artist_clause}. {why_clause}If you recommend it, keep it optional, "
        f"copy these citations exactly: {cite_tail}. Do not say it is loaded or "
        "playing. This is not a proven transition unless deck/live evidence says so; "
        "stay silent if the moment is not right."
    )


def _register_risk_citation(
    suggestion: Mapping[str, Any],
    evidence_registry: EvidenceRegistry,
) -> str | None:
    transition = suggestion.get("transition")
    if not isinstance(transition, Mapping):
        return None
    risk_flags = transition.get("risk_flags")
    if not isinstance(risk_flags, (list, tuple)):
        return None
    for raw in risk_flags:
        risk = _clean_citation_body(raw)
        if risk is None:
            continue
        key = f"next_suggestion_risk={risk}"
        evidence_registry.write("mix", key, 0.0)
        return f"[mix:{key}]"
    return None


def _clean_citation_body(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or _CITATION_BODY_RE.fullmatch(value) is None:
        return None
    return value


def _clean_text(value: object, *, fallback: str, cap: int = 72) -> str:
    if not isinstance(value, str):
        return fallback
    text = " ".join(value.translate(_TEXT_ESCAPE).split())
    if not text:
        return fallback
    if len(text) <= cap:
        return text
    return text[: cap - 1].rstrip() + "..."


__all__ = ["build_next_suggestion_voice_line"]
