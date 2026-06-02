# SPDX-License-Identifier: Apache-2.0
"""Write an earned Mastered moment as an additive library hot cue.

This is the safe, source-level half of L3. It does NOT infer track position from
set time. The caller must provide an in-track playhead position; without one the
writer abstains. A failed marker write must never unwind the live credit path.
"""

from __future__ import annotations

import math
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.library.export_serato import SeratoCue, read_serato_cues, write_serato_cues
from vibemix.state.deck_poller import DECK_CITE_MIN_CONF

_MAX_HOT_CUE_PADS = 8
_MASTERED_COLOR = (40, 226, 20)
_POSITION_CITE_MIN_CONF = 0.5


@dataclass(frozen=True, slots=True)
class MasteredMarkerResult:
    """Outcome of an attempted Mastered marker write."""

    written: bool
    reason: str
    path: str = ""
    index: int | None = None
    position_ms: int | None = None
    name: str = ""


@dataclass(frozen=True, slots=True)
class MasteredMarkerRequest:
    """Resolved, safe-to-attempt input for a Mastered marker write."""

    ok: bool
    reason: str
    skill_id: str
    deck: str = ""
    track_id: str = ""
    track_path: str = ""
    position_s: float | None = None


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


def _local_track_path(raw: object) -> str:
    """Normalize a library filepath into a local filesystem path string."""
    text = str(raw or "").strip()
    if not text:
        return ""
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme == "file":
        if parsed.netloc and parsed.netloc not in {"localhost", "127.0.0.1"}:
            return ""
        return urllib.parse.unquote(parsed.path)
    return text


def resolve_mastered_marker_request(
    *,
    skill_id: str,
    state: Any,
    library: Any,
    min_position_confidence: float = _POSITION_CITE_MIN_CONF,
) -> MasteredMarkerRequest:
    """Resolve current live state into a marker-write request, or abstain.

    This is the source-safe L3 glue before the live ``coach.py`` hook: it refuses
    to infer a file cue from set-relative time, mixed/unknown decks, sub-floor
    deck identity, missing library rows, or untrusted track position.
    """
    deck = str(getattr(state, "audible_deck", "") or "").upper()
    if deck not in {"A", "B", "C", "D"}:
        return MasteredMarkerRequest(False, "missing_audible_deck", skill_id=skill_id)

    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None)
    deck_track = decks.get(deck) if isinstance(decks, dict) else None
    if deck_track is None:
        return MasteredMarkerRequest(False, "missing_deck_track", skill_id=skill_id, deck=deck)
    if float(getattr(deck_track, "confidence", 0.0) or 0.0) < DECK_CITE_MIN_CONF:
        return MasteredMarkerRequest(False, "deck_identity_untrusted", skill_id=skill_id, deck=deck)

    track_id = str(getattr(deck_track, "track_id", "") or "").strip()
    if not track_id:
        return MasteredMarkerRequest(False, "missing_track_id", skill_id=skill_id, deck=deck)

    position_ms = _coerce_position_ms(getattr(state, "audible_track_position_s", None))
    if position_ms is None:
        return MasteredMarkerRequest(
            False,
            "missing_in_track_position",
            skill_id=skill_id,
            deck=deck,
            track_id=track_id,
        )
    position_s = position_ms / 1000.0
    if float(getattr(state, "audible_track_position_confidence", 0.0) or 0.0) < float(
        min_position_confidence
    ):
        return MasteredMarkerRequest(
            False,
            "position_untrusted",
            skill_id=skill_id,
            deck=deck,
            track_id=track_id,
            position_s=position_s,
        )

    lookup = getattr(library, "lookup_by_id", None)
    entry = lookup(track_id) if callable(lookup) else None
    if entry is None:
        return MasteredMarkerRequest(
            False,
            "library_track_missing",
            skill_id=skill_id,
            deck=deck,
            track_id=track_id,
            position_s=position_s,
        )

    track_path = _local_track_path(getattr(entry, "filepath", ""))
    if not track_path:
        return MasteredMarkerRequest(
            False,
            "missing_track_path",
            skill_id=skill_id,
            deck=deck,
            track_id=track_id,
            position_s=position_s,
        )

    return MasteredMarkerRequest(
        True,
        "ready",
        skill_id=skill_id,
        deck=deck,
        track_id=track_id,
        track_path=track_path,
        position_s=position_s,
    )


def write_mastered_marker_from_state(
    *,
    skill_id: str,
    state: Any,
    library: Any,
    allow_write: bool = False,
    name_suffix: str | None = None,
    min_position_confidence: float = _POSITION_CITE_MIN_CONF,
) -> MasteredMarkerResult:
    """Resolve state+library and attempt the opt-in Mastered marker write."""
    request = resolve_mastered_marker_request(
        skill_id=skill_id,
        state=state,
        library=library,
        min_position_confidence=min_position_confidence,
    )
    if not request.ok:
        return MasteredMarkerResult(False, request.reason, name=mastered_marker_name(skill_id))
    return write_mastered_marker(
        skill_id=skill_id,
        track_path=request.track_path,
        position_s=request.position_s,
        allow_write=allow_write,
        name_suffix=name_suffix,
    )


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
    "MasteredMarkerRequest",
    "MasteredMarkerResult",
    "mastered_marker_name",
    "resolve_mastered_marker_request",
    "write_mastered_marker",
    "write_mastered_marker_from_state",
]
