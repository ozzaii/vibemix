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
_VOICE_EVENT_TYPES = frozenset({"PHASE", "TRACK_CHANGE", "TRANSITION_OPPORTUNITY"})
_CUE_LOOKAHEAD_EVENT_TYPES = frozenset({"PHASE", "TRACK_CHANGE"})
_CUE_LOOKAHEAD_CONFIDENCE_FLOOR = 0.7
_CUE_LOOKAHEAD_MAX_ETA_S = 64.0
_TEXT_ESCAPE = str.maketrans({"[": "(", "]": ")", "\n": " ", "\r": " ", "|": "/"})


def build_next_suggestion_voice_line(
    suggestion: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
    state: Any | None = None,
) -> str | None:
    """Return a citable prompt receipt for a current suggestion.

    The suggestion is derived state, not live audio proof. We therefore cite:
    ``[track:<id>]`` for the candidate existing in the library and
    ``[mix:next_suggestion=<id>]`` for the runtime selector choosing it. If the
    candidate id cannot be represented in the citation grammar, we abstain.
    """

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if evidence_registry is None:
        return None
    if suggestion is None:
        return _build_cue_lookahead_voice_line(
            state,
            event_type=event_type,
            evidence_registry=evidence_registry,
        )

    track_id = _clean_citation_body(suggestion.get("track_id"))
    if track_id is None:
        return None

    mix_key = f"next_suggestion={track_id}"
    evidence_registry.write("track", track_id, 0.0)
    evidence_registry.write("mix", mix_key, 0.0)

    risk_cite = _register_risk_citation(suggestion, evidence_registry)
    section = _register_section_pairing(suggestion, evidence_registry)
    section_clause = section[0] if section is not None else ""
    section_cite = section[1] if section is not None else None
    title = _clean_text(suggestion.get("title"), fallback="candidate")
    artist = _clean_text(suggestion.get("artist"), fallback="")
    artist_clause = f" by {artist}" if artist else ""
    why = _clean_text(suggestion.get("why"), fallback="")
    why_clause = f" - {why}" if why else ""

    cite_tail = f"[track:{track_id}] [mix:{mix_key}]"
    if risk_cite is not None:
        cite_tail = f"{cite_tail} {risk_cite}"
    if section_cite is not None:
        cite_tail = f"{cite_tail} {section_cite}"

    return (
        f"Forward read: {title}{artist_clause} pairs next{why_clause}. "
        f"{section_clause}Hand it as one nudge if it fits the live sound. "
        f"Copy these citations exactly: {cite_tail}. Do not say it is loaded "
        "or playing; it is not a proven transition unless deck/live evidence says so."
    )


def _build_cue_lookahead_voice_line(
    state: Any | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry,
) -> str | None:
    if event_type not in _CUE_LOOKAHEAD_EVENT_TYPES or state is None:
        return None

    cue_id = _clean_citation_body(getattr(state, "next_phrase_cue_id", None))
    if cue_id is None:
        return None
    confidence = _finite_float(getattr(state, "phrase_position_confidence", None))
    if confidence is None or confidence < _CUE_LOOKAHEAD_CONFIDENCE_FLOOR:
        return None
    next_phrase_at = _finite_float(getattr(state, "next_phrase_at", None))
    if next_phrase_at is None:
        return None
    set_seconds = _finite_float(getattr(state, "set_seconds", 0.0)) or 0.0
    eta_s = next_phrase_at - set_seconds
    if eta_s <= 0.0 or eta_s > _CUE_LOOKAHEAD_MAX_ETA_S:
        return None

    evidence_registry.write("cue", cue_id, next_phrase_at)
    timing_clause = _phrase_timing_clause(state, eta_s)
    return (
        f"Forward cue receipt: the next citable phrase boundary is {timing_clause}. "
        "Use it as one forward timing nudge for what comes next if the live sound "
        f"supports it. Copy this citation exactly: [cue:{cue_id}]."
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


def _register_section_pairing(
    suggestion: Mapping[str, Any],
    evidence_registry: EvidenceRegistry,
) -> tuple[str, str] | None:
    """Return citable section-pairing copy for a grounded transition."""
    transition = suggestion.get("transition")
    if not isinstance(transition, Mapping):
        return None
    from_role = _clean_citation_body(transition.get("from_role"))
    to_role = _clean_citation_body(transition.get("to_role"))
    if from_role is None or to_role is None:
        return None
    if from_role == "unknown" or to_role == "unknown":
        return None
    key = f"next_suggestion_section={from_role}_to_{to_role}"
    evidence_registry.write("mix", key, 0.0)
    clause = f"Section pairing: mix out of this {from_role} into that {to_role}. "
    return clause, f"[mix:{key}]"


def _clean_citation_body(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or _CITATION_BODY_RE.fullmatch(value) is None:
        return None
    return value


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def _phrase_timing_clause(state: Any, eta_s: float) -> str:
    bpm = _finite_float(getattr(state, "bpm", None))
    bpm_confidence = _finite_float(getattr(state, "bpm_confidence", None)) or 0.0
    if bpm is not None and bpm > 0.0 and bpm_confidence >= 0.6:
        bars = max(1, round((eta_s * bpm) / 240.0))
        unit = "bar" if bars == 1 else "bars"
        return f"about {bars} {unit} ahead"
    return "coming up in the phrase grid"


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
