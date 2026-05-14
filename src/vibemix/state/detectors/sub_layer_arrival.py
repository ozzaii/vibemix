# SPDX-License-Identifier: Apache-2.0
"""SubLayerArrivalDetector — sub bass / 808 / sub-trade arrival.

Fires when ``state.bands["sub"]`` jumps by at least ``SUB_JUMP_THRESHOLD``
versus the trailing ~8s baseline AND BPM stayed stable (|Δbpm| ≤ 4.0). The
BPM-stability gate is the anti-double-fire contract with TRACK_CHANGE
(Plan 17-02 threat register T-17-02-02): cross-track sub jumps almost always
shift BPM by >4 in dance music, so TRACK_CHANGE owns those moments and
SUB_LAYER_ARRIVAL only catches in-flight sub-layer arrivals (a producer
dropping the 808, a DJ EQ-restoring the bass after a kill).

Reads ``state.bands["sub"]`` directly — does NOT re-derive from raw samples.
``state_refresh_loop._tick_once`` already computed ``feats["sub_share"]`` for
the canonical 16384-sample FFT window; re-computing here would duplicate the
writer's work and risk numerical disagreement with what the rest of the system
sees. ``audio_buf`` is accepted as a parameter for API symmetry with
``KickSwapDetector`` but explicitly unused.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
    SUB_JUMP_THRESHOLD,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# Trailing baseline window — symmetrical with ``BUILDUP_SLOPE_WINDOW_S`` so all
# Phase 17 trailing-window detectors share a consistent "recent past" horizon.
_BASELINE_WINDOW_SEC: float = 8.0
# BPM-stability tolerance — a dance-music BPM that wanders by ≤4 BPM is the
# same track (DJ tempo-fader nudge). >4 is a track change suspect; we yield to
# TRACK_CHANGE rather than fire on top of it.
_BPM_STABILITY_TOLERANCE: float = 4.0


class SubLayerArrivalDetector:
    """Reads ``state.bands["sub"]`` + ``state.bpm``; never touches audio_buf.

    Fields are public-readable for tests + observability — never mutated by
    anything other than ``detect()``.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        self.baseline_sub: float | None = None
        self.baseline_bpm: float = 0.0
        self.baseline_at: float = 0.0

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return an ``Event("SUB_LAYER_ARRIVAL", ...)`` when sub jumps under
        a stable BPM, else ``None``.

        ``audio_buf`` is unused — the detector consumes ``state.bands["sub"]``
        which the state-refresh writer already populated. Re-deriving from
        raw samples would duplicate the snapshot_features call the writer
        just did and risk numerical disagreement.
        """
        del audio_buf  # unused — see module docstring + class docstring

        # 1. Silence gate — must run BEFORE baseline seeding so a breakdown
        #    doesn't seed a "sub=0" baseline that the next audible tick diffs
        #    against (would false-fire the moment music returns).
        if state.rms < LOW_RMS:
            return None

        current_sub = state.bands.get("sub", 0.0)
        current_bpm = state.bpm

        # 2. First call ever — seed baseline + bail.
        if self.baseline_sub is None:
            self.baseline_sub = current_sub
            self.baseline_bpm = current_bpm
            self.baseline_at = now
            return None

        # 3. Window guard — the baseline must be at least one full
        #    _BASELINE_WINDOW_SEC old before we treat the comparison as
        #    "current vs trailing-8s baseline" rather than "current vs
        #    half-second-ago baseline". Returning None without rotating keeps
        #    the original baseline intact for the next eligible tick.
        if now - self.baseline_at < _BASELINE_WINDOW_SEC:
            return None

        # 4. BPM-stability gate — anti-double-fire with TRACK_CHANGE
        #    (T-17-02-02). A BPM jump > 4.0 strongly suggests a new track;
        #    rotate baseline (so we don't carry a stale pre-mix anchor) and
        #    yield to the TRACK_CHANGE detector.
        if abs(current_bpm - self.baseline_bpm) > _BPM_STABILITY_TOLERANCE:
            self.baseline_sub = current_sub
            self.baseline_bpm = current_bpm
            self.baseline_at = now
            return None

        # 5. Cooldown gate — refuse to fire twice within the per-type cooldown.
        #    Unlike KickSwapDetector, we do NOT rotate baseline on cooldown —
        #    keeping the pre-fire baseline lets the post-cooldown tick still
        #    see the jump if it's persistent (which is what a real sub-layer
        #    arrival looks like).
        if now - self.last_event_at < MIN_EVENT_GAP_PER_TYPE["SUB_LAYER_ARRIVAL"]:
            return None

        # 6. Sub jump check — fire if the jump crosses the threshold.
        sub_jump = current_sub - self.baseline_sub
        if sub_jump >= SUB_JUMP_THRESHOLD:
            ev = Event(
                "SUB_LAYER_ARRIVAL",
                state,
                extra={
                    "prev_sub": round(self.baseline_sub, 2),
                    "new_sub": round(current_sub, 2),
                    "sub_jump": round(sub_jump, 2),
                },
            )
            self.baseline_sub = current_sub
            self.baseline_bpm = current_bpm
            self.baseline_at = now
            self.last_event_at = now
            return ev

        # 7. Slow-drift hygiene — rotate baseline so a slow build over minutes
        #    can never accumulate into a spurious fire. Same idiom as
        #    KickSwapDetector step 9.
        self.baseline_sub = current_sub
        self.baseline_bpm = current_bpm
        self.baseline_at = now
        return None
