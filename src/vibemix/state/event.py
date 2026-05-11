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
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vibemix.state.music_state import MusicState


@dataclass
class Event:
    # KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT
    type: str
    state: MusicState
    extra: dict = field(default_factory=dict)
