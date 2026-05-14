# SPDX-License-Identifier: Apache-2.0
"""PhraseBoundaryDetector — fires on a downbeat that closes an 8/16/32-bar
phrase, the structural unit DJs use to plan blends.

The detector is the highest-level Wave-2 structural detector — it lets the
AI react to "we're at the END of a phrase" not just "the kick just changed".
Pairs with the kick-side detectors from Plans 17-02 + 17-03 to give the AI
the FULL grammar of dance-music structure (groove → phrase end → breakdown
→ re-entry).

Self-correction protocol (per Plan 17-04 plan body Step 3 + threat T-17-04-04
accept disposition):
    The detector accepts an OPTIONAL ``BreakdownKickKillDetector`` instance
    via the constructor. When it observes a NEW kill (a fresh
    ``kill_detector.last_kill_at`` since the last tick), it resets its
    ``lock_anchor_t`` to the kill timestamp. Rationale: the breakdown IS
    where the next phrase starts — there's no phrase boundary "before" the
    post-breakdown re-entry by definition. Plan 05's GenreRouter MAY pass
    ``None`` for genres where kick-kill self-correction isn't relevant
    (disco / pop / etc.).

Same DI idiom as ``ReentryKickLandDetector``: read the kill detector's
public ``last_kill_at`` attribute on every tick, no observer pattern, no
event bus, no globals.

Anti-hallucination guard (T-17-04-01 mitigation):
    Two independent confidence gates:
    1. ``state.bpm_confidence < BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`` (=0.5)
       short-circuits BEFORE any seeding or boundary check. Phase 13's
       contract forces ``beat_phase = 0.0`` when BPM lock is weak — without
       this gate that fabricated 0.0 would naively pass the alignment check
       and false-fire on every "no BPM lock" frame.
    2. ``lock_downbeat_phase`` requires its own internal confidence ≥ 0.5
       to seed. Two independent gates (state-level + lock-level).

The detector is read-only on ``MusicState`` (Phase 3 single-writer invariant
preserved — only ``state_refresh_loop._tick_once`` writes inside
``state._lock``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    BPM_CONFIDENCE_MIN_FOR_DOWNBEAT,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
    PHRASE_BOUNDARY_BAR_TOLERANCE,
    PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES,
)
from vibemix.state.detectors._phrase_dsp import (
    estimate_phrase_length_bars,
    lock_downbeat_phase,
)
from vibemix.state.event import Event

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
    from vibemix.state.music_state import MusicState

# Lock-seeding window — 8 seconds of audio is enough for the band-limited
# autocorr to lock at slow BPM (60 BPM = 1 beat/sec → 8 beats in window =
# minimum useful peak count). Aligned with the autocorr's max_lag_seconds=4
# default in `_phrase_dsp.py` so we sample double the longest lag we test.
_LOCK_WINDOW_SEC: float = 8.0


class PhraseBoundaryDetector:
    """Stateful detector — keeps the lock anchor (timestamp + locked BPM) so
    consecutive ``.detect()`` calls compute bar_index relative to the lock,
    NOT relative to a wall-clock zero. Re-locks only when ``state.bpm``
    changes materially, OR on first call, OR after observing a fresh
    ``BREAKDOWN_KICK_KILL`` from the injected kill detector.

    Fields are public-readable for tests + observability — never mutated by
    anything other than ``detect()``.
    """

    def __init__(self, kill_detector: "BreakdownKickKillDetector | None" = None) -> None:
        # Optional dep — None is valid (Plan 05's GenreRouter MAY pass None
        # for genres where kick-kill self-correction isn't relevant).
        self.kill_detector = kill_detector
        self.last_event_at: float = 0.0
        # The BPM at which we last seeded the downbeat lock (0.0 = no lock).
        self.locked_bpm: float = 0.0
        # Session-time of the last lock (or kill self-correct).
        self.lock_anchor_t: float = 0.0
        # Current phrase length in bars (default 16 — overridden by
        # estimate_phrase_length_bars on every re-lock).
        self.phrase_length_bars: int = 16
        # Tracks kill_detector.last_kill_at to detect NEW kills since the
        # last tick (idempotency: each kill resets the counter at most once).
        self.last_observed_kill_at: float = 0.0
        # bar_index of the most recent fire (for the min-bars-between-fires
        # gate). -999 sentinel = no fires yet (so the first eligible boundary
        # is never blocked by an undefined-prior-fire comparison).
        self.last_fire_bar_index: int = -999

    def detect(
        self,
        state: "MusicState",
        audio_buf: "AudioBuffer | None",
        now: float,
    ) -> Event | None:
        """Return an ``Event("PHRASE_BOUNDARY", ...)`` when a downbeat closes
        an 8/16/32-bar phrase, else ``None``.

        Order of gates is load-bearing:
            1. Silence gate — rejects BEFORE any lock work so a silence tick
               doesn't waste an autocorr cycle.
            2. BPM confidence gate — rejects BEFORE seeding so a fake lock
               can't anchor the phrase counter.
            3. Self-correction observation — resets the anchor on a fresh
               kill BEFORE any boundary check (the kill IS the new lock).
            4. Lock seeding — only when no anchor OR BPM changed materially.
            5. Bar arithmetic + min-bars-between-fires + cooldown + boundary
               check.

        ``audio_buf=None`` is a graceful no-op (Plan 17-05 contract — when
        EventDetector is constructed without an audio_buf the lock-seeding
        step has no samples to work with; detector silently can't fire,
        no exception, no log per T-17-05 threat note). The kill-driven
        self-correction step still runs because it doesn't need samples —
        it just observes ``kill_detector.last_kill_at``.
        """
        # 1. Silence gate (RMS floor + Phase 6 silent classification).
        if state.rms < LOW_RMS or state.phase == "silent":
            return None

        # 1b. audio_buf-required gate (Plan 17-05). The lock-seeding step
        #     needs raw samples for autocorr; without an audio_buf there's
        #     nothing to seed the downbeat lock with. Graceful no-op.
        if audio_buf is None:
            return None

        # 2. BPM confidence gate — anti-hallucination per T-17-04-01.
        #    Refuse to do anything (including seeding) if the lock can't
        #    be trusted. Phase 13 fabricates beat_phase=0.0 in that regime;
        #    without this guard the boundary check would naively accept that
        #    fabricated value and false-fire on every weak-lock frame.
        if state.bpm_confidence < BPM_CONFIDENCE_MIN_FOR_DOWNBEAT:
            return None

        # 3. Self-correction step — observe a NEW kill (kill_detector.last_kill_at
        #    advanced since our last_observed_kill_at). Reset the anchor to
        #    the kill timestamp; next-tick is the start of the new phrase,
        #    not a boundary.
        if self.kill_detector is not None:
            kill_at = self.kill_detector.last_kill_at
            if kill_at > self.last_observed_kill_at and kill_at > 0.0:
                self.lock_anchor_t = kill_at
                self.last_observed_kill_at = kill_at
                # Reset the "last fire bar index" so post-kill fires aren't
                # blocked by the pre-kill counter. The kill is the structural
                # restart — the new phrase has no prior fires.
                self.last_fire_bar_index = -999
                return None

        # 4. Lock seeding — first call ever OR BPM changed materially → re-lock.
        if self.lock_anchor_t == 0.0 or state.bpm != self.locked_bpm:
            n_samples = int(audio_buf._sr * _LOCK_WINDOW_SEC)
            samples = audio_buf.snapshot(n_samples)
            _phase, conf = lock_downbeat_phase(samples, state.bpm, audio_buf._sr)
            # Don't seed on a fake lock — the lock-internal confidence floor
            # mirrors the state-level bpm_confidence floor.
            if conf < BPM_CONFIDENCE_MIN_FOR_DOWNBEAT:
                return None
            self.lock_anchor_t = now
            self.locked_bpm = state.bpm
            # Re-estimate phrase length from the energy curve.
            self.phrase_length_bars = estimate_phrase_length_bars(
                state.energy_curve, state.bpm
            )
            return None

        # 5. Bar arithmetic — beats since lock, divided by 4 = bars.
        #    Add a small epsilon (0.5 ms worth of beats — well under any real
        #    beat period) before truncation so float drift can't silently
        #    lose the boundary tick. Without this, a 16-bar interval computed
        #    from 1000.0 → 1029.538... yields beats=63.99999999999977 →
        #    bar_index=15 instead of 16.
        beats_since_lock = (now - self.lock_anchor_t) * state.bpm / 60.0
        bar_index = int(beats_since_lock / 4.0 + 1e-6)

        # 5a. Min-bars-between-fires gate — bar count, not seconds. Protects
        #     against fast-BPM double-fire even if wall-clock cooldown is
        #     somehow cleared / not engaged (e.g. genre-switch reset).
        if bar_index - self.last_fire_bar_index < PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES:
            return None

        # 5b. Wall-clock cooldown gate.
        if now - self.last_event_at < MIN_EVENT_GAP_PER_TYPE["PHRASE_BOUNDARY"]:
            return None

        # 5c. Boundary check — bar_index is on a phrase boundary IF
        #     bar_index > 0 AND bar_index % phrase_length_bars == 0.
        if bar_index > 0 and bar_index % self.phrase_length_bars == 0:
            # Beat-phase alignment — we're at the right BAR; verify we're
            # also on its DOWNBEAT (within ±PHRASE_BOUNDARY_BAR_TOLERANCE
            # of beat_phase 0.0, with wrap-around at 1.0 ≡ 0.0).
            bp = state.beat_phase
            dist = min(bp, 1.0 - bp)
            if dist > PHRASE_BOUNDARY_BAR_TOLERANCE:
                return None
            # Fire.
            ev = Event(
                "PHRASE_BOUNDARY",
                state,
                extra={
                    "phrase_length_bars": self.phrase_length_bars,
                    "bar_index_in_phrase": bar_index,
                    "beat_phase": round(bp, 3),
                    "bpm": round(state.bpm, 1),
                },
            )
            self.last_event_at = now
            self.last_fire_bar_index = bar_index
            return ev

        return None
