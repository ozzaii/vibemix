# SPDX-License-Identifier: Apache-2.0
"""Grounded voice receipts for scored transition verdicts.

This module does not speak. It converts the already-computed transition payload
on a next-suggestion into a bounded prompt receipt Sven may use. The receipt is
derived scorer context, not raw live-audio proof, so every emitted claim carries
EvidenceRegistry citations and the helper abstains when the payload is not
two-deck, confident, and citable.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from vibemix.intel.transition_scorer import LIVE_SELECT_CONFIDENCE_FLOOR

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibemix.state.evidence_registry import EvidenceRegistry

_CITATION_BODY_RE = re.compile(r"^[^\s,\]]+$")
_VOICE_EVENT_TYPES = frozenset({"TRACK_CHANGE", "TRANSITION_OPPORTUNITY"})
_TEXT_ESCAPE = str.maketrans({"[": "(", "]": ")", "\n": " ", "\r": " ", "|": "/"})


def build_transition_verdict_voice_line(
    suggestion: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
) -> str | None:
    """Return a citable prompt receipt for a scored transition payload.

    The rich 10-signal scorer already runs inside ``library.next_suggestion``.
    The live coach should consume that bounded payload, not re-derive a second
    verdict. A receipt is emitted only when the payload has two deck labels, a
    citable incoming track, a citable transition candidate id, and live-mode
    confidence above the scorer's own selection floor.
    """

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if suggestion is None or evidence_registry is None:
        return None

    transition = suggestion.get("transition")
    if not isinstance(transition, Mapping):
        return None

    source_deck = _clean_deck_label(transition.get("source_deck"))
    target_deck = _clean_deck_label(transition.get("target_deck"))
    if source_deck is None or target_deck is None or source_deck == target_deck:
        return None

    confidence = _finite_float(transition.get("confidence"))
    if confidence is None or confidence < LIVE_SELECT_CONFIDENCE_FLOOR:
        return None

    score = _finite_float(transition.get("score"))
    track_id = _clean_citation_body(transition.get("to_track_id")) or _clean_citation_body(
        suggestion.get("track_id")
    )
    candidate_id = _clean_citation_body(transition.get("candidate_id"))
    if track_id is None or candidate_id is None:
        return None

    mix_key = f"transition_verdict={candidate_id}"
    evidence_registry.write("track", track_id, 0.0)
    evidence_registry.write("mix", mix_key, 0.0)

    risk_cite = _register_first_risk_citation(transition, evidence_registry)
    cite_tail = f"[track:{track_id}] [mix:{mix_key}]"
    if risk_cite is not None:
        cite_tail = f"{cite_tail} {risk_cite}"

    role_clause = _role_clause(transition)
    key_clause = _key_clause(transition)
    score_clause = f"score {score:.2f} and " if score is not None else ""
    reasons_clause = _list_clause("Reasons", transition.get("reasons"))
    risks_clause = _list_clause("Risks", transition.get("risk_flags"))

    return (
        "Transition-verdict receipt: the 10-signal transition scorer rated "
        f"deck {source_deck} to deck {target_deck}{role_clause}{key_clause} with "
        f"{score_clause}confidence {confidence:.2f}. "
        f"{reasons_clause}{risks_clause}"
        f"If you mention this transition read, copy these citations exactly: {cite_tail}. "
        "This is derived scorer context, not proof of a fader, EQ, or timing move; "
        "do not invent deck-control causes, and stay silent if the live sound does not support it."
    )


def _register_first_risk_citation(
    transition: Mapping[str, Any],
    evidence_registry: EvidenceRegistry,
) -> str | None:
    risk_flags = transition.get("risk_flags")
    if not isinstance(risk_flags, Sequence) or isinstance(risk_flags, str):
        return None
    for raw in risk_flags:
        risk = _clean_citation_body(raw)
        if risk is None:
            continue
        key = f"transition_risk={risk}"
        evidence_registry.write("mix", key, 0.0)
        return f"[mix:{key}]"
    return None


def _role_clause(transition: Mapping[str, Any]) -> str:
    source_role = _clean_text(transition.get("from_role"), fallback="", cap=28)
    target_role = _clean_text(transition.get("to_role"), fallback="", cap=28)
    if not source_role or not target_role:
        return ""
    return f" ({source_role} to {target_role})"


def _key_clause(transition: Mapping[str, Any]) -> str:
    source_key = _clean_text(transition.get("from_camelot"), fallback="", cap=8)
    target_key = _clean_text(transition.get("to_camelot"), fallback="", cap=8)
    if not source_key or not target_key:
        return ""
    return f", key {source_key} to {target_key},"


def _list_clause(label: str, value: object) -> str:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ""
    cleaned = [
        _clean_text(item, fallback="", cap=96)
        for item in value
        if _clean_text(item, fallback="", cap=96)
    ]
    if not cleaned:
        return ""
    return f"{label}: {'; '.join(cleaned[:2])}. "


def _clean_deck_label(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    deck = value.strip().upper()
    return deck if deck in {"A", "B"} else None


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


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


__all__ = ["build_transition_verdict_voice_line"]
