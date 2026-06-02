# SPDX-License-Identifier: Apache-2.0
"""Write an earned Mastered moment as an additive library hot cue.

This is the safe, source-level half of L3. It does NOT infer track position from
set time. The caller must provide an in-track playhead position; without one the
writer abstains. A failed marker write must never unwind the live credit path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from vibemix.library.export_serato import SeratoCue, read_serato_cues, write_serato_cues

_MAX_HOT_CUE_PADS = 8
_MASTERED_COLOR = (40, 226, 20)


@dataclass(frozen=True, slots=True)
class MasteredMarkerResult:
    """Outcome of an attempted Mastered marker write."""

    written: bool
    reason: str
    path: str = ""
    index: int | None = None
    position_ms: int | None = None
    name: str = ""


def mastered_marker_name(skill_id: str, *, suffix: str | None = None) -> str:
    """Return the stable hot-cue name for a mastered skill."""
    label = (skill_id or "skill").strip().replace("_", " ")
    label = " ".join(label.split()) or "skill"
    name = f"Mastered: {label}"
    if suffix:
        clean_suffix = " ".join(str(suffix).strip().split())
        if clean_suffix:
            name = f"{name} {clean_suffix}"
    return name


def _coerce_position_ms(position_s: float | int | None) -> int | None:
    if position_s is None:
        return None
    try:
        seconds = float(position_s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return round(seconds * 1000.0)


def _first_free_hot_cue_index(existing: list[SeratoCue]) -> int | None:
    used = {int(cue.index) for cue in existing if 0 <= int(cue.index) < _MAX_HOT_CUE_PADS}
    for index in range(_MAX_HOT_CUE_PADS):
        if index not in used:
            return index
    return None


def write_mastered_marker(
    *,
    skill_id: str,
    track_path: str | Path | None,
    position_s: float | int | None,
    allow_write: bool = False,
    name_suffix: str | None = None,
) -> MasteredMarkerResult:
    """Add a "Mastered" hot cue to ``track_path`` when all safety gates pass.

    Safety rules:
    - explicit opt-in only (``allow_write=True``);
    - no inferred set-relative timing; ``position_s`` must be in-track seconds;
    - choose an unused hot-cue pad, preserving all existing hand-set cues;
    - never raise, because this may run next to the live credit/vocal hook.
    """
    name = mastered_marker_name(skill_id, suffix=name_suffix)
    position_ms = _coerce_position_ms(position_s)
    if position_ms is None:
        return MasteredMarkerResult(False, "missing_in_track_position", name=name)
    if not allow_write:
        return MasteredMarkerResult(False, "opt_in_required", position_ms=position_ms, name=name)
    if track_path is None:
        return MasteredMarkerResult(False, "missing_track_path", position_ms=position_ms, name=name)

    path = Path(track_path).expanduser()
    if not path.is_file():
        return MasteredMarkerResult(
            False,
            "track_file_missing",
            path=str(path),
            position_ms=position_ms,
            name=name,
        )

    try:
        existing = read_serato_cues(path)
        for cue in existing:
            if cue.name == name:
                return MasteredMarkerResult(
                    False,
                    "already_present",
                    path=str(path),
                    index=int(cue.index),
                    position_ms=int(cue.position_ms),
                    name=name,
                )

        index = _first_free_hot_cue_index(existing)
        if index is None:
            return MasteredMarkerResult(
                False,
                "no_free_hot_cue_slot",
                path=str(path),
                position_ms=position_ms,
                name=name,
            )

        cue = SeratoCue(index=index, position_ms=position_ms, color=_MASTERED_COLOR, name=name)
        result = write_serato_cues(path, [cue], allow_write=True, merge=True)
        if not bool(result.get("written")):
            return MasteredMarkerResult(
                False,
                str(result.get("reason") or "write_failed"),
                path=str(path),
                index=index,
                position_ms=position_ms,
                name=name,
            )
        return MasteredMarkerResult(
            True,
            "written",
            path=str(path),
            index=index,
            position_ms=position_ms,
            name=name,
        )
    except Exception as exc:
        return MasteredMarkerResult(
            False,
            f"write_error:{type(exc).__name__}",
            path=str(path),
            position_ms=position_ms,
            name=name,
        )


__all__ = [
    "MasteredMarkerResult",
    "mastered_marker_name",
    "write_mastered_marker",
]
