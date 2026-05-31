# SPDX-License-Identifier: Apache-2.0
"""The drop-timing oracle — a deterministic 15 Hz transition clock.

This is the spine of the co-host's viral "DJ reaction" vertical. Ported clean-room
from Mixxx's ``AutoDJProcessor`` (scar dossier 20, GPLv2 — facts re-derived, no
source copied): it reduces a whole transition to three normalized fractions
(``from_fade_begin`` / ``from_fade_end`` / ``to_start``) plus one monotonic
``transition_progress`` scalar — the single number a co-host phrase-locks to so its
"the drop is coming / they just mixed it in / clean, fully on the new one" beats
land ON the mix instead of over it.

Design (the clean-leaf contract): this module owns NO audio and reads NO
``MusicState``. ``calculate_transition`` takes :class:`TrackCues` as a pure input —
the caller fills them from vibemix's own analyzer output (intro/outro markers +
the −60 dB first/last-sound bounds it already computes). The state-refresh loop
remains the only ``MusicState`` writer (Invariant #1); this is a pure predictor.

Key scars honored (``scars/20-autodj-transitions.md``):
  * 15 Hz is the resolution of reality — the drop is detected on a ~66.7 ms grid
    (``enginebuffer.cpp:52``); a sample-accurate callout is a lie (§4.1).
  * The plan is FROZEN at fade start — compute once when the fade arms, never
    re-plan mid-drop (``:1265`` ADJ_IDLE gate, §4.2).
  * Progress tracks TRACK position, not wall-clock — a backward seek freezes the
    mix (the ``step > 0`` guard); here progress is additionally MONOTONIC so a
    cited "they dropped it" never un-fires (§3.6 / §4.3).
  * ``fadeBeginPos >= fadeEndPos`` is a hard CUT, not a fade (§4.4) — never
    narrate a "smooth blend" over a jump-cut.
  * ``introEnd == introStart`` / ``outroStart == outroEnd`` are "unset" sentinels,
    not zero-length regions (§4.6).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

# --- scar constants (dossier 20 §2) -----------------------------------------
GRID_HZ: int = 15  # kPlaypositionUpdateRate (enginebuffer.cpp:52) — the clock tick
GRID_PERIOD_SEC: float = 1.0 / GRID_HZ  # ~66.7 ms detection granularity
SILENCE_THRESHOLD: float = 0.001  # 10**(-60/20), -60 dB first/last sound (analyzersilence.cpp:11)
TRANSITION_DEFAULT_SEC: float = 10.0  # kTransitionPreferenceDefault (:15)
KEEP_POSITION: float = -1.0  # sentinel "don't seek the toDeck" (:16)
MIN_TRACK_DURATION_SEC: float = 0.2  # kMinimumTrackDurationSec (:19)
MIN_FADE_SEC: float = MIN_TRACK_DURATION_SEC / 2.0  # fade-fit floor 0.1 s (:1555-1556)


class TransitionMode(IntEnum):
    """AutoDJ transition modes (autodjprocessor.h:166), persisted as the int."""

    FULL_INTRO_OUTRO = 0  # default — ride both cues, cut nothing
    FADE_AT_OUTRO_START = 1  # fade begins at outro start; trim outro tail if long
    FIXED_FULL_TRACK = 2  # play whole track incl. silence; fixed-seconds fade
    FIXED_SKIP_SILENCE = 3  # -60 dB bounds + fixed-seconds fade
    FIXED_START_CENTER_SKIP_SILENCE = 4  # mode 3 + crossfader-to-center slam


@dataclass(frozen=True)
class TrackCues:
    """One track's transition anchors, in SECONDS — the pure input to the clock.

    The caller derives these from vibemix's own analyzer. Markers are ``None`` when
    unmarked (NOT a real position). ``introEnd == introStart`` and
    ``outroStart == outroEnd`` are honored as "unset" sentinels by the resolution
    ladder. ``last_sound_sec`` defaults to the track end; ``first_sound_sec`` to 0.
    """

    duration_sec: float
    intro_start_sec: float | None = None
    intro_end_sec: float | None = None
    outro_start_sec: float | None = None
    outro_end_sec: float | None = None
    first_sound_sec: float = 0.0
    last_sound_sec: float | None = None  # None -> duration_sec (last audible default)


@dataclass(frozen=True)
class TransitionPlan:
    """The frozen plan: three normalized fractions + the live-progress inputs.

    All positions are fractions ``[0..1]`` of their own deck (fromDeck for the two
    fade points, toDeck for ``to_start``). Immutable — this is the "lock at fade
    start, never re-plan" contract (§4.2) made literal.
    """

    from_fade_begin: float  # fromDeck play-pos the fade STARTS — the "drop" trigger
    from_fade_end: float  # fromDeck play-pos the fade COMPLETES (old track muted)
    to_start: float  # toDeck cue point the incoming track starts from
    mode: TransitionMode
    transition_sec: float
    crossfader_start_center: bool  # mode 4 — slam xfader to center at fade start
    from_duration_sec: float
    to_duration_sec: float

    @property
    def is_cut(self) -> bool:
        """``fadeBeginPos >= fadeEndPos`` ⇒ a hard CUT, not a fade (§4.4)."""
        return self.from_fade_begin >= self.from_fade_end


def frame_to_seconds(frame_pos: float | None, sample_rate: int, rate_ratio: float = 1.0) -> float:
    """Frame index → seconds, rate-aware (§3.1). A sped-up track has earlier cues.

    ``rate_ratio`` is the playback speed (1.0 = normal); dividing by it shifts every
    cue the same way the engine does, so callouts stay synced when tempo is bent.
    """
    if sample_rate <= 0 or frame_pos is None or frame_pos < 0 or rate_ratio <= 0:
        return 0.0
    return frame_pos / sample_rate / rate_ratio


def snap_to_update_grid(pos_sec: float) -> float:
    """Floor a time to the 15 Hz play-position grid (§4.1) — the determinism floor.

    Two instants inside the same ~66.7 ms cell collapse to the cell start, so the
    drop trigger is detected on the same grid the engine actually updates on.
    """
    return math.floor(pos_sec * GRID_HZ) / GRID_HZ


# --- cue-resolution fallback ladder (§3.2) ----------------------------------
# A marker is usable only when present AND within the track. None / out-of-range
# falls through the ladder, exactly as the AutoDJ getters do.
def _valid(x: float | None, duration: float) -> bool:
    return x is not None and 0.0 <= x <= duration


def _last_sound(c: TrackCues) -> float:
    return c.last_sound_sec if c.last_sound_sec is not None else c.duration_sec


def _intro_start(c: TrackCues, tt: float) -> float:
    if _valid(c.intro_start_sec, c.duration_sec):
        return float(c.intro_start_sec)  # type: ignore[arg-type]
    fs = c.first_sound_sec
    if not _valid(c.intro_end_sec, c.duration_sec):
        return fs
    ie = float(c.intro_end_sec)  # type: ignore[arg-type]
    return ie - tt if tt >= 0.0 else ie


def _intro_end(c: TrackCues, tt: float) -> float:
    if not _valid(c.intro_end_sec, c.duration_sec):
        return _intro_start(c, tt)  # zero-length intro when unset
    return float(c.intro_end_sec)  # type: ignore[arg-type]


def _outro_start(c: TrackCues, tt: float) -> float:
    if not _valid(c.outro_start_sec, c.duration_sec):
        return _outro_end(c, tt)  # zero-length outro when unset
    return float(c.outro_start_sec)  # type: ignore[arg-type]


def _outro_end(c: TrackCues, tt: float) -> float:
    if not _valid(c.outro_end_sec, c.duration_sec):
        ls = _last_sound(c)
        if not _valid(c.outro_start_sec, c.duration_sec):
            return ls
        os_ = float(c.outro_start_sec)  # type: ignore[arg-type]
        if tt >= 0.0 and ls > os_:
            cand = os_ + tt
            return cand if cand < ls else ls
        return os_
    return float(c.outro_end_sec)  # type: ignore[arg-type]


def _use_fixed_fade_time(
    *, to_cues: TrackCues, tt: float, from_sec: float, fade_end_sec: float,
    to_start_sec: float, to_fade_begin: float, to_fade_end: float,
) -> tuple[float, float, float]:
    """Fixed-seconds fade fitting (§3.5). Returns (from_begin, from_end, to_start) in sec.

    ``tt <= 0`` is the jump-cut / insert-silence branch: begin == end (instant cut),
    and a negative ``tt`` shifts the incoming start earlier to leave a silent gap.
    """
    if tt > 0.0:
        to_outro_start = to_fade_begin
        if to_fade_begin >= to_fade_end:  # toDeck outro undefined
            to_outro_start -= tt
        if to_outro_start <= to_start_sec + MIN_TRACK_DURATION_SEC:  # past toDeck outro
            end = _outro_end(to_cues, tt)
            if end <= to_start_sec + MIN_TRACK_DURATION_SEC:
                end = to_cues.duration_sec  # last resort: track end
            to_outro_start = (end - to_start_sec) / 2.0 + to_start_sec  # half remaining
        ttime = min(to_outro_start - to_start_sec, tt)
        if ttime < MIN_FADE_SEC:
            ttime = MIN_FADE_SEC
        return max(fade_end_sec - ttime, from_sec), fade_end_sec, to_start_sec
    # tt <= 0 : jump-cut (==0) or insert silence (<0)
    return fade_end_sec, fade_end_sec, to_start_sec + tt


def calculate_transition(
    from_cues: TrackCues,
    to_cues: TrackCues,
    *,
    mode: TransitionMode = TransitionMode.FULL_INTRO_OUTRO,
    transition_sec: float = TRANSITION_DEFAULT_SEC,
    from_playposition: float = 0.0,
    to_playposition: float = 0.0,
    seek_to_start: bool = True,
) -> TransitionPlan:
    """Build the frozen transition plan (§3.4) — the heart of the engine.

    Produces the fromDeck fade points + the toDeck start cue as ``[0..1]``
    fractions, dispatching on ``mode``. Mirrors ``AutoDJProcessor::calculateTransition``
    clean-room. Runs once, at arm time (the caller must not recompute mid-fade).
    """
    tt = transition_sec
    from_dur = max(from_cues.duration_sec, MIN_TRACK_DURATION_SEC)
    to_dur = max(to_cues.duration_sec, MIN_TRACK_DURATION_SEC)

    outro_end = min(_outro_end(from_cues, tt), from_dur)
    outro_start = _outro_start(from_cues, tt)
    from_pos = from_dur * from_playposition
    # Already past outroStart (enabled mid-track) -> anchor the outro here.
    if from_pos > outro_start:
        outro_start = from_pos
        if from_pos > outro_end:
            outro_end = min(outro_start + abs(tt), from_dur)
    outro_length = outro_end - outro_start

    # toDeck's OWN next-outro so this transition finishes before it.
    to_fade_end = _outro_end(to_cues, tt)
    to_outro_start = _outro_start(to_cues, tt)
    if to_fade_end == to_outro_start:  # toDeck outro undefined
        to_outro_start -= tt
    to_fade_begin = to_outro_start

    to_pos = to_dur * to_playposition
    intro_start = _intro_start(to_cues, tt)
    intro_end = _intro_end(to_cues, tt)
    to_start = to_pos
    if seek_to_start or to_pos >= to_fade_begin:
        to_start = intro_start  # re-cue to intro start

    intro_length = 0.0
    if to_start < intro_end and intro_start < intro_end:
        intro_length = intro_end - to_start
        if (
            intro_length > 2.0 * (intro_end - intro_start)
            and intro_length > (intro_end - intro_start) + tt
            and intro_length > outro_length
        ):
            intro_length = 0.0  # absurd reverse-seek guard

    crossfader_start_center = False
    from_begin = from_end = 0.0

    if mode == TransitionMode.FULL_INTRO_OUTRO:
        tlen = intro_length
        if outro_length > 0.0 and (tlen <= 0.0 or tlen > outro_length):
            tlen = outro_length
        if tlen > 0.0:
            if to_start + tlen > to_fade_begin:
                tlen = to_fade_begin - to_start
            from_begin, from_end, to_start = outro_end - tlen, outro_end, to_start
        else:
            from_begin, from_end, to_start = _use_fixed_fade_time(
                to_cues=to_cues, tt=tt, from_sec=from_pos, fade_end_sec=outro_end,
                to_start_sec=to_start, to_fade_begin=to_fade_begin, to_fade_end=to_fade_end,
            )

    elif mode == TransitionMode.FADE_AT_OUTRO_START:
        tlen = outro_length
        if tlen > 0.0:
            if intro_length > 0.0 and outro_length > intro_length:
                tlen = intro_length  # cut the outro tail
            if to_start + tlen > to_fade_begin:
                tlen = to_fade_begin - to_start
            from_begin, from_end, to_start = outro_start, outro_start + tlen, to_start
        elif intro_length > 0.0:  # outro unmarked, intro marked
            from_begin, from_end, to_start = outro_end - intro_length, outro_end, to_start
        else:
            from_begin, from_end, to_start = _use_fixed_fade_time(
                to_cues=to_cues, tt=tt, from_sec=from_pos, fade_end_sec=outro_end,
                to_start_sec=to_start, to_fade_begin=to_fade_begin, to_fade_end=to_fade_end,
            )

    elif mode in (
        TransitionMode.FIXED_SKIP_SILENCE,
        TransitionMode.FIXED_START_CENTER_SKIP_SILENCE,
    ):
        crossfader_start_center = mode == TransitionMode.FIXED_START_CENTER_SKIP_SILENCE
        to_fade_begin = _last_sound(to_cues)
        if seek_to_start or to_pos >= to_fade_begin:
            to_start = to_cues.first_sound_sec
        else:
            to_start = to_pos
        from_begin, from_end, to_start = _use_fixed_fade_time(
            to_cues=to_cues, tt=tt, from_sec=from_pos, fade_end_sec=_last_sound(from_cues),
            to_start_sec=to_start, to_fade_begin=to_fade_begin, to_fade_end=to_fade_end,
        )

    else:  # FIXED_FULL_TRACK (and the default fallthrough)
        to_fade_begin = to_dur
        to_start = 0.0 if (seek_to_start or to_pos >= to_fade_begin) else to_pos
        from_begin, from_end, to_start = _use_fixed_fade_time(
            to_cues=to_cues, tt=tt, from_sec=from_pos, fade_end_sec=from_dur,
            to_start_sec=to_start, to_fade_begin=to_fade_begin, to_fade_end=to_fade_end,
        )

    # Normalize to fractions; clamp fadeBegin to 1.0 (:1501-1513).
    from_begin_f = min(from_begin / from_dur, 1.0)
    from_end_f = from_end / from_dur
    to_start_f = to_start / to_dur
    return TransitionPlan(
        from_fade_begin=from_begin_f,
        from_fade_end=from_end_f,
        to_start=min(max(to_start_f, 0.0), 1.0),
        mode=mode,
        transition_sec=tt,
        crossfader_start_center=crossfader_start_center,
        from_duration_sec=from_dur,
        to_duration_sec=to_dur,
    )


def step_progress(plan: TransitionPlan, from_playposition: float, prev_progress: float) -> float:
    """Advance ``transition_progress`` ∈ [0,1] for one tick (§3.6), monotonic.

    Progress is linear in the fromDeck's play-position across the fade window, NOT
    in wall-clock — so a forward seek accelerates the mix and a backward seek
    freezes it. Unlike Mixxx's raw scalar this is MONOTONIC (``max`` with the prior
    value): a cited "they dropped it" must never un-fire when the DJ nudges back.
    Before the trigger it is 0.0 (reset); at/after the fade end it clamps to 1.0; a
    hard cut (begin >= end) is 1.0 once the cut point is reached, else 0.0.
    """
    span = plan.from_fade_end - plan.from_fade_begin
    if span <= 0.0:  # hard cut — no ramp
        return 1.0 if from_playposition >= plan.from_fade_begin else max(prev_progress, 0.0)
    raw = (from_playposition - plan.from_fade_begin) / span
    raw = min(max(raw, 0.0), 1.0)
    return max(prev_progress, raw)


def drop_eta_seconds(plan: TransitionPlan, from_playposition: float) -> float:
    """Seconds until the fade trigger (negative once the drop has begun).

    The "ooh, here it comes" countdown the co-host phrase-locks anticipation to —
    distance from the current fromDeck position to ``from_fade_begin``, in seconds.
    """
    return (plan.from_fade_begin - from_playposition) * plan.from_duration_sec


class TransitionPhase(IntEnum):
    """The co-host's phrase-lockable beats over a transition — a monotonic ladder.

    Ordered so ``max(prev, raw)`` enforces "a cited beat never un-fires" and the
    caller fires an event exactly when ``phase > prev_phase``.
    """

    IDLE = 0  # nothing to say (drop too far out, or no transition)
    ARMED = 1  # "ooh, here it comes" — within the anticipation lead
    FADING = 2  # "AND THERE IT IS — they mixed it straight in" — the mix is live
    LANDED = 3  # "clean. fully on the new one now." — old deck muted


# Never arm more than this far out — a "drop incoming" callout 10 s early reads as
# cringe, not prescience (the §4.1 15 Hz-grid spirit: anticipation is ~1 bar, not a
# wall-clock countdown). The caller passes ~1 bar from the BeatGrid, capped here.
ARM_LEAD_SEC_MAX: float = 8.0


def transition_phase(
    plan: TransitionPlan,
    from_playposition: float,
    prev_phase: TransitionPhase,
    *,
    prev_progress: float = 0.0,
    arm_lead_sec: float = 2.0,
) -> tuple[TransitionPhase, float]:
    """The armed→fading→landed state machine for one 15 Hz tick.

    Returns ``(phase, progress)``. ``phase`` is monotonic — it never regresses
    below ``prev_phase`` (a backward seek freezes the beat, it does not rewind a
    cited callout). The caller fires a ``TransitionTimingEvent`` exactly when the
    returned ``phase`` exceeds ``prev_phase``. A hard cut goes ARMED→LANDED with no
    FADING ramp (it is a cut, not a blend — never narrate a smooth fade over it).

    ``arm_lead_sec`` is the anticipation window in seconds (the caller passes ~1
    bar from the BeatGrid); it is clamped to :data:`ARM_LEAD_SEC_MAX` so a far-off
    drop never arms early.
    """
    progress = step_progress(plan, from_playposition, prev_progress)
    if progress >= 1.0:
        raw = TransitionPhase.LANDED
    elif progress > 0.0:
        raw = TransitionPhase.FADING
    else:
        eta = drop_eta_seconds(plan, from_playposition)
        lead = min(arm_lead_sec, ARM_LEAD_SEC_MAX)
        raw = TransitionPhase.ARMED if 0.0 <= eta <= lead else TransitionPhase.IDLE
    phase = max(prev_phase, raw)
    return phase, progress
