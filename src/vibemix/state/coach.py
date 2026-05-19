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

# ---- Plan 19-02 — prompt diet caps + ack-eligible event set ----
# 4 chars/token proxy (cl100k empirical English baseline; project has no
# tiktoken dep). PROMPT_TOKEN_CAP_FULL is asserted via test on diet=False;
# the runtime invariant for diet=False is v4 byte-identity, NOT a cap check.
PROMPT_TOKEN_CAP_ACK = 800
PROMPT_TOKEN_CAP_FULL = 1500
# Events that are eligible for the diet path. The other event classes
# (PHASE / TRACK_CHANGE / MANUAL / DROP) keep the full payload — Gemini
# truly needs the 18s audio window + corpus footer + history fields to
# ground a substantive reaction on those classes.
ACK_ELIGIBLE_EVENTS: frozenset[str] = frozenset(
    {"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}
)


class AICoach:
    """Builds the per-event prompt. Single persona is set at session-open via
    SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task."""

    @staticmethod
    def evidence_line(
        state: MusicState,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
    ) -> str:
        """Build the grounded-state evidence string for the AI prompt.

        ``registry_snapshot`` (Phase 18 Plan 02): optional EvidenceRegistry
        snapshot dict ``{source: {key: (t1, t2, ...)}}``. When non-None AND
        non-empty, an ``evidence_corpus[ev=N,aud=M,mix=K]`` footer is
        appended — primes Gemini that grounded observations exist (Plan
        18-03 builds on this to bake the citation grammar). Default None
        preserves the v4 byte-identical output for all existing callers.
        """
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

        # Phase 18 Plan 02 — evidence-corpus footer. When the registry
        # snapshot is provided AND has at least one observation, append a
        # single-line summary of citable observation counts. This SEEDS
        # the grammar primer that Plan 18-03 expands in the prompt body —
        # Gemini sees "evidence corpus exists" and (with Plan 18-03's
        # grammar block) learns to cite against it. The default-None gate
        # below preserves the v4 byte-identical output for all existing
        # callers (Phase 4 invariant; HYPE_INTERMEDIATE prompt golden test
        # stays green).
        if registry_snapshot:
            ev_n = sum(len(v) for v in registry_snapshot.get("ev", {}).values())
            aud_n = sum(len(v) for v in registry_snapshot.get("aud", {}).values())
            mix_n = sum(len(v) for v in registry_snapshot.get("mix", {}).values())
            if (ev_n + aud_n + mix_n) > 0:
                e.append(f"evidence_corpus[ev={ev_n},aud={aud_n},mix={mix_n}]")

        return " | ".join(e)

    @staticmethod
    def _evidence_line_compact(state: MusicState) -> str:
        """Plan 19-02 — 5-field compact evidence_line for the diet path.

        Drops phase_age / track_age / set_arc / phase_history / recent_tracks
        from the full evidence_line (saves ~400 token-proxy chars on a
        maximally-populated state). The 6s audio window in DJCoHostAgent.
        llm_node is the safety net that recovers grounding for the dropped
        history fields.

        Branches are COPIES of the relevant evidence_line branches — kept
        separate so the v4-byte-identical evidence_line stays untouched.
        """
        e: list[str] = []
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

        recent_8s = [(age, label) for age, label in state.recent_moves if age <= 8.0]
        if recent_8s:
            recent_8s.sort(key=lambda x: x[0])
            mv = ", ".join(f"{age:.1f}s ago {label}" for age, label in recent_8s)
            e.append(f"recent_moves[8s]: {mv}")
        else:
            e.append("recent_moves[8s]: NONE")

        return " | ".join(e)

    @staticmethod
    def task_for_event(ev: Event) -> str:
        t = ev.type
        if t == "KAAN_SPOKE":
            return (
                "Kaan just SPOKE — answer him directly, friend tone. Short. "
                "Not a music reaction."
            )
        if t == "MANUAL":
            return (
                "Kaan hit his trigger — react with substance to ONE concrete thing "
                "(audible event or recent move)."
            )
        if t == "TRACK_CHANGE":
            prev = ev.extra.get("prev_track")
            prev_clause = f" (was: {prev!r})" if prev else ""
            return (
                f"Track flipped{prev_clause}. React to the NEW track's vibe vs "
                "the previous — heavier, weirder, darker, more euphoric?"
            )
        if t == "PHASE":
            new = ev.extra.get("new_phase", "?")
            prev = ev.extra.get("prev_phase", "?")
            return (
                f"Phase shifted: {prev}→{new}. React to what the new section "
                "FEELS like, not the label."
            )
        if t == "LAYER_ARRIVAL":
            return (
                "A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
                "riff, pad. Name what arrived and how it feels."
            )
        if t == "MIX_MOVE":
            mv = ", ".join(ev.extra.get("moves", []))
            return (
                f"Trigger seed (do NOT quote): MIDI moves [{mv}]. "
                "Listen to the AUDIO and describe the SONIC EFFECT — how "
                "the music CHANGED in sound (bass dropped out, highs scooped, "
                "space opened up, vocal pierced through). Do NOT name "
                "faders/EQs/knobs/decks/controls. "
                "If the audio didn't actually change, output a single space "
                "to stay silent."
            )
        if t == "HEARTBEAT":
            return (
                "Steady stretch. ONE sharp observation about the SOUND right "
                "now — groove, texture, what the track is doing musically. "
                "Always reply with something fresh; don't go silent."
            )
        return "React naturally."

    @staticmethod
    def build_prompt(
        ev: Event,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
        diet: bool = False,
    ) -> str:
        """Format the per-event prompt body.

        ``registry_snapshot`` (Phase 18 Plan 02) threads through to
        ``evidence_line`` for the evidence-corpus footer. Default None
        preserves the v4 byte-identical output.

        ``diet`` (Plan 19-02): when True, returns a compressed prompt for
        ack-eligible events — the compact 5-field evidence_line + the
        existing task tail, NO ``| event=TYPE`` tag, NO evidence-corpus
        footer. Saves ≥500ms TTFT on the four ack-eligible event classes
        (HEARTBEAT, MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE). Raises ValueError
        if the caller passes ``diet`` set to a truthy value on a non-ack
        event — fails loud at the call site to mask dispatch bugs.

        Default ``diet=False`` is the v4-byte-identical path; the diet
        branch is a NEW code path that does not affect existing callers.
        """
        if diet:
            if ev.type not in ACK_ELIGIBLE_EVENTS:
                raise ValueError(
                    f"diet path only valid for ACK_ELIGIBLE_EVENTS; got {ev.type}"
                )
            evidence = AICoach._evidence_line_compact(ev.state)
            task = AICoach.task_for_event(ev)
            return f"[{evidence}] {task}"
        evidence = AICoach.evidence_line(ev.state, registry_snapshot=registry_snapshot)
        task = AICoach.task_for_event(ev)
        return f"[{evidence} | event={ev.type}] {task}"
