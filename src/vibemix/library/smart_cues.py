# SPDX-License-Identifier: Apache-2.0
"""Review-first smart hot-cue proposals.

This module is the deterministic policy layer between grounded structure
records and Rekordbox export. It never reads audio, never mutates Rekordbox, and
never asks a model to invent cue positions. The output is a reviewable proposal
with stable A-H slot semantics plus an adapter that preserves explicit hot-cue
slot numbers for XML export.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from vibemix.library.cue_types import CueAnchor, CueLabel
from vibemix.library.rekordbox import CuePoint, TrackEntry

SmartCueSlot = Literal["A", "B", "C", "D", "E", "F", "G", "H"]
SmartCueRole = Literal[
    "mix_in",
    "early_groove",
    "breakdown",
    "main_drop",
    "secondary_drop",
    "mix_out",
    "loop_utility",
    "rescue_or_alt",
]
SmartCueSource = Literal["dj", "anlz", "auto", "fallback"]
ReviewStatus = Literal["export_ready", "review", "suppressed", "missing"]

POLICY_VERSION = "smart-cue-policy-v1"
SLOTS: tuple[SmartCueSlot, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
REQUIRED_SLOTS: frozenset[SmartCueSlot] = frozenset({"A", "D", "F"})
SOURCE_RANK: dict[str, int] = {"dj": 4, "anlz": 3, "auto": 2, "fallback": 1}

SLOT_ROLES: dict[SmartCueSlot, SmartCueRole] = {
    "A": "mix_in",
    "B": "early_groove",
    "C": "breakdown",
    "D": "main_drop",
    "E": "secondary_drop",
    "F": "mix_out",
    "G": "loop_utility",
    "H": "rescue_or_alt",
}

SLOT_EXPORT_LABELS: dict[SmartCueSlot, str] = {
    "A": "VM A IN",
    "B": "VM B GROOVE",
    "C": "VM C BREAK",
    "D": "VM D DROP",
    "E": "VM E DROP2",
    "F": "VM F OUT",
    "G": "VM G LOOP",
    "H": "VM H ALT",
}

GENRE_SLOT_PRIORITIES: dict[str, tuple[SmartCueSlot, ...]] = {
    "techno": ("A", "B", "F", "D", "G", "C", "E", "H"),
    "hardtechno": ("A", "B", "F", "D", "G", "C", "E", "H"),
    "hard tek": ("A", "B", "F", "D", "G", "C", "E", "H"),
    "hardtek": ("A", "B", "F", "D", "G", "C", "E", "H"),
    "house": ("A", "F", "D", "C", "B", "E", "G", "H"),
    "disco": ("A", "F", "D", "C", "B", "E", "G", "H"),
    "drum and bass": ("A", "D", "C", "E", "F", "B", "G", "H"),
    "dnb": ("A", "D", "C", "E", "F", "B", "G", "H"),
    "pop": ("A", "D", "C", "H", "F", "B", "E", "G"),
    "open format": ("A", "D", "C", "H", "F", "B", "E", "G"),
}
DEFAULT_SLOT_PRIORITY: tuple[SmartCueSlot, ...] = ("A", "D", "F", "C", "B", "E", "G", "H")


@dataclass(frozen=True, slots=True)
class SmartCue:
    cue_id: str
    track_id: str
    slot: SmartCueSlot
    role: SmartCueRole
    start_s: float
    start_beat: int | None
    end_s: float | None
    source: SmartCueSource
    source_detail: str
    source_section_id: str | None
    confidence: float
    review_status: ReviewStatus
    export_label: str
    reason_codes: tuple[str, ...]
    provenance_ref: str


@dataclass(frozen=True, slots=True)
class SuppressedCueCandidate:
    track_id: str
    slot: SmartCueSlot | None
    role: SmartCueRole | None
    start_s: float | None
    source: str
    source_section_id: str | None
    confidence: float
    reason_codes: tuple[str, ...]
    provenance_ref: str


@dataclass(frozen=True, slots=True)
class SmartCueProposalSummary:
    export_ready_count: int
    review_count: int
    missing_required_count: int
    suppressed_count: int
    slot_priority: tuple[SmartCueSlot, ...]


@dataclass(frozen=True, slots=True)
class SmartCueProposal:
    proposal_id: str
    track_id: str
    policy_version: str
    cues: tuple[SmartCue, ...]
    missing_slots: tuple[SmartCueSlot, ...]
    suppressed_candidates: tuple[SuppressedCueCandidate, ...]
    summary: SmartCueProposalSummary


@dataclass(frozen=True, slots=True)
class SmartCuePolicy:
    export_ready_floor: float = 0.78
    review_floor: float = 0.55
    source_floor: float = 0.45


@dataclass(frozen=True, slots=True)
class _CueCandidate:
    track_id: str
    slot: SmartCueSlot
    role: SmartCueRole
    start_s: float
    start_beat: int | None
    end_s: float | None
    source: str
    source_detail: str
    source_section_id: str | None
    confidence: float
    provenance_ref: str


def propose_smart_cues(
    track: TrackEntry,
    sections: Sequence[Any],
    *,
    genre: str | None = None,
    existing_cues: Sequence[CuePoint] | None = None,
    policy: SmartCuePolicy | None = None,
) -> SmartCueProposal:
    """Build a deterministic, review-first A-H cue proposal for one track."""
    active_policy = policy or SmartCuePolicy()
    priority = slot_priority_for_genre(genre or track.genre)
    existing = tuple(track.cues if existing_cues is None else existing_cues)
    proposal_id = _proposal_id(track, sections, priority)

    cues: dict[SmartCueSlot, SmartCue] = {}
    used_refs: set[str] = set()
    suppressed: list[SuppressedCueCandidate] = []

    for cue in sorted(existing, key=lambda c: (c.number, float(c.start_s))):
        slot = _slot_from_num(cue.number)
        if slot is None or cue.type not in {"cue", "loop"}:
            continue
        smart = _smart_cue_from_dj_cue(track, cue, proposal_id, slot)
        cues[slot] = smart
        used_refs.add(smart.provenance_ref)

    candidates = _candidates_from_sections(track, sections)
    candidates_by_slot: dict[SmartCueSlot, list[_CueCandidate]] = {slot: [] for slot in SLOTS}
    for candidate in candidates:
        if candidate.source not in SOURCE_RANK:
            suppressed.append(_suppress(candidate, ("no_grounded_source",)))
            continue
        if candidate.confidence < active_policy.source_floor:
            suppressed.append(_suppress(candidate, ("low_source_confidence",)))
            continue
        if candidate.start_s < 0 or (
            track.duration_s and track.duration_s > 0 and candidate.start_s > track.duration_s
        ):
            suppressed.append(_suppress(candidate, ("invalid_start",)))
            continue
        if candidate.slot in cues and cues[candidate.slot].source == "dj":
            suppressed.append(_suppress(candidate, ("human_slot_occupied",)))
            continue
        candidates_by_slot[candidate.slot].append(candidate)

    for slot in priority:
        if slot in cues:
            continue
        selected = _select_candidate(
            slot,
            candidates_by_slot[slot],
            cues=tuple(cues.values()),
            used_refs=used_refs,
            track_bpm=track.bpm,
        )
        if selected is None:
            continue
        candidate, duplicate_reason = selected
        if duplicate_reason is not None:
            suppressed.append(_suppress(candidate, (duplicate_reason,)))
            continue
        if candidate.confidence < active_policy.review_floor:
            suppressed.append(_suppress(candidate, ("low_source_confidence",)))
            continue
        smart = _smart_cue_from_candidate(candidate, proposal_id, active_policy)
        cues[slot] = smart
        used_refs.add(candidate.provenance_ref)

    missing = tuple(slot for slot in sorted(REQUIRED_SLOTS) if slot not in cues)
    ordered_cues = tuple(cues[slot] for slot in SLOTS if slot in cues)
    summary = SmartCueProposalSummary(
        export_ready_count=sum(1 for cue in ordered_cues if cue.review_status == "export_ready"),
        review_count=sum(1 for cue in ordered_cues if cue.review_status == "review"),
        missing_required_count=len(missing),
        suppressed_count=len(suppressed),
        slot_priority=priority,
    )
    return SmartCueProposal(
        proposal_id=proposal_id,
        track_id=track.track_id,
        policy_version=POLICY_VERSION,
        cues=ordered_cues,
        missing_slots=missing,
        suppressed_candidates=tuple(suppressed),
        summary=summary,
    )


def smart_cue_to_anchor(cue: SmartCue) -> CueAnchor:
    """Convert one selected smart cue into the legacy cue-window primitive."""
    source = cue.source if cue.source in {"dj", "anlz", "auto"} else "auto"
    return CueAnchor(
        label=_anchor_label_for_role(cue.role),
        start_s=cue.start_s,
        end_s=cue.end_s if cue.end_s is not None else cue.start_s + 1.0,
        confidence=cue.confidence,
        source=source,  # type: ignore[arg-type]
    )


def proposal_to_export_marks(
    proposal: SmartCueProposal,
    *,
    include_review: bool = False,
    include_preserved: bool = False,
) -> list[dict[str, Any]]:
    """Return slot-preserving `export_set` cue marks for a reviewed proposal.

    By default this exports only machine-proposed `export_ready` cues. Existing
    DJ-authored hot cues are represented in the proposal but are not re-exported
    unless `include_preserved=True`, avoiding accidental overwrite risk.
    """
    marks: list[dict[str, Any]] = []
    for cue in proposal.cues:
        if cue.review_status == "review" and not include_review:
            continue
        if cue.review_status != "export_ready" and not (
            include_review and cue.review_status == "review"
        ):
            continue
        if cue.source == "dj" and not include_preserved:
            continue
        marks.append(
            {
                "cue_id": cue.cue_id,
                "name": cue.export_label,
                "type": "cue",
                "start_s": cue.start_s,
                "end_s": None,
                "num": SLOTS.index(cue.slot),
                "review_status": cue.review_status,
                "source": cue.source,
            }
        )
    return marks


def slot_priority_for_genre(genre: str | None) -> tuple[SmartCueSlot, ...]:
    value = (genre or "").strip().lower()
    if not value:
        return DEFAULT_SLOT_PRIORITY
    for key, priority in GENRE_SLOT_PRIORITIES.items():
        if key in value:
            return priority
    return DEFAULT_SLOT_PRIORITY


def _smart_cue_from_dj_cue(
    track: TrackEntry, cue: CuePoint, proposal_id: str, slot: SmartCueSlot
) -> SmartCue:
    role = SLOT_ROLES[slot]
    label = cue.name.strip() if cue.name and cue.name.strip() else f"HOT CUE {slot}"
    return SmartCue(
        cue_id=f"{proposal_id}:{slot}",
        track_id=track.track_id,
        slot=slot,
        role=role,
        start_s=max(0.0, float(cue.start_s)),
        start_beat=_beat_for_seconds(cue.start_s, track.bpm),
        end_s=cue.end_s,
        source="dj",
        source_detail="hotcue" if cue.type == "cue" else "loop",
        source_section_id=None,
        confidence=0.98,
        review_status="export_ready",
        export_label=label,
        reason_codes=("preserve_human_hot_cue",),
        provenance_ref=f"dj:{track.track_id}:{slot}:{cue.start_s:.3f}",
    )


def _smart_cue_from_candidate(
    candidate: _CueCandidate, proposal_id: str, policy: SmartCuePolicy
) -> SmartCue:
    status: ReviewStatus = (
        "export_ready" if candidate.confidence >= policy.export_ready_floor else "review"
    )
    reason = "high_confidence" if status == "export_ready" else "needs_review"
    return SmartCue(
        cue_id=f"{proposal_id}:{candidate.slot}",
        track_id=candidate.track_id,
        slot=candidate.slot,
        role=candidate.role,
        start_s=candidate.start_s,
        start_beat=candidate.start_beat,
        end_s=candidate.end_s,
        source=candidate.source,  # type: ignore[arg-type]
        source_detail=candidate.source_detail,
        source_section_id=candidate.source_section_id,
        confidence=_clamp01(candidate.confidence),
        review_status=status,
        export_label=SLOT_EXPORT_LABELS[candidate.slot],
        reason_codes=(reason,),
        provenance_ref=candidate.provenance_ref,
    )


def _candidates_from_sections(
    track: TrackEntry, sections: Sequence[Any]
) -> tuple[_CueCandidate, ...]:
    out: list[_CueCandidate] = []
    for index, section in enumerate(sections):
        role = str(getattr(section, "role", "unknown") or "unknown").lower()
        slots = _slots_for_section_role(role)
        for slot in slots:
            out.append(_candidate_for_section(track, section, slot=slot, index=index))
    return tuple(out)


def _candidate_for_section(
    track: TrackEntry, section: Any, *, slot: SmartCueSlot, index: int
) -> _CueCandidate:
    source = str(getattr(section, "source", "") or "")
    source_detail = str(getattr(section, "source_detail", None) or _default_source_detail(source))
    section_id = str(getattr(section, "section_id", "") or f"{track.track_id}#s{index:03d}")
    start_s = float(getattr(section, "start_s", 0.0) or 0.0)
    end_s = getattr(section, "end_s", None)
    confidence = _candidate_confidence(source, float(getattr(section, "confidence", 0.0) or 0.0))
    return _CueCandidate(
        track_id=track.track_id,
        slot=slot,
        role=SLOT_ROLES[slot],
        start_s=start_s,
        start_beat=getattr(section, "start_beat", None),
        end_s=float(end_s) if end_s is not None else None,
        source=source,
        source_detail=source_detail,
        source_section_id=section_id,
        confidence=confidence,
        provenance_ref=f"{source}:{section_id}:{slot}:{start_s:.3f}",
    )


def _slots_for_section_role(role: str) -> tuple[SmartCueSlot, ...]:
    if role == "intro":
        return ("A",)
    if role in {"groove", "body", "verse"}:
        return ("B", "G")
    if role == "build":
        return ("B",)
    if role in {"breakdown", "bridge"}:
        return ("C", "H")
    if role in {"drop", "chorus", "hook"}:
        return ("D", "E", "H")
    if role == "outro":
        return ("F", "G")
    return ("H",)


def _select_candidate(
    slot: SmartCueSlot,
    candidates: list[_CueCandidate],
    *,
    cues: tuple[SmartCue, ...],
    used_refs: set[str],
    track_bpm: float,
) -> tuple[_CueCandidate, str | None] | None:
    usable = [candidate for candidate in candidates if candidate.provenance_ref not in used_refs]
    if not usable:
        return None
    usable.sort(key=lambda candidate: _candidate_sort_key(slot, candidate), reverse=True)
    candidate = usable[0]
    if _near_stronger_cue(candidate, cues, track_bpm=track_bpm):
        return candidate, "duplicate_near_existing"
    return candidate, None


def _candidate_sort_key(slot: SmartCueSlot, candidate: _CueCandidate) -> tuple[float, int, float]:
    source_rank = SOURCE_RANK.get(candidate.source, 0)
    time_value = candidate.start_s
    if slot == "F":
        time_value = -candidate.start_s
    return (candidate.confidence, source_rank, -time_value)


def _near_stronger_cue(
    candidate: _CueCandidate, cues: tuple[SmartCue, ...], *, track_bpm: float
) -> bool:
    if not cues:
        return False
    threshold = _four_bar_seconds(track_bpm)
    for cue in cues:
        if (
            abs(cue.start_s - candidate.start_s) < threshold
            and cue.confidence >= candidate.confidence
        ):
            return True
    return False


def _four_bar_seconds(bpm: float) -> float:
    return 16.0 * 60.0 / bpm if bpm and bpm > 0 else 8.0


def _suppress(candidate: _CueCandidate, reason_codes: tuple[str, ...]) -> SuppressedCueCandidate:
    return SuppressedCueCandidate(
        track_id=candidate.track_id,
        slot=candidate.slot,
        role=candidate.role,
        start_s=candidate.start_s,
        source=candidate.source,
        source_section_id=candidate.source_section_id,
        confidence=_clamp01(candidate.confidence),
        reason_codes=reason_codes,
        provenance_ref=candidate.provenance_ref,
    )


def _candidate_confidence(source: str, confidence: float) -> float:
    if source == "dj":
        return max(0.95, _clamp01(confidence))
    if source == "fallback":
        return min(0.54, _clamp01(confidence))
    if source == "auto":
        return max(0.0, _clamp01(confidence) - 0.05)
    return _clamp01(confidence)


def _default_source_detail(source: str) -> str:
    if source == "anlz":
        return "pssi"
    if source == "auto":
        return "cue_detr_or_dsp"
    if source == "fallback":
        return "whole_track"
    return source or "unknown"


def _slot_from_num(number: int) -> SmartCueSlot | None:
    if 0 <= int(number) <= 7:
        return SLOTS[int(number)]
    return None


def _anchor_label_for_role(role: SmartCueRole) -> CueLabel:
    if role == "mix_in":
        return "intro"
    if role in {"early_groove", "loop_utility"}:
        return "build"
    if role == "breakdown":
        return "breakdown"
    if role in {"main_drop", "secondary_drop", "rescue_or_alt"}:
        return "drop"
    return "outro"


def _beat_for_seconds(seconds: float, bpm: float) -> int | None:
    if not bpm or bpm <= 0:
        return None
    return round(float(seconds) * float(bpm) / 60.0)


def _proposal_id(
    track: TrackEntry, sections: Sequence[Any], priority: tuple[SmartCueSlot, ...]
) -> str:
    h = hashlib.sha256()
    h.update(POLICY_VERSION.encode("utf-8"))
    h.update(b"\0")
    h.update(str(track.track_id).encode("utf-8", "surrogatepass"))
    h.update(b"\0")
    h.update("".join(priority).encode("ascii"))
    for section in sections:
        bits = (
            getattr(section, "section_id", ""),
            getattr(section, "role", ""),
            getattr(section, "source", ""),
            getattr(section, "start_s", ""),
            getattr(section, "end_s", ""),
            getattr(section, "confidence", ""),
        )
        h.update("|".join(str(bit) for bit in bits).encode("utf-8", "surrogatepass"))
        h.update(b"\0")
    return "cueprop_" + h.hexdigest()[:10]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 6)))


__all__ = [
    "DEFAULT_SLOT_PRIORITY",
    "GENRE_SLOT_PRIORITIES",
    "POLICY_VERSION",
    "REQUIRED_SLOTS",
    "SLOTS",
    "SLOT_EXPORT_LABELS",
    "SLOT_ROLES",
    "ReviewStatus",
    "SmartCue",
    "SmartCuePolicy",
    "SmartCueProposal",
    "SmartCueProposalSummary",
    "SmartCueRole",
    "SmartCueSlot",
    "SuppressedCueCandidate",
    "proposal_to_export_marks",
    "propose_smart_cues",
    "slot_priority_for_genre",
    "smart_cue_to_anchor",
]
