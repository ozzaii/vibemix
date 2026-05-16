# SPDX-License-Identifier: Apache-2.0
"""KickDensityShiftDetector — kick-pattern regime change.

Fires when ``state.onset_density`` (onsets/sec, populated by
``state_refresh_loop`` from ``feats["onsets_per_sec"]``) changes by at least
``KICK_DENSITY_SHIFT_DELTA`` versus a trailing ~8s baseline. The moment
captured: a DJ shifting between half-time, 4-on-floor, and broken kick
patterns — structural changes the v4 ``LAYER_ARRIVAL`` detector misses
because its mid/high band-share signature is insensitive to onset count.

Genre-tuning note (per CONTEXT G-followup-1): the 1.5 onsets/sec threshold is
the smallest robustly-detectable shift between any two of the three canonical
regimes (half-time ≈ 1.0/sec, 4-on-floor techno ≈ 2.5/sec, hard tek
4-on-floor ≈ 5.0/sec). Plan 06's tuning harness may later split this into
per-genre thresholds via the ``GenreRouter`` registry Plan 05 wires up; for
v1.0 a single threshold suffices and avoids over-fitting to limited live
data.

The silent-phase gate (``state.phase == "silent"``) is layered on top of the
RMS gate because Phase 6 owns the authoritative "music isn't truly playing"
classification — RMS may briefly exceed ``LOW_RMS`` during a transient ambient
spike that Phase 6's hysteresis correctly classifies as silent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    KICK_DENSITY_SHIFT_DELTA,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# Trailing baseline window — matches SubLayerArrivalDetector so all Phase 17
# trailing-window detectors share a consistent "recent past" horizon
# (symmetrical with BUILDUP_SLOPE_WINDOW_S).
_BASELINE_WINDOW_SEC: float = 8.0


class KickDensityShiftDetector:
    """Stateful detector — keeps the prior density + the time it was captured.

    Fields are public-readable for tests + observability — never mutated by
    anything other than ``detect()``.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        self.baseline_density: float | None = None
        self.baseline_at: float = 0.0

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return an ``Event("KICK_DENSITY_SHIFT", ...)`` on regime jumps,
        else ``None``.

        ``audio_buf`` is unused — ``state.onset_density`` is already populated
        by ``state_refresh_loop``. Accepted as a parameter for API symmetry
        with the other Phase 17 detectors.
        """
        del audio_buf  # unused — reads state.onset_density directly

        # 1. Silence gates — RMS floor AND Phase 6's silent-phase classification.
        #    Either rejects before baseline seeding (so a transient ambient
        #    spike during silence cannot seed a phantom baseline).
        if state.rms < LOW_RMS or state.phase == "silent":
            return None

        current_density = state.onset_density

        # 2. First call ever — seed baseline + bail.
        if self.baseline_density is None:
            self.baseline_density = current_density
            self.baseline_at = now
            return None

        # 3. Window guard — baseline must be at least _BASELINE_WINDOW_SEC old
        #    before we treat the comparison as "current vs trailing-8s
        #    baseline". Returning None without rotating keeps the original
        #    baseline intact for the next eligible tick.
        if now - self.baseline_at < _BASELINE_WINDOW_SEC:
            return None

        # 4. Cooldown gate. Like SubLayerArrivalDetector, we do NOT rotate
        #    baseline on cooldown — keeping the pre-fire baseline lets the
        #    post-cooldown tick still see the shift if it's persistent.
        if now - self.last_event_at < MIN_EVENT_GAP_PER_TYPE["KICK_DENSITY_SHIFT"]:
            return None

        # 5. Signed delta — preserve direction in extra so the AI prompt
        #    can describe "kick pattern doubled" vs "kick pattern halved".
        delta = current_density - self.baseline_density
        abs_delta = abs(delta)
        if abs_delta >= KICK_DENSITY_SHIFT_DELTA:
            ev = Event(
                "KICK_DENSITY_SHIFT",
                state,
                extra={
                    "prev_density": round(self.baseline_density, 2),
                    "new_density": round(current_density, 2),
                    "delta": round(delta, 2),
                },
            )
            self.baseline_density = current_density
            self.baseline_at = now
            self.last_event_at = now
            return ev

        # 6. Slow-drift hygiene — rotate baseline so a 10-minute slow drift
        #    can never accumulate into a spurious fire. Same idiom as
        #    KickSwapDetector step 9.
        self.baseline_density = current_density
        self.baseline_at = now
        return None
