# SPDX-License-Identifier: Apache-2.0
"""Build grounded section records from library metadata.

This is the v1 bridge between Rekordbox cues/fallback timing and the INTEL
transition scorer. It deliberately stays deterministic: no model-derived roles
or cue claims enter these records.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.state import harmonics


def sections_for_entry(entry: TrackEntry) -> tuple[SectionRecord, ...]:
    """Build v1 grounded sections from Rekordbox cues or a fallback map."""
    duration_s = float(entry.duration_s or 0.0)
    bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None
    camelot = entry.camelot or (harmonics.to_camelot(entry.key) if entry.key else None)
    cues = sorted(
        [cue for cue in (entry.cues or ()) if cue.type in {"cue", "loop"} and cue.start_s >= 0],
        key=lambda cue: (float(cue.start_s), cue.number),
    )
    if not cues:
        return _fallback_sections_for_entry(entry, duration_s, bpm, camelot)

    sections: list[SectionRecord] = []
    for index, cue in enumerate(cues):
        next_start = cues[index + 1].start_s if index + 1 < len(cues) else None
        end_s = _section_end(cue, next_start, duration_s)
        start_s = max(0.0, float(cue.start_s))
        if end_s <= start_s:
            end_s = start_s + 80.0
        section_id = f"{entry.track_id}#s{index:03d}"
        sections.append(
            SectionRecord(
                section_id=section_id,
                track_id=entry.track_id,
                role=_role_for_cue(cue, index=index, total=len(cues)),
                source="dj",
                source_detail="hotcue" if 0 <= cue.number <= 7 else "memory_cue",
                confidence=1.0,
                start_s=start_s,
                end_s=end_s,
                start_beat=_beat_for_seconds(start_s, bpm),
                end_beat=_beat_for_seconds(end_s, bpm),
                bar_count=_bar_count(start_s, end_s, bpm),
                bpm=bpm,
                camelot=camelot,
                cue_slot=_cue_slot(cue.number),
                cue_source="dj",
                cue_confidence=1.0,
            )
        )
    return tuple(sections)


def best_source_section(sections: tuple[SectionRecord, ...]) -> SectionRecord:
    for role in ("outro", "groove", "drop", "build", "breakdown", "intro"):
        for section in reversed(sections):
            if section.role == role:
                return section
    return sections[-1]


def destination_sections(sections: tuple[SectionRecord, ...]) -> tuple[SectionRecord, ...]:
    preferred = [
        section
        for section in sections
        if section.role in {"intro", "groove", "build", "drop", "breakdown"}
    ]
    return tuple(preferred or sections[:1])


def section_at_position(
    sections: tuple[SectionRecord, ...], position_s: float | None
) -> SectionRecord:
    """Resolve the section containing a live playhead position."""
    if position_s is None:
        return best_source_section(sections)
    position = max(0.0, float(position_s))
    for section in sections:
        if section.start_s <= position < section.end_s:
            return section
    for section in reversed(sections):
        if position >= section.start_s:
            return section
    return sections[0]


def bars_until_section_end(section: SectionRecord, position_s: float | None) -> int | None:
    """Return whole bars until this source section ends, when BPM is known."""
    if position_s is None or section.bpm is None or section.bpm <= 0:
        return None
    seconds = max(0.0, section.end_s - max(0.0, float(position_s)))
    bars = seconds * section.bpm / 60.0 / 4.0
    return max(0, math.ceil(bars))


def section_to_dict(section: SectionRecord) -> dict[str, Any]:
    return asdict(section)


def _fallback_sections_for_entry(
    entry: TrackEntry, duration_s: float, bpm: float | None, camelot: str | None
) -> tuple[SectionRecord, ...]:
    if duration_s >= 96.0:
        intro_end = min(80.0, duration_s)
        outro_start = max(0.0, duration_s - 80.0)
        return (
            SectionRecord(
                section_id=f"{entry.track_id}#s000",
                track_id=entry.track_id,
                role="intro",
                source="fallback",
                source_detail="whole_track",
                confidence=0.45,
                start_s=0.0,
                end_s=intro_end,
                start_beat=_beat_for_seconds(0.0, bpm),
                end_beat=_beat_for_seconds(intro_end, bpm),
                bar_count=_bar_count(0.0, intro_end, bpm),
                bpm=bpm,
                camelot=camelot,
            ),
            SectionRecord(
                section_id=f"{entry.track_id}#s001",
                track_id=entry.track_id,
                role="outro",
                source="fallback",
                source_detail="whole_track",
                confidence=0.45,
                start_s=outro_start,
                end_s=duration_s,
                start_beat=_beat_for_seconds(outro_start, bpm),
                end_beat=_beat_for_seconds(duration_s, bpm),
                bar_count=_bar_count(outro_start, duration_s, bpm),
                bpm=bpm,
                camelot=camelot,
            ),
        )
    end_s = duration_s if duration_s > 0 else 80.0
    return (
        SectionRecord(
            section_id=f"{entry.track_id}#s000",
            track_id=entry.track_id,
            role="unknown",
            source="fallback",
            source_detail="whole_track",
            confidence=0.35,
            start_s=0.0,
            end_s=end_s,
            start_beat=_beat_for_seconds(0.0, bpm),
            end_beat=_beat_for_seconds(end_s, bpm),
            bar_count=_bar_count(0.0, end_s, bpm),
            bpm=bpm,
            camelot=camelot,
        ),
    )


def _section_end(cue: CuePoint, next_start: float | None, duration_s: float) -> float:
    if cue.end_s is not None and cue.end_s > cue.start_s:
        return float(cue.end_s)
    if next_start is not None and next_start > cue.start_s:
        return float(next_start)
    if duration_s > cue.start_s:
        return min(duration_s, cue.start_s + 80.0)
    return float(cue.start_s) + 80.0


def _role_for_cue(cue: CuePoint, *, index: int, total: int) -> str:
    name = (cue.name or "").strip().lower()
    if any(token in name for token in ("intro", "start", "mix in", "mix-in", " in ")):
        return "intro"
    if any(token in name for token in ("groove", "tool", "body", "roll")):
        return "groove"
    if "build" in name or "rise" in name:
        return "build"
    if any(token in name for token in ("break", "breakdown", "reset")):
        return "breakdown"
    if any(token in name for token in ("drop", "slam", "chorus", "hook")):
        return "drop"
    if any(token in name for token in ("outro", "mix out", "mix-out", " out ", "end")):
        return "outro"
    slot = _cue_slot(cue.number)
    if slot == "A":
        return "intro"
    if slot == "B":
        return "groove"
    if slot == "C":
        return "breakdown"
    if slot in {"D", "E"}:
        return "drop"
    if slot == "F":
        return "outro"
    if index == 0:
        return "intro"
    if index == total - 1:
        return "outro"
    return "groove"


def _cue_slot(number: int) -> str | None:
    if 0 <= number <= 7:
        return chr(ord("A") + number)
    return None


def _beat_for_seconds(seconds: float, bpm: float | None) -> int | None:
    if bpm is None or bpm <= 0:
        return None
    return round(seconds * bpm / 60.0)


def _bar_count(start_s: float, end_s: float, bpm: float | None) -> float | None:
    if bpm is None or bpm <= 0:
        return None
    return max(0.0, (end_s - start_s) * bpm / 60.0 / 4.0)


__all__ = [
    "bars_until_section_end",
    "best_source_section",
    "destination_sections",
    "section_at_position",
    "section_to_dict",
    "sections_for_entry",
]
