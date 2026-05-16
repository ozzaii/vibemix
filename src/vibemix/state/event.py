# SPDX-License-Identifier: Apache-2.0
"""Event dataclass — verbatim port of cohost_v4.py:1162-1166.

The seven canonical event types (KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE /
LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT) are string literals, not enum members,
matching v4. EventDetector returns at most one Event per cycle; AICoach builds
the per-event prompt from ``ev.type`` + ``ev.extra``.

``state`` holds a reference to the MusicState as it was at fire time — readers
should NOT depend on it being a snapshot (the state-refresh writer keeps
mutating the same object); use ``state`` only to read fields synchronously
inside the event-handling code path.

Plan 19-01 extension: ``priority: int`` carries a deterministic per-type
default from EVENT_PRIORITY. CancelGate (runtime/cancel.py) reads this int
to decide whether an incoming Event preempts an in-flight one. The reserved
``DROP`` slot is pre-wired here per CONTEXT D-04 ahead of Phase 17 emitting
real DROP events.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vibemix.state.music_state import MusicState

# Per-type cancel-and-refire ladder (CONTEXT D-04). Higher int = stronger
# claim on the speech bus. MANUAL and DROP tie at the ceiling because both
# represent an unambiguous "react now" — MANUAL is user-issued, DROP is the
# musical climax. KAAN_SPOKE sits one rung below: Kaan's voice should win
# over passive music observations but never over an explicit user trigger.
EVENT_PRIORITY: dict[str, int] = {
    "MANUAL": 10,
    "DROP": 10,
    "KAAN_SPOKE": 9,
    "TRACK_CHANGE": 7,
    "PHASE": 6,
    "MIX_MOVE": 5,
    # Phase 30 Hard Tek overlay detectors — sit just above LAYER_ARRIVAL
    # because a distortion climb / acid-line entry IS the moment in a Hard
    # Tek set worth calling out, on a par with a structural mix move.
    "DISTORTION_CLIMB": 5,
    "ACID_LINE_ENTRY": 5,
    "LAYER_ARRIVAL": 4,
    "HEARTBEAT": 1,
}


@dataclass
class Event:
    # KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT
    type: str
    state: MusicState
    extra: dict = field(default_factory=dict)
    # priority: 0 = "use EVENT_PRIORITY default for this type"; non-zero
    # explicit value bypasses the lookup. Kept LAST in the field order so
    # existing positional callers (Event(type, state, extra=...)) keep working.
    priority: int = 0

    def __post_init__(self) -> None:
        if self.priority == 0:
            self.priority = EVENT_PRIORITY.get(self.type, 0)
