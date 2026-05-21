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

        # Phase 59-04 (DECK-01) — deck-state block, the grounded way. ADDITIVE +
        # gated so an EMPTY deck_state (decks={}) emits NOTHING and the v4
        # evidence_line stays byte-identical (Pitfall 5 golden-equivalence — the
        # 59-01 baseline test stays green). Once the poller populates decks, show
        # the resolved decks (camelot present + confidence >= 0.3, mirroring the
        # track= gate); decks present but none resolved → honest decks=unknown.
        # NOT added to _evidence_line_compact — deck-state is substantive
        # full-payload, out of the diet/ack path (RESEARCH line 243).
        if state.deck_state.decks:
            resolved = {
                s: d
                for s, d in state.deck_state.decks.items()
                if d.camelot and d.confidence >= 0.3
            }
            if resolved:
                parts = [
                    f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm"
                    for s, d in sorted(resolved.items())
                ]
                e.append("decks[" + " | ".join(parts) + "]")
            else:
                e.append("decks=unknown")

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
                f"A move just landed [{mv}]. The recent_moves[8s] ages tell you HOW "
                "MANY SECONDS AGO it hit — that moment is a CHANGE point in the audio. "
                "Put your ears RIGHT THERE and listen to the before→after: what shifted "
                "in the SOUND (energy, low-end, space, tension, how the blend sits). "
                "Ground your feedback on what that change DID to the mix — did it land, "
                "muddy it, open it up — and if it needs a fix, give the fix. Name the "
                "EQ, filter, or move if that's genuinely what's worth flagging — you're "
                "a pro, you decide what matters this moment. If the change did nothing "
                "notable, give your read on how the mix is sitting overall, or output a "
                "single space to stay silent."
            )
        if t == "HEARTBEAT":
            return (
                "Steady stretch. ONE sharp observation about the SOUND right "
                "now — groove, texture, what the track is doing musically. "
                "Always reply with something fresh; don't go silent."
            )
        # Phase 60-04 (HARMONIC-01) — CITED, NARRATE-ONLY clash fragment. The
        # verdict is the system's (is_clash() in the detector), NOT the LLM's.
        # The fragment hands the pre-decided clash + both decks' keys + the
        # pre-computed semitone count, instructs the model to CITE BOTH keys
        # exactly, and FORBIDS it from inventing a key or computing intervals.
        # The existence-only CitationLinter (Phase 59, key source) strips the
        # WHOLE turn if the model fabricates a [key:...] the registry never
        # observed — the anti-slop guarantee is structural, not prompt-trust.
        # Phase 61 owns the persona voice; this phase keeps to the grounded FACTS.
        if t == "KEY_CLASH":
            a_side = ev.extra.get("a_side", "A")
            a_cam = ev.extra.get("a_camelot", "?")
            b_side = ev.extra.get("b_side", "B")
            b_cam = ev.extra.get("b_camelot", "?")
            semis = ev.extra.get("semitones")
            # Guard the count against None (cross-letter pairs carry no semitone
            # number) — say "clashing" without interpolating a None.
            gap = (
                f"{semis} semitone{'s' if semis != 1 else ''} apart"
                if semis is not None
                else "clashing on the melodic overlap"
            )
            return (
                f"HARMONIC CLASH confirmed by the system (you do NOT decide this): "
                f"deck {a_side} is {a_cam}, deck {b_side} is {b_cam} — {gap}, "
                f"they're fighting where the two decks' melodies overlap. Tell Kaan "
                f"the move in DJ verbs (kill {b_side}'s mids, cut on the drop, "
                f"filter one out, don't ride the pads). Cite BOTH keys exactly: "
                f"[key:{a_side}:{a_cam}] and [key:{b_side}:{b_cam}]. Do NOT invent a "
                f"key and do NOT compute intervals — narrate the clash the code "
                f"already proved. If it doesn't warrant a call, output a single "
                f"space to stay silent."
            )
        # Phase 60-04 (HARMONIC-04) — RETROSPECTIVE transition note. PAST-TENSE
        # only: LLM+TTS latency makes a live "bring the fader down" arrive 5-10s
        # late (Pitfall 3). The detector fires this ONLY when both decks are
        # resolved + cited AND a structural blend move just landed, so we narrate
        # what ALREADY happened. No phrase-alignment / bass-swap specifics —
        # vibemix has no per-deck phrase grid or dual-deck low-band, so those are
        # not groundable; stay silent on them.
        if t == "TRANSITION_OPPORTUNITY":
            a_side = ev.extra.get("a_side", "A")
            a_cam = ev.extra.get("a_camelot", "?")
            b_side = ev.extra.get("b_side", "B")
            b_cam = ev.extra.get("b_camelot", "?")
            clash = ev.extra.get("clash")
            verdict = (
                "harmonically those keys were clashing"
                if clash
                else "harmonically the keys sat fine together"
            )
            return (
                f"You just blended deck {a_side} ({a_cam}) into deck {b_side} "
                f"({b_cam}) — {verdict}. Give Kaan the PAST-TENSE read on how that "
                f"blend sat harmonically — nothing else, no present-tense advice, "
                f"the moment's already gone. Cite both keys: [key:{a_side}:{a_cam}] "
                f"and [key:{b_side}:{b_cam}]. Do NOT invent a key. If there's "
                f"nothing worth saying, output a single space to stay silent."
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
