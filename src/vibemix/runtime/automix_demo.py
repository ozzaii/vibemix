# SPDX-License-Identifier: Apache-2.0
"""Auto-mix demo reel — the owned-deck viral vertical, headless + deterministic.

This is the data-available home for the scar-20 transition clock. The LIVE co-host
has no playposition/cue data, but an OWNED mix does (a MiniDeck owns the frame
cursors; the demo supplies analyzed cues), so the clock first earns its keep here:
:func:`build_automix_reel` steps an owned transition across the fromDeck at 15 Hz
and emits the phrase-locked reaction beats — "ooh here it comes" (armed) → "AND
THERE IT IS, they mixed it in" (fading) → "clean, fully on the new one" (landed) —
the shareable "AI that GETS the drop" reel.

It is the deterministic CORE: this module returns a timeline of semantic reaction
cues, never audio or LLM text. The audio (MiniDeck playback), waveform (rank 14),
and voice (TTS) layers render this reel; the persona turns each cue key into a line.

The jump-cut distinction (rank 27) is folded in: a hard cut (begin >= end) skips
the FADING beat entirely, so the co-host never narrates a smooth blend over a slam.
"""
from __future__ import annotations

from dataclasses import dataclass

from vibemix.state.transition_clock import (
    GRID_HZ,
    TrackCues,
    TransitionMode,
    TransitionPhase,
    TransitionPlan,
    calculate_transition,
    transition_phase,
)


def reaction_cue(phase: TransitionPhase, *, is_cut: bool, center_start: bool) -> str:
    """The semantic reaction-cue key for a phase edge (NOT the spoken line).

    Distinguishes the three transition kinds the scar separates so the co-host
    never mislabels them: a smooth blend ("mixing_in"/"landed_clean"), a
    center-start full-volume slam (mode 4, "slam_in"), and a hard cut
    ("slammed_cut" — no blend beat ever fires for it).
    """
    if phase == TransitionPhase.ARMED:
        return "drop_incoming"
    if phase == TransitionPhase.FADING:
        return "slam_in" if center_start else "mixing_in"
    # LANDED
    return "slammed_cut" if is_cut else "landed_clean"


@dataclass(frozen=True)
class DemoBeat:
    """One phrase-locked reaction beat on the reel timeline."""

    t_sec: float  # fromDeck wall-time of the beat, on the 15 Hz grid
    from_playposition: float  # fromDeck position fraction [0..1] at the beat
    phase: TransitionPhase
    progress: float  # transition_progress [0..1] at the beat
    cue: str  # the reaction_cue key the persona renders into a line


@dataclass(frozen=True)
class AutomixReel:
    """The full deterministic reel: the frozen plan + its ordered reaction beats."""

    plan: TransitionPlan
    beats: tuple[DemoBeat, ...]

    @property
    def is_cut(self) -> bool:
        return self.plan.is_cut


def build_automix_reel(
    from_cues: TrackCues,
    to_cues: TrackCues,
    *,
    mode: TransitionMode = TransitionMode.FULL_INTRO_OUTRO,
    transition_sec: float = 10.0,
    arm_lead_sec: float = 2.0,
    fps: int = GRID_HZ,
) -> AutomixReel:
    """Build the deterministic reaction reel for an owned mix of two tracks.

    Computes the frozen transition plan once (scar §4.2 — lock at fade start), then
    steps the fromDeck position across the whole track at ``fps`` (15 Hz, the
    engine's real cadence) and records a :class:`DemoBeat` at each phase EDGE. The
    result is bit-identical for identical inputs (the "lands every time" guarantee).
    """
    plan = calculate_transition(
        from_cues, to_cues, mode=mode, transition_sec=transition_sec,
    )
    beats: list[DemoBeat] = []
    prev_phase = TransitionPhase.IDLE
    prev_progress = 0.0
    n_ticks = int(plan.from_duration_sec * fps) + 1
    for i in range(n_ticks + 1):
        t = i / fps
        frac = t / plan.from_duration_sec
        if frac > 1.0:
            frac = 1.0
        phase, prev_progress = transition_phase(
            plan, frac, prev_phase, prev_progress=prev_progress, arm_lead_sec=arm_lead_sec,
        )
        if phase > prev_phase:
            beats.append(
                DemoBeat(
                    t_sec=t,
                    from_playposition=frac,
                    phase=phase,
                    progress=prev_progress,
                    cue=reaction_cue(
                        phase, is_cut=plan.is_cut, center_start=plan.crossfader_start_center,
                    ),
                )
            )
        prev_phase = phase
    return AutomixReel(plan=plan, beats=tuple(beats))
