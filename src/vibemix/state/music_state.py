# SPDX-License-Identifier: Apache-2.0
"""MusicState dataclass — verbatim port of cohost_v4.py:1009-1062.

This is the single source of truth refreshed at 10Hz by ``state_refresh_loop``
(wave 4). ``EventDetector`` and ``AICoach`` are READ-ONLY consumers — only
``state_refresh_loop`` writes, and its writes are batched inside
``with state._lock:`` so multi-field consistent snapshots are achievable.

Field defaults match v4 EXACTLY. Section comments are LOAD-BEARING developer
documentation (the v4 comments tell consumers what each block represents);
they are preserved verbatim.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class MusicState:
    """Single source of truth. Refreshed at 10Hz from audio + MIDI + track poll.
    Everything the EventDetector and AICoach need — and nothing they don't.
    Read-only from the consumer side; only state_refresh_loop writes to it."""

    # Audio
    audible: bool = False  # debounced — true only when sustained sound
    rms: float = 0.0
    bands: dict = field(default_factory=lambda: {"sub": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0})
    onset_density: float = 0.0
    bpm: float = 0.0
    energy_curve: list = field(default_factory=list)  # last ~12s, 1s hop

    # Phase (derived from energy curve, only valid when audible)
    phase: str = "silent"  # silent / low / groove / build / drop / peak / breakdown
    phase_started_at: float = 0.0

    # Controller (snapshot from MIDI thread)
    deck_a: dict = field(default_factory=dict)
    deck_b: dict = field(default_factory=dict)
    xfader: int = 64
    controller_connected: bool = False

    # Audible deck inference — which deck is producing the sound NOW
    audible_deck: str = "none"  # 'A' / 'B' / 'mix' / 'none'
    deck_confidence: float = 0.0  # 0..1

    # Track (cross-referenced with audible deck)
    audible_track: str | None = None
    audible_track_confidence: float = 0.0  # 0..1 — feeds into prompt as `(unsure)` flag
    last_audible_track: str | None = None  # what was audible last refresh (for change detection)

    # Recent moves (within last 12s, deck-attributed)
    recent_moves: list = field(default_factory=list)

    # Historical context — lets the AI reference set shape and continuity
    long_arc: list = field(default_factory=list)  # ~120s RMS, 10s hop
    phase_history: list = field(default_factory=list)  # [(t, from, to)] last 6
    track_history: list = field(default_factory=list)  # [(t, title)] last 6 audible titles

    # Set timing
    set_start_at: float = 0.0
    last_kaan_spoke_at: float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def set_seconds(self) -> float:
        return time.time() - self.set_start_at if self.set_start_at else 0.0

    @property
    def time_in_phase(self) -> float:
        return time.time() - self.phase_started_at if self.phase_started_at else 0.0
