# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-03 — events.jsonl → list[ChapterRegion].

Heuristic per CONTEXT D-3:

- Chapter break on ``TRACK_CHANGE`` event types.
- Chapter break on ``PHASE`` event types older than 30s since the last break.
- Skip ``HEARTBEAT`` events — not chapter-worthy.
- Each chapter's ``[start, end]`` is contiguous: ``chapter[i+1].start ==
  chapter[i].end``. Last chapter ends at the timestamp of the final event.

The originating event's ``t`` provides ``start``; its kind chooses ``kind``.
The ``citation_event_id`` is a stable string the renderer can hand to the
citation-tooltip endpoint (Plan 29-02 ws_server) to resolve evidence.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

__all__ = ["ChapterRegion", "derive_chapters"]

logger = logging.getLogger(__name__)

# Minimum gap between PHASE-driven chapter breaks. TRACK_CHANGE always
# breaks regardless of gap.
_PHASE_MIN_GAP_S = 30.0

# Allowed event-type → ChapterRegion.kind mapping.
# Any other ``type`` value falls into ``kind="phase"`` if it matches the
# phase-driven break logic; otherwise the event is skipped entirely.
_KIND_MAP: dict[str, str] = {
    "TRACK_CHANGE": "track",
    "PHASE": "phase",
    "LAYER_ARRIVAL": "layer",
    "MIX_MOVE": "mix",
    "KAAN_SPOKE": "crowd",
}


@dataclass(frozen=True, slots=True)
class ChapterRegion:
    """One chapter region between two adjacent break-events.

    Fields:
        id: stable identifier (e.g. ``"track-01"``, ``"phase-build-04:32"``).
        start: seconds from session start.
        end: seconds from session start; ``end >= start``.
        label: human-visible label rendered in the renderer sidebar.
        kind: one of ``track | phase | layer | mix | crowd``.
        citation_event_id: ``source:key`` reference the renderer can pass
            to the citation-tooltip endpoint. Format: ``"ev:<TYPE>@<t>"``.
    """

    id: str
    start: float
    end: float
    label: str
    kind: str
    citation_event_id: str


def _format_ts(seconds: float) -> str:
    """``465.6`` → ``"07:45"``."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def _label_for(kind: str, idx: int, event: dict) -> str:
    """Build the human-readable chapter label."""
    ts = _format_ts(event.get("t", 0.0))
    track = event.get("track")
    if kind == "track":
        if track:
            return f"Track {idx + 1}: {track}"
        return f"Track {idx + 1}"
    if kind == "layer":
        return f"Layer arrival at {ts}"
    if kind == "mix":
        return f"Mix at {ts}"
    if kind == "crowd":
        return f"Crowd interaction at {ts}"
    # phase
    phase_name = event.get("phase", "transition")
    return f"{phase_name.title()} at {ts}"


def _chapter_id(kind: str, idx: int, event: dict) -> str:
    """Generate a stable chapter id."""
    if kind == "track":
        return f"track-{idx + 1:02d}"
    ts = _format_ts(event.get("t", 0.0))
    return f"{kind}-{event.get('phase', 'x')}-{ts}"


def _is_break_event(
    event: dict, prev_break_t: float | None
) -> bool:
    """Decide whether ``event`` triggers a new chapter break."""
    if event.get("kind") != "event":
        return False
    etype = event.get("type", "")
    if etype == "HEARTBEAT":
        return False
    if etype == "TRACK_CHANGE":
        return True
    if etype not in _KIND_MAP:
        return False
    # PHASE / LAYER_ARRIVAL / MIX_MOVE / KAAN_SPOKE — require ≥30s gap.
    if prev_break_t is None:
        return True
    return (event.get("t", 0.0) - prev_break_t) >= _PHASE_MIN_GAP_S


def derive_chapters(events_jsonl_path: Path) -> list[ChapterRegion]:
    """Parse ``events_jsonl_path`` and return chapter regions.

    Malformed JSON lines are skipped with a logged warning; derivation
    continues on the remaining lines.

    If the resulting list would be empty (no break-events found), returns
    a single chapter spanning ``[0.0, last_t]`` so the renderer always has
    something to mount.
    """
    events_jsonl_path = Path(events_jsonl_path)
    events: list[dict] = []
    with events_jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError as e:
                logger.warning(
                    "[debrief] events.jsonl line %d malformed, skipped: %s",
                    line_no,
                    e,
                )

    if not events:
        return []

    # Compute session-end (last event's t).
    session_end = max((e.get("t", 0.0) for e in events), default=0.0)

    # First pass — collect break events with their pre-mapped kind.
    breaks: list[dict] = []
    prev_break_t: float | None = None
    for e in events:
        if _is_break_event(e, prev_break_t):
            breaks.append(e)
            prev_break_t = e.get("t", 0.0)

    if not breaks:
        # Degenerate session — synthesize one chapter spanning the whole thing.
        first_t = events[0].get("t", 0.0)
        return [
            ChapterRegion(
                id="chapter-00",
                start=first_t,
                end=session_end,
                label="Session",
                kind="phase",
                citation_event_id=f"ev:SESSION@{first_t:.3f}",
            )
        ]

    # Second pass — convert breaks into ChapterRegions with contiguous bounds.
    chapters: list[ChapterRegion] = []
    for idx, event in enumerate(breaks):
        kind = _KIND_MAP.get(event.get("type", ""), "phase")
        start = float(event.get("t", 0.0))
        end = float(breaks[idx + 1].get("t", session_end)) if idx + 1 < len(breaks) else session_end
        chapters.append(
            ChapterRegion(
                id=_chapter_id(kind, idx, event),
                start=start,
                end=end,
                label=_label_for(kind, idx, event),
                kind=kind,
                citation_event_id=f"ev:{event.get('type', 'EVENT')}@{start:.3f}",
            )
        )
    return chapters
