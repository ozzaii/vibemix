# SPDX-License-Identifier: Apache-2.0
"""Grounded voice receipts for move-grade transition coaching.

Move grades are already produced by the transition scorer. This helper turns
that existing payload into one citable prompt receipt so Sven can coach the
next move from library/scorer evidence instead of inventing a verdict.
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
_NEGATIVE_SLUGS = frozenset({"negative"})
_CARE_SLUGS = frozenset({"mid"})


def build_move_grade_voice_line(
    suggestion: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
) -> str | None:
    """Return a citable prompt receipt for a selected transition move grade."""

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if suggestion is None or evidence_registry is None:
        return None

    transition = suggestion.get("transition")
    if not isinstance(transition, Mapping):
        return None
    grade = transition.get("move_grade")
    if not isinstance(grade, Mapping):
        return None

    slug = _clean_citation_body(grade.get("slug"))
    candidate_id = _clean_citation_body(transition.get("candidate_id"))
    track_id = _clean_citation_body(transition.get("to_track_id")) or _clean_citation_body(
        suggestion.get("track_id")
    )
    if slug is None or candidate_id is None or track_id is None:
        return None

    grade_key = f"move_grade={candidate_id}:{slug}"
    evidence_registry.write("track", track_id, 0.0)
    evidence_registry.write("mix", grade_key, 0.0)

    progress_cite = _register_progress_citation(suggestion, grade, evidence_registry)
    cite_tail = f"[track:{track_id}] [mix:{grade_key}]"
    if progress_cite is not None:
        cite_tail = f"{cite_tail} {progress_cite}"

    title = _clean_text(suggestion.get("title"), fallback="the next option")
    artist = _clean_text(suggestion.get("artist"), fallback="")
    subject = f"{title} by {artist}" if artist else title
    label = _clean_text(grade.get("label"), fallback=slug.upper(), cap=24)
    reason = _clean_text(grade.get("reason"), fallback="the scorer fit is grounded")
    confidence = _finite_float(grade.get("confidence"))
    confidence_clause = f" at confidence {confidence:.2f}" if confidence is not None else ""
    coaching_clause = _coaching_clause(subject, slug, reason, suggestion.get("grade_progress"))

    return (
        "Move-grade receipt: the transition scorer graded "
        f"{subject} as {label} because {reason}{confidence_clause}. "
        f"{coaching_clause} "
        f"Copy these citations exactly: {cite_tail}. "
        "This is scorer context; coach it as a next-move option, not a live outcome."
    )


def _coaching_clause(
    subject: str,
    slug: str,
    reason: str,
    progress: object,
) -> str:
    if slug in _NEGATIVE_SLUGS:
        return f"Coach the DJ toward a safer bridge than {subject}; {reason}."
    if slug in _CARE_SLUGS:
        return f"Coach {subject} as a careful option; {reason}."
    if isinstance(progress, Mapping) and bool(progress.get("level_up")):
        return f"Coach {subject} as the confident next move; {reason}, and the run levels up."
    if isinstance(progress, Mapping) and bool(progress.get("earned")):
        return f"Coach {subject} as the confident next move; {reason}."
    return f"Coach {subject} as the next option; {reason}."


def _register_progress_citation(
    suggestion: Mapping[str, Any],
    grade: Mapping[str, Any],
    evidence_registry: EvidenceRegistry,
) -> str | None:
    progress = suggestion.get("grade_progress")
    if not isinstance(progress, Mapping):
        return None
    if not (bool(progress.get("earned")) or bool(progress.get("level_up"))):
        return None
    slug = _clean_citation_body(grade.get("slug"))
    level = _bounded_int(progress.get("level"), 1, 999)
    total_xp = _bounded_int(progress.get("total_xp"), 0, 999_999)
    if slug is None or level is None or total_xp is None:
        return None
    key = f"move_grade_progress={slug}:lvl{level}:xp{total_xp}"
    evidence_registry.write("mix", key, 0.0)
    return f"[mix:{key}]"


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


def _bounded_int(value: object, floor: int, ceiling: int) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < floor or parsed > ceiling:
        return None
    return parsed


__all__ = ["build_move_grade_voice_line"]
