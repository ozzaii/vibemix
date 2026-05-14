# SPDX-License-Identifier: Apache-2.0
"""ReentryKickLandDetector — kick comes back near a downbeat (paired with
BreakdownKickKillDetector).

Pair contract (per Plan 17-03):
    - Constructor takes a ``BreakdownKickKillDetector`` instance — no globals.
    - Reads ``kill_detector.last_kill_at`` (the public attribute the kill
      detector stamps on every successful fire).
    - Tracks ``last_consumed_kill_at`` so each kill pairs with at most ONE
      re-entry; subsequent ticks pointing at the same kill timestamp are
      ignored until a fresh kill arrives.

Threat T-17-03-02 mitigation: ``bpm_confidence < 0.5`` short-circuits BEFORE
the downbeat-alignment gate. Phase 13's anti-hallucination contract forces
``beat_phase = 0.0`` when BPM lock is weak — without the confidence guard
that fabricated 0.0 would naively pass the alignment check (0.0 IS the
downbeat) and false-fire on every "no BPM lock" frame.

The detector is read-only on ``MusicState`` — Phase 3's single-writer
invariant is preserved (only ``state_refresh_loop._tick_once`` writes).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    KICK_REENTRY_BAR_TOLERANCE,
    KICK_REENTRY_MAX_AGE_S,
    KICK_REENTRY_SUB_FLOOR,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
    from vibemix.state.music_state import MusicState

# Phase 13 anti-hallucination guard threshold (mirror of mascot renderer's
# beat-locked-entry skip rule per Plan 13-04 Open Q 4). When BPM confidence
# falls below 0.5, ``beat_phase`` is fabricated (forced to 0.0) and MUST NOT
# be trusted by alignment-sensitive consumers.
_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT: float = 0.5


class ReentryKickLandDetector:
    """Watches for the kick coming back after a ``BreakdownKickKillDetector``
    fire. Each kill pairs with at most one re-entry.

    Fields are public-readable for tests + observability — never mutated by
    anything other than ``detect()`` (other than the constructor-injected
    ``kill_detector`` reference).
    """

    def __init__(self, kill_detector: "BreakdownKickKillDetector") -> None:
        # Dependency-injected pair — NO global state. Plan 05's GenreRouter
        # is responsible for wiring exactly one ReentryKickLandDetector per
        # active genre with the matching kill detector.
        self.kill_detector = kill_detector
        self.last_event_at: float = 0.0
        # Tracks the kill timestamp consumed by the most recent re-entry fire.
        # When ``kill_detector.last_kill_at == self.last_consumed_kill_at`` we
        # treat the kill as "already paired" and ignore subsequent ticks until
        # a fresh kill arrives (i.e. ``kill_detector.last_kill_at`` advances).
        self.last_consumed_kill_at: float = 0.0

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return an ``Event("REENTRY_KICK_LAND", ...)`` when the kick comes
        back near a downbeat after a recent BREAKDOWN_KICK_KILL, else
        ``None``.

        ``audio_buf`` is unused — the detector reads ``state.bands["sub"]``
        and ``state.beat_phase`` which the state-refresh writer already
        populated.
        """
        del audio_buf  # unused — see class docstring

        # 1. Silence gate.
        if state.rms < LOW_RMS:
            return None

        # 2. Pair contract: no kill ever → nothing to watch for.
        kill_at = self.kill_detector.last_kill_at
        if kill_at == 0.0:
            return None

        # 3. Already-consumed kill: each kill pairs with at most one re-entry.
        if kill_at == self.last_consumed_kill_at:
            return None

        # 4. Age check: kill too old → the breakdown effectively ended on its
        #    own, no specific re-entry moment worth calling out.
        kill_age = now - kill_at
        if kill_age > KICK_REENTRY_MAX_AGE_S:
            return None

        # 5. Per-type cooldown gate.
        if now - self.last_event_at < MIN_EVENT_GAP_PER_TYPE["REENTRY_KICK_LAND"]:
            return None

        # 6. Sub recovery gate (hysteresis above the kill floor).
        current_sub = state.bands.get("sub", 0.0)
        if current_sub < KICK_REENTRY_SUB_FLOOR:
            return None

        # 7. Threat T-17-03-02: refuse to trust beat_phase when BPM lock is
        #    weak. Phase 13 forces beat_phase=0.0 in that regime — without
        #    this short-circuit, the next gate would naively pass (0.0 IS
        #    the downbeat) and false-fire on every "no BPM lock" frame.
        if state.bpm_confidence < _BPM_CONFIDENCE_MIN_FOR_DOWNBEAT:
            return None

        # 8. Downbeat alignment: handle wrap-around. beat_phase ∈ [0, 1) so
        #    distance to the nearest downbeat is min(bp, 1 - bp) — beat_phase
        #    = 0.95 is 0.05 away from the next downbeat at 1.0/0.0.
        bp = state.beat_phase
        dist_to_downbeat = min(bp, 1.0 - bp)
        if dist_to_downbeat > KICK_REENTRY_BAR_TOLERANCE:
            return None

        # 9. Fire — stamp consumption + cooldown.
        ev = Event(
            "REENTRY_KICK_LAND",
            state,
            extra={
                "kill_age_s": round(kill_age, 1),
                "sub_at_reentry": round(current_sub, 2),
                "beat_phase": round(bp, 3),
            },
        )
        self.last_event_at = now
        self.last_consumed_kill_at = kill_at
        return ev
