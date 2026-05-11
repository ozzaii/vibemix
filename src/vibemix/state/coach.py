# SPDX-License-Identifier: Apache-2.0
"""AICoach — verbatim port of cohost_v4.py:1327-1433.

Three @staticmethod methods, no instance state. The class is a namespace
holding the per-event prompt-construction IP.

Phase 3 boundary: this module ships ``evidence_line`` (the grounded state
string), ``task_for_event`` (per-event instruction tail), and ``build_prompt``
(format wrapper). Phase 4's DJCoHostAgent.llm_node calls ``build_prompt`` and
feeds the result to Gemini Flash. Phase 10's prompt-template-matrix wraps it
in the full anti-slop stack (persona, system instruction, <silence/> short-
circuit).

LOAD-BEARING ANTI-HALLUCINATION INVARIANT (v4:1350-1351 comment):
    evidence_line does NOT include a ``phase=`` field. The RMS-derived phase
    label was priming the AI to invent kicks/drops when the audio was
    actually atmospheric. AI should hear the phase from the audio itself.
    v3 still had ``phase=``; v4 removed it. Do NOT reintroduce when porting.

TWO confidence thresholds (do not confuse):
    - 0.3 in evidence_line: the floor for quoting the track name.
      Below 0.3 the prompt prints ``track=unknown``.
    - 0.5 in EventDetector (``TRACK_CHANGE_MIN_CONFIDENCE``): the floor for
      firing a TRACK_CHANGE event.
"""

from __future__ import annotations

import time

from vibemix.state.event import Event
from vibemix.state.music_state import MusicState


class AICoach:
    """Builds the per-event prompt. Single persona is set at session-open via
    SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task."""

    @staticmethod
    def evidence_line(state: MusicState) -> str:
        e = []
        if state.audible:
            b = state.bands
            e.append(
                f"hearing[rms={state.rms:.3f} sub={b['sub']:.2f} low={b['low']:.2f} "
                f"mid={b['mid']:.2f} high={b['high']:.2f} bpm={state.bpm:.0f}]"
            )
        else:
            e.append("hearing[silent]")

        if state.audible_track and state.audible_track_confidence >= 0.3:
            e.append(f"track={state.audible_track!r}")
        else:
            e.append("track=unknown")

        e.append(f"deck={state.audible_deck}")
        e.append(f"set_time={int(state.set_seconds // 60)}:{int(state.set_seconds % 60):02d}")
        # phase= removed — RMS-based label was priming the AI to invent kicks/drops
        # when the audio was actually atmospheric. AI should hear the phase from audio.

        # Per-event ages so the AI can reason in seconds (e.g. "you held that 6s").
        now_ts = time.time()
        if state.phase_history:
            last_phase_t = state.phase_history[-1][0]
            e.append(f"phase_age={now_ts - last_phase_t:.1f}s")
        if state.track_history:
            last_track_t = state.track_history[-1][0]
            e.append(f"track_age={now_ts - last_track_t:.1f}s")

        recent_8s = [(age, label) for age, label in state.recent_moves if age <= 8.0]
        if recent_8s:
            # newest-first; show seconds-ago per move so AI can say "2s ago you killed the lows"
            recent_8s.sort(key=lambda x: x[0])
            mv = ", ".join(f"{age:.1f}s ago {label}" for age, label in recent_8s)
            e.append(f"recent_moves[8s]: {mv}")
        else:
            e.append("recent_moves[8s]: NONE")

        # Set-arc — coarse 2-minute energy shape so the AI can see set context
        if state.long_arc and len(state.long_arc) >= 2:
            e.append(f"set_arc[{len(state.long_arc) * 10}s]={state.long_arc}")

        # Phase history — last 3 transitions for continuity
        if state.phase_history:
            chain = []
            for i, (_, fr, to) in enumerate(state.phase_history[-4:]):
                if i == 0:
                    chain.append(fr)
                chain.append(to)
            e.append(f"phase_history: {'→'.join(chain)}")

        # Track history — last 3 audibly-confirmed titles
        if len(state.track_history) >= 2:
            titles = [repr(t) for _, t in state.track_history[-3:]]
            e.append(f"recent_tracks: {'→'.join(titles)}")

        return " | ".join(e)

    @staticmethod
    def task_for_event(ev: Event) -> str:
        t = ev.type
        if t == "KAAN_SPOKE":
            return (
                "Kaan just SPOKE — answer him directly, friend tone, 6-15 words. "
                "Not a music reaction."
            )
        if t == "MANUAL":
            return (
                "Kaan hit his trigger — react with substance to ONE concrete thing "
                "(audible event or recent move). 12-18 words."
            )
        if t == "TRACK_CHANGE":
            prev = ev.extra.get("prev_track")
            prev_clause = f" (was: {prev!r})" if prev else ""
            return (
                f"Track flipped{prev_clause}. React to the NEW track's vibe vs "
                "the previous — heavier, weirder, darker, more euphoric? "
                "12-18 words. Past tense."
            )
        if t == "PHASE":
            new = ev.extra.get("new_phase", "?")
            prev = ev.extra.get("prev_phase", "?")
            return (
                f"Phase shifted: {prev}→{new}. React to what the new section "
                "FEELS like, not the label. 10-14 words."
            )
        if t == "LAYER_ARRIVAL":
            return (
                "A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
                "riff, pad. Name what arrived and how it feels. 10-14 words."
            )
        if t == "MIX_MOVE":
            mv = ", ".join(ev.extra.get("moves", []))
            return (
                f"Trigger seed (do NOT quote): MIDI moves [{mv}]. "
                "Listen to the AUDIO and describe the SONIC EFFECT — how "
                "the music CHANGED in sound (bass dropped out, highs scooped, "
                "space opened up, vocal pierced through). Do NOT name "
                "faders/EQs/knobs/decks/controls. Past tense, 8-12 words. "
                "If the audio didn't actually change, output a single space "
                "to stay silent."
            )
        if t == "HEARTBEAT":
            return (
                "Steady stretch. ONE sharp observation about the SOUND right "
                "now — groove, texture, what the track is doing musically. "
                "8-12 words. Always reply with something fresh; don't go silent."
            )
        return "React naturally. 10-14 words."

    @staticmethod
    def build_prompt(ev: Event) -> str:
        evidence = AICoach.evidence_line(ev.state)
        task = AICoach.task_for_event(ev)
        return f"[{evidence} | event={ev.type}] {task}"
