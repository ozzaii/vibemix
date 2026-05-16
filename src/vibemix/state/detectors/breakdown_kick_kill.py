# SPDX-License-Identifier: Apache-2.0
"""BreakdownKickKillDetector — kick disappears mid-track (filter sweep,
breakdown, drop preparation). Pairs with ``ReentryKickLandDetector`` via the
public ``last_kill_at`` attribute (Plan 17-03 Task 2).

Fires when ``state.bands["sub"]`` collapses below ``KICK_KILL_SUB_FLOOR`` AND
the drop magnitude (``baseline_sub - current_sub``) clears
``KICK_KILL_SUB_DROP_MIN``, while ``state.rms`` is still above ``LOW_RMS``
(the crucial "music is still playing" gate that distinguishes a breakdown
from a track-end). Two silence gates layer on top — RMS floor + Phase 6
silent-phase classification — mirroring ``KickDensityShiftDetector`` and the
v4 "trust the audio" anti-hallucination rule.

The two trailing-window-style fields (``baseline_sub``, ``baseline_at``) follow
the same idiom as ``SubLayerArrivalDetector`` / ``KickDensityShiftDetector``:
the baseline rotates every ~8s so a slow drift can never accumulate into a
spurious fire, and we never seed during a silence gate so a breakdown / pause
can't seed a "sub=0" baseline that the next audible tick falsely diffs against.

Pair contract (read by ``ReentryKickLandDetector`` — see Plan 17-03 Task 2):
    - ``last_kill_at: float`` — timestamp of the most recent fire (0.0 = never).
      Updated on every successful fire alongside ``last_event_at``. The sibling
      detector reads this attribute and only watches for a re-entry while the
      kill is fresh (``now - last_kill_at <= KICK_REENTRY_MAX_AGE_S``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    KICK_KILL_SUB_DROP_MIN,
    KICK_KILL_SUB_FLOOR,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.music_state import MusicState

# Trailing baseline window — symmetrical with ``SubLayerArrivalDetector`` and
# ``KickDensityShiftDetector`` so all Phase 17 trailing-window detectors share
# a consistent "recent past" horizon (matches BUILDUP_SLOPE_WINDOW_S = 8.0).
_BASELINE_WINDOW_SEC: float = 8.0


class BreakdownKickKillDetector:
    """Reads ``state.bands["sub"]`` + ``state.rms`` + ``state.phase``; never
    touches ``audio_buf`` (state-refresh loop already populated the bands).

    ``last_kill_at`` is PUBLIC by design — ``ReentryKickLandDetector`` consumes
    it as the dependency-injected pair contract. Keep it readable.
    """

    def __init__(self) -> None:
        self.last_event_at: float = 0.0
        # Public — read by ReentryKickLandDetector (Plan 17-03 Task 2).
        # 0.0 sentinel = no kill yet; first fire stamps it with ``now``.
        self.last_kill_at: float = 0.0
        self.baseline_sub: float | None = None
        self.baseline_at: float = 0.0

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return an ``Event("BREAKDOWN_KICK_KILL", ...)`` when the kick band
        collapses while the rest of the music keeps playing, else ``None``.

        ``audio_buf`` is unused — ``state.bands["sub"]`` is already populated
        by ``state_refresh_loop._tick_once``. Re-deriving from raw samples
        would duplicate the snapshot_features call the writer just did.
        """
        del audio_buf  # unused — see class docstring

        # 1. Silence gates — RMS floor AND Phase 6's silent classification.
        #    Either rejects BEFORE baseline seeding so a silence window can
        #    never seed a phantom "sub=0" baseline that the next audible tick
        #    would falsely diff against.
        if state.rms < LOW_RMS or state.phase == "silent":
            return None

        current_sub = state.bands.get("sub", 0.0)

        # 2. First call ever (or stale baseline) — seed + bail. We rotate the
        #    baseline every _BASELINE_WINDOW_SEC so a slow drift over minutes
        #    can never accumulate into a spurious fire.
        if self.baseline_sub is None or (now - self.baseline_at >= _BASELINE_WINDOW_SEC):
            seeded_first_time = self.baseline_sub is None
            # Cooldown gate must run BEFORE we accept a kill, but the
            # baseline-rotation tick on a non-firing call still updates the
            # anchor for future diffs. Process kill below if we've had a
            # baseline long enough; otherwise just seed.
            if seeded_first_time:
                self.baseline_sub = current_sub
                self.baseline_at = now
                return None
            # Stale baseline path — fall through to evaluate, then rotate.
            prev_baseline = self.baseline_sub

            # 3. Cooldown gate.
            if now - self.last_event_at < MIN_EVENT_GAP_PER_TYPE["BREAKDOWN_KICK_KILL"]:
                self.baseline_sub = current_sub
                self.baseline_at = now
                return None

            # 4. Kill detection: sub fell below floor AND the drop magnitude
            #    clears the anti-noise gate.
            if (
                current_sub < KICK_KILL_SUB_FLOOR
                and (prev_baseline - current_sub) >= KICK_KILL_SUB_DROP_MIN
            ):
                ev = Event(
                    "BREAKDOWN_KICK_KILL",
                    state,
                    extra={
                        "prev_sub": round(prev_baseline, 2),
                        "new_sub": round(current_sub, 2),
                        "sub_drop": round(prev_baseline - current_sub, 2),
                        "rms": round(state.rms, 3),
                    },
                )
                self.last_event_at = now
                self.last_kill_at = now  # PAIR contract — ReentryKickLand reads this
                self.baseline_sub = current_sub
                self.baseline_at = now
                return ev

            # 5. Slow-drift hygiene — rotate baseline so future diffs anchor
            #    against the recent past.
            self.baseline_sub = current_sub
            self.baseline_at = now
            return None

        # 6. Baseline still fresh (< _BASELINE_WINDOW_SEC old) — wait for it
        #    to age before evaluating diffs (avoids comparing partly-overlapping
        #    windows; same idiom as KickSwap step 5).
        return None
