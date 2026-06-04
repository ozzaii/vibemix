# SPDX-License-Identifier: Apache-2.0
"""Permissioned cue landing across DJ-software carriers.

This module is glue above the existing carriers. It does not detect cues and it
does not write Rekordbox's private database. Producers are normalized through
``propose_smart_cues`` into slot-native ``LandedCue`` rows, then ``land``
requires per-call consent and delegates to the current Rekordbox XML, M3U8, or
Serato/Mixxx tag carriers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library.cue_types import CueAnchor, CueSource
from vibemix.library.rekordbox import TrackEntry
from vibemix.library.smart_cues import (
    SLOTS,
    ReviewStatus,
    SmartCue,
    SmartCuePolicy,
    SmartCueRole,
    SmartCueSlot,
    propose_smart_cues,
)
from vibemix.state import harmonics

TargetKind = Literal["rekordbox_xml", "m3u8", "serato_tags", "mixxx_tags"]
_KNOWN_SOURCES = frozenset({"dj", "anlz", "auto", "fallback"})


@dataclass(frozen=True, slots=True)
class LandedCue:
    cue_id: str
    track_id: str
    slot: SmartCueSlot
    role: SmartCueRole
    start_s: float
    start_beat: int | None
    end_s: float | None
    source: CueSource
    source_detail: str
    source_section_id: str | None
    confidence: float
    review_status: ReviewStatus
    export_label: str
    reason_codes: tuple[str, ...]
    provenance_ref: str


@dataclass(frozen=True, slots=True)
class CueSet:
    track_id: str
    title: str
    artist: str
    filepath: str
    bpm: float | None
    camelot: str | None
    duration_s: float | None
    cues: tuple[LandedCue, ...]
    proposal_id: str | None = None
    policy_version: str | None = None


@dataclass(frozen=True, slots=True)
class ExportTarget:
    kind: TargetKind
    out_path: str | Path | None = None
    name: str = "vibemix landed cues"
    destructive: bool = False
    requires_permission: bool = True

    @classmethod
    def rekordbox_xml(cls, out_path: str | Path, *, name: str = "vibemix landed cues"):
        return cls("rekordbox_xml", out_path=out_path, name=name)

    @classmethod
    def m3u8(cls, out_path: str | Path, *, name: str = "vibemix landed cues"):
        return cls("m3u8", out_path=out_path, name=name)

    @classmethod
    def serato_tags(cls):
        return cls("serato_tags", destructive=True)

    @classmethod
    def mixxx_tags(cls):
        return cls("mixxx_tags", destructive=True)


@dataclass(frozen=True, slots=True)
class LandReceipt:
    path: str
    written_count: int
    kept_dj_count: int
    skipped_count: int
    target: TargetKind
    import_instruction: str


def cue_set_from_smart_cues(
    track: TrackEntry,
    cues: Sequence[SmartCue],
    *,
    proposal_id: str | None = None,
    policy_version: str | None = None,
) -> CueSet:
    landed = tuple(_landed_cue_from_smart(cue) for cue in cues)
    return CueSet(
        track_id=track.track_id,
        title=track.title,
        artist=track.artist,
        filepath=track.filepath,
        bpm=track.bpm if track.bpm and track.bpm > 0 else None,
        camelot=track.camelot or (harmonics.to_camelot(track.key) if track.key else None),
        duration_s=track.duration_s or None,
        cues=landed,
        proposal_id=proposal_id,
        policy_version=policy_version,
    )


def cue_set_from_proposal(
    track: TrackEntry,
    proposal: Any,
    *,
    include_review: bool = False,
    include_preserved: bool = True,
) -> CueSet:
    cues = []
    for cue in proposal.cues:
        if cue.source == "dj" and not include_preserved:
            continue
        if cue.review_status == "review" and not include_review:
            continue
        if cue.review_status not in {"export_ready", "review"}:
            continue
        cues.append(cue)
    return cue_set_from_smart_cues(
        track,
        cues,
        proposal_id=getattr(proposal, "proposal_id", None),
        policy_version=getattr(proposal, "policy_version", None),
    )


def cue_set_from_anchors(
    track: TrackEntry,
    anchors: Sequence[CueAnchor],
    *,
    genre: str | None = None,
    policy: SmartCuePolicy | None = None,
    include_review: bool = False,
    include_preserved: bool = True,
) -> CueSet:
    sections = sections_from_anchors(track, anchors)
    proposal = propose_smart_cues(
        track,
        sections,
        genre=genre,
        policy=policy,
    )
    return cue_set_from_proposal(
        track,
        proposal,
        include_review=include_review,
        include_preserved=include_preserved,
    )


def sections_from_anchors(
    track: TrackEntry,
    anchors: Sequence[CueAnchor],
) -> tuple[SectionRecord, ...]:
    bpm = track.bpm if track.bpm and track.bpm > 0 else None
    camelot = track.camelot or (harmonics.to_camelot(track.key) if track.key else None)
    sections = []
    for index, anchor in enumerate(sorted(anchors, key=lambda cue: cue.start_s)):
        start_s = max(0.0, float(anchor.start_s))
        end_s = float(anchor.end_s)
        if end_s <= start_s:
            end_s = start_s + 1.0
        start_beat = _beat_for_seconds(start_s, bpm)
        end_beat = _beat_for_seconds(end_s, bpm)
        sections.append(
            SectionRecord(
                section_id=f"{track.track_id}#anchor{index:03d}",
                track_id=track.track_id,
                role=_role_for_anchor(anchor),
                source=anchor.source,
                source_detail="cue_anchor",
                confidence=anchor.confidence,
                start_s=start_s,
                end_s=end_s,
                start_beat=start_beat,
                end_beat=end_beat,
                bar_count=_bar_count(start_s, end_s, bpm),
                bpm=bpm,
                camelot=camelot,
                cue_source=anchor.source,
                cue_confidence=anchor.confidence,
            )
        )
    return tuple(sections)


def land(cueset: CueSet, target: ExportTarget, *, granted: bool) -> LandReceipt:
    """Land a reviewed cue set through one carrier after explicit consent."""
    if target.requires_permission and not granted:
        raise PermissionError("cue landing requires per-call user permission")

    marks = [_cue_to_mark(cue) for cue in cueset.cues if _known_source(cue.source)]
    skipped = len(cueset.cues) - len(marks)
    if len(marks) != len(cueset.cues):
        raise ValueError("cue landing refuses cues with empty or unknown source")

    kept_dj = sum(1 for cue in cueset.cues if cue.source == "dj")
    if target.kind == "rekordbox_xml":
        return _land_rekordbox_xml(cueset, marks, target, kept_dj, skipped)
    if target.kind == "m3u8":
        return _land_m3u8(cueset, target, kept_dj, skipped)
    if target.kind in {"serato_tags", "mixxx_tags"}:
        return _land_serato_tags(cueset, marks, target, kept_dj, skipped)
    raise ValueError(f"unknown cue landing target: {target.kind!r}")


def _land_rekordbox_xml(
    cueset: CueSet,
    marks: list[dict[str, Any]],
    target: ExportTarget,
    kept_dj: int,
    skipped: int,
) -> LandReceipt:
    if target.out_path is None:
        raise ValueError("rekordbox_xml landing needs out_path")
    from vibemix.library.export_rekordbox import export_set

    result = export_set([_track_dict(cueset, marks)], target.name, target.out_path)
    return LandReceipt(
        path=str(result.path),
        written_count=len(marks),
        kept_dj_count=kept_dj,
        skipped_count=skipped + len(result.dropped),
        target=target.kind,
        import_instruction=(
            "Rekordbox: Preferences -> Bridge -> Imported Library, choose this XML, "
            "then drag its playlist into your collection."
        ),
    )


def _land_m3u8(
    cueset: CueSet,
    target: ExportTarget,
    kept_dj: int,
    skipped: int,
) -> LandReceipt:
    if target.out_path is None:
        raise ValueError("m3u8 landing needs out_path")
    from vibemix.library.cue_folder import write_m3u8

    path = write_m3u8([_track_dict(cueset, [])], target.out_path)
    return LandReceipt(
        path=str(path),
        written_count=0,
        kept_dj_count=kept_dj,
        skipped_count=skipped,
        target=target.kind,
        import_instruction="Import the M3U8 as an additive crate/playlist; cues ride via tags/XML.",
    )


def _land_serato_tags(
    cueset: CueSet,
    marks: list[dict[str, Any]],
    target: ExportTarget,
    kept_dj: int,
    skipped: int,
) -> LandReceipt:
    from vibemix.library.export_serato import marks_to_serato_cues, write_serato_cues

    result = write_serato_cues(
        cueset.filepath,
        marks_to_serato_cues(marks),
        merge=True,
        allow_write=True,
    )
    if not result.get("written"):
        raise ValueError(str(result.get("reason") or "tag write failed"))
    return LandReceipt(
        path=str(result["path"]),
        written_count=int(result.get("cue_count", len(marks))),
        kept_dj_count=kept_dj,
        skipped_count=skipped,
        target=target.kind,
        import_instruction=(
            "Serato/Mixxx: cues were written as opt-in Serato Markers2 file tags; "
            "reload/rescan the track in your DJ software."
        ),
    )


def _landed_cue_from_smart(cue: SmartCue) -> LandedCue:
    if not _known_source(cue.source):
        raise ValueError(f"unknown cue source: {cue.source!r}")
    return LandedCue(
        cue_id=cue.cue_id,
        track_id=cue.track_id,
        slot=cue.slot,
        role=cue.role,
        start_s=cue.start_s,
        start_beat=cue.start_beat,
        end_s=cue.end_s,
        source=cue.source,
        source_detail=cue.source_detail,
        source_section_id=cue.source_section_id,
        confidence=cue.confidence,
        review_status=cue.review_status,
        export_label=cue.export_label,
        reason_codes=cue.reason_codes,
        provenance_ref=cue.provenance_ref,
    )


def _cue_to_mark(cue: LandedCue) -> dict[str, Any]:
    return {
        "cue_id": cue.cue_id,
        "name": cue.export_label,
        "type": "cue",
        "start_s": cue.start_s,
        "end_s": None,
        "num": SLOTS.index(cue.slot),
        "review_status": cue.review_status,
        "source": cue.source,
    }


def _track_dict(cueset: CueSet, marks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "track_id": cueset.track_id,
        "filepath": cueset.filepath,
        "title": cueset.title,
        "artist": cueset.artist,
        "bpm": cueset.bpm,
        "camelot": cueset.camelot,
        "duration_s": cueset.duration_s,
        "cues": marks,
    }


def _known_source(source: str) -> bool:
    return bool(source) and source in _KNOWN_SOURCES


def _role_for_anchor(anchor: CueAnchor) -> str:
    if anchor.label == "intro":
        return "intro"
    if anchor.label == "build":
        return "build"
    if anchor.label == "breakdown":
        return "breakdown"
    if anchor.label == "drop":
        return "drop"
    return "outro"


def _beat_for_seconds(seconds: float, bpm: float | None) -> int | None:
    if bpm is None or bpm <= 0:
        return None
    return round(float(seconds) * float(bpm) / 60.0)


def _bar_count(start_s: float, end_s: float, bpm: float | None) -> float | None:
    if bpm is None or bpm <= 0:
        return None
    return (end_s - start_s) * bpm / 60.0 / 4.0


__all__ = [
    "CueSet",
    "ExportTarget",
    "LandReceipt",
    "LandedCue",
    "cue_set_from_anchors",
    "cue_set_from_proposal",
    "cue_set_from_smart_cues",
    "land",
    "sections_from_anchors",
]
