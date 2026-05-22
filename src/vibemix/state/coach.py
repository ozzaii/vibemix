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
from typing import TYPE_CHECKING

from vibemix.state.event import Event
from vibemix.state.music_state import MusicState

if TYPE_CHECKING:  # pragma: no cover — typing-only, keeps coach.py import-light
    # Forward reference for Phase 65 RECALL-02 — the recall_moments list is a
    # list[Record] from vibemix.memory.store. Imported under TYPE_CHECKING so
    # state/coach.py never pulls memory/ at module import time (the no-live-
    # path / no-extraction static gates over memory/ still hold; the coupling
    # here is one-way and lazy, only for the type hint).
    from vibemix.memory.store import Record

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


# ---- Phase 66 — Visible Copilot Move prompt fragments (COPILOT-01/02/03) ----
#
# Two module-scope fragment template strings + the dispatch helper
# (``recall_fragment_for_event``). The fragments are CONDITIONAL APPENDS
# to ``AICoach.build_prompt`` output: they fire only when ``recall_moments``
# is non-empty AND the event type matches the gate (transition-shape vs
# vocabulary). On a cold/feature-off turn the helper returns ``""`` (the
# falsy gate at top of the helper) — preserving the v5.0 byte-identity
# regression floor across every existing ``tests/state/test_coach.py``
# golden test.
#
# Shape precedent: Phase 60 KEY_CLASH + TRANSITION_OPPORTUNITY branches
# at lines 332-381 below — cited, system-grounded, narrate-only,
# do-NOT-invent. Each fragment template:
#   - reads PAST-tense (the past moment AND the current latency)
#   - hands the cite to the LLM ([recall:{record_id}]) — the LLM does
#     NOT invent it; the registry strict-subset at dj_cohost.py:754-778
#     validates the id (a fabricated id strips the WHOLE turn via the
#     Phase 65 anti-poisoning linter — defense in depth)
#   - bakes the anti-feature rules into the template body (no "tendency"
#     phrases, no "next track" recommendation, no settings-screen
#     personalization — COPILOT-03)
#   - caps emission at ONE [recall:<id>] per turn structurally (the
#     "EXACTLY ONCE" instruction + the single-survivor-interpolation in
#     the helper + the registry strict-subset)
#
# Static-gate compatibility note (load-bearing): the templates below
# contain literal forbidden phrases ("you usually do", "you always",
# "you tend to") INSIDE QUOTED EXAMPLES. Those quoted examples are inside
# Python STRING LITERALS — the static gate at
# tests/repo/test_no_recall_antifeatures.py uses
# ``_strip_comments_and_docstrings`` to remove STRING token contents
# (replaces with ``""``) before scanning for forbidden phrases. So the
# forbidden phrases inside example quotes are STRIPPED OUT before the
# substring scan. This means the gate stays GREEN with the example
# phrases in place — the stripper is the load-bearing mechanism, not a
# carve-out. (Verified by the negative-control stripper test
# ``test_strip_comments_and_docstrings_removes_string_content``.)
#
# The leading-space at the start of each template is LOAD-BEARING:
# ``AICoach.build_prompt`` concatenates the fragment directly onto the
# task tail with no separator, so the leading space is the only
# delimiter; preserve it exactly.
#
# Phase 66 (COPILOT-01) — transition-shape recall fragment. Verbatim
# from 66-RESEARCH.md §Pattern 1 (RESEARCH lines 258-275). Gates on
# TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL events with non-empty
# survivors. Substring-uniqueness anchor: "in the live audio" (pre-
# grepped at Wave 0 land time, zero hits in coach.py + matrix.py — the
# Wave 0 RED tests use this as the structural marker).
TRANSITION_SHAPE_RECALL_FRAGMENT_TPL: str = (
    " A PAST MOMENT from a prior session is attached in the "
    "'FROM A PAST SESSION' block above — a transition with similar shape "
    "you've run before. If — AND ONLY IF — that past moment matches what "
    "just happened in the live audio, you MAY add ONE short past-tense "
    "callback line referencing it, citing exactly [recall:{record_id}]. "
    "Compare what you heard NOW vs. what's in the past signature — the "
    "delta is the whole point. Examples of shape: \"that blend sat longer "
    "than the same one you ran last set\", \"killed the bass earlier this "
    "time around\", \"cleaner cut than the version you ran before\". "
    "Hard rules: cite [recall:{record_id}] EXACTLY ONCE (the registry "
    "validates it; a fabricated id strips the whole turn); do NOT invent a "
    "past moment, paraphrase the past signature, or describe it as live; "
    "do NOT recommend a NEXT track or move (no 'try X next time'); do NOT "
    "claim a tendency ('you usually do', 'you always') — narrate THIS one "
    "compared to THAT one. If the past moment doesn't match, OMIT the "
    "callback entirely — your normal reaction is the floor."
)


# Phase 66 (COPILOT-02) — vocabulary/register recall fragment. Verbatim
# from 66-RESEARCH.md §Pattern 2 (RESEARCH lines 288-302). Gates on
# PHASE events with non-empty survivors. Substring-uniqueness anchor:
# "echo your own past words" (pre-grepped at Wave 0 land time, zero
# hits in coach.py + matrix.py).
#
# Anti-paraphrase discipline (66-RESEARCH §Pitfall 4): the template
# instructs Gemini to speak in the DJ's own register ("speak in the same
# register, not Gemini-paraphrased") — explicit framing against the
# failure mode where Gemini describes the DJ's voice instead of echoing
# it. The §RECALL-EAR Kaan-ear check (KAAN-ACTION-LEGAL.md) is the
# runtime defense in depth.
VOCABULARY_RECALL_FRAGMENT_TPL: str = (
    " A PAST MOMENT from a prior session is attached in the "
    "'FROM A PAST SESSION' block above — a phrasing or call you made "
    "before. If — AND ONLY IF — what you'd naturally say RIGHT NOW lines "
    "up with that past signature, you MAY echo your own past words, "
    "citing exactly [recall:{record_id}]. The past signature is YOUR "
    "voice from before; speak in the same register, not Gemini-paraphrased. "
    "Examples: \"same call you made on the last drop like this\", "
    "\"your line from the last set still holds\". Hard rules: cite "
    "[recall:{record_id}] EXACTLY ONCE; do NOT invent a past phrasing; "
    "do NOT claim it's a habit ('you always', 'you tend to'); do NOT "
    "recommend a next move. If your live reaction wouldn't naturally "
    "echo the past, OMIT the callback — a forced echo is the failure "
    "mode this phase guards."
)


def recall_fragment_for_event(
    ev: Event,
    recall_moments: "list[Record] | None",
) -> str:
    """Phase 66 (COPILOT-01/02) — dispatch the right recall fragment
    template for the event type, or return ``""`` on cold/empty input.

    The helper is a TOP-LEVEL pure function (not a class method, not a
    dispatcher class — 66-RESEARCH.md §Don't Hand-Roll names it as a
    helper, not infrastructure). It is called from ``AICoach.build_prompt``
    in the non-diet path; the diet path skips it entirely (Phase 65
    invariant: diet events are ACK_ELIGIBLE incl. HEARTBEAT, never
    retrieval events, and the existing ``_bp_kwargs`` logic at
    ``dj_cohost.py:827`` already withholds ``recall_moments`` from the
    diet call).

    Falsy-gate (cold-path byte-identity contract): if ``recall_moments``
    is ``None`` or ``[]``, return ``""`` immediately. This preserves the
    v5.0 byte-identity floor — every existing
    ``tests/state/test_coach.py`` golden test depends on cold-path
    output being byte-identical to the v5.0 baseline. The triple-equality
    contract is pinned by
    ``test_task_for_event_byte_identical_v5_baseline_no_recall``
    (recall_moments=None == recall_moments=[] == no-kwarg).

    Branch order (TRACK_CHANGE overlap resolution per 66-RESEARCH.md
    §Pitfall 5 + §Open Q1):
        1. TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL → transition-shape
           fragment WINS (TRACK_CHANGE is in BOTH event gates per
           CONTEXT.md Area 1 Q1+Q2; transition is more concrete than
           a vocabulary echo on a track-flip).
        2. PHASE → vocabulary fragment.
        3. Other events → return ``""`` (no fragment).

    Strongest-survivor-only interpolation (66-RESEARCH.md §Pattern 1
    closing paragraph + §Pattern 3): only ``recall_moments[0].record_id``
    is interpolated into the template — Phase 65's ``cosine_topk`` returns
    survivors sorted DESCENDING by score, so index 0 is the strongest
    match. The weaker survivors still appear in the
    ``evidence_line``'s PAST-tense ``FROM A PAST SESSION`` block (so
    Gemini can pattern-match across them) but ONLY the strongest is
    named for the citation. This is the structural max-1-per-turn cap:
    the template instructs "cite [recall:{record_id}] EXACTLY ONCE" and
    only one record_id is interpolated, so any second citation Gemini
    invents would target a record_id that EITHER is not in the registry
    (fabricated → whole turn strips) OR is the same id repeated (the
    EXACTLY-ONCE instruction is a soft cap; the registry strict-subset
    invariant + the single-emit-stream-per-turn shape are the harder
    enforcement). Pinned by
    ``test_only_strongest_survivor_record_id_in_fragment`` +
    ``test_max_one_recall_per_turn_COPILOT02``.

    Args:
        ev: The current ``Event`` (read for ``ev.type`` only — no other
            field is consumed by this helper).
        recall_moments: The Phase 65 ``MemoryRecall.get_latest()``
            survivor list, sorted descending by cosine score. ``None``
            (default / feature-off) and ``[]`` (event fired but all
            below floor / deadline missed / current-session-only) are
            both falsy → ``""`` returned, cold-path byte-identical to
            v5.0.

    Returns:
        A leading-space-prefixed string to concatenate onto the
        ``build_prompt`` task tail, or ``""`` on cold input / unmatched
        event type.
    """
    # Cold-path falsy gate (Pattern A in 66-PATTERNS.md, the LOAD-BEARING
    # byte-identity contract). Mirrors the existing ``if recall_moments:``
    # gate in ``evidence_line`` at line 220.
    if not recall_moments:
        return ""
    # Strongest-survivor-only interpolation. Phase 65 contract:
    # ``cosine_topk`` returns DESC by score, so index 0 is the highest
    # match. Documented in the dispatch decision §Pattern 1 closing
    # paragraph (66-RESEARCH.md).
    strongest = recall_moments[0]
    # Branch order = TRACK_CHANGE overlap resolution (§Pitfall 5 + §Open
    # Q1). TRACK_CHANGE is in BOTH gates; transition-shape WINS by being
    # listed FIRST.
    if ev.type in ("TRACK_CHANGE", "MIX_MOVE", "LAYER_ARRIVAL"):
        return TRANSITION_SHAPE_RECALL_FRAGMENT_TPL.format(
            record_id=strongest.record_id
        )
    if ev.type == "PHASE":
        return VOCABULARY_RECALL_FRAGMENT_TPL.format(
            record_id=strongest.record_id
        )
    # Other event types (KAAN_SPOKE, MANUAL, HEARTBEAT, KEY_CLASH,
    # TRANSITION_OPPORTUNITY) → no fragment. The byte-identity guarantee
    # for these types is preserved by returning "".
    return ""


class AICoach:
    """Builds the per-event prompt. Single persona is set at session-open via
    SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task."""

    @staticmethod
    def evidence_line(
        state: MusicState,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
        recall_moments: "list[Record] | None" = None,
    ) -> str:
        """Build the grounded-state evidence string for the AI prompt.

        ``registry_snapshot`` (Phase 18 Plan 02): optional EvidenceRegistry
        snapshot dict ``{source: {key: (t1, t2, ...)}}``. When non-None AND
        non-empty, an ``evidence_corpus[ev=N,aud=M,mix=K]`` footer is
        appended — primes Gemini that grounded observations exist (Plan
        18-03 builds on this to bake the citation grammar). Default None
        preserves the v4 byte-identical output for all existing callers.

        ``recall_moments`` (Phase 65 Plan 04, RECALL-02): optional list of
        past-session ``Record`` objects pulled off the (off-loop)
        ``MemoryRecall`` seam. The block is gated identically to the Phase-59 ``decks[…]``
        block: ``None`` AND ``[]`` are both falsy → zero bytes appended →
        the v5.0 cold-memory golden stays BYTE-IDENTICAL. When the list is
        non-empty, a PAST-tense fenced ``FROM A PAST SESSION (not happening
        now): …`` block is appended AFTER the live evidence (subordinate —
        live audio stays primary; recall is never read as live). Each token
        is ``[recall:<record_id>]`` so the EXISTING CitationLinter validates
        a Gemini emission against registry survivors registered before the
        snapshot. Default ``None`` preserves the v5.0 byte-identical output.
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
        #
        # Phase 65 review CR-03 — the corpus footer is emitted BEFORE the
        # recall block so its counts describe LIVE evidence (which is what
        # state_refresh_loop / EventDetector wrote into the registry), NOT
        # the past-session fence below. If recall landed first, the
        # adjacent "evidence_corpus[…]" line would sit AFTER the
        # "FROM A PAST SESSION" fence and prime Gemini to read the counts
        # as describing the past session — an inversion of meaning the
        # linter cannot catch.
        if registry_snapshot:
            ev_n = sum(len(v) for v in registry_snapshot.get("ev", {}).values())
            aud_n = sum(len(v) for v in registry_snapshot.get("aud", {}).values())
            mix_n = sum(len(v) for v in registry_snapshot.get("mix", {}).values())
            if (ev_n + aud_n + mix_n) > 0:
                e.append(f"evidence_corpus[ev={ev_n},aud={aud_n},mix={mix_n}]")

        # Phase 65 Plan 04 (RECALL-02) — recall[…] block. ADDITIVE + gated
        # identically to the Phase-59 decks[…] block (and the
        # registry_snapshot footer above): ``if recall_moments:`` is falsy
        # for both the default ``None`` (cold / feature-off) AND ``[]``
        # (event fired but all below floor / deadline missed / current-
        # session-only). In every empty case ZERO bytes are appended →
        # the v5.0 cold-memory golden (tests/state/test_coach.py:47) stays
        # BYTE-IDENTICAL.  PAST-TENSE fenced (RECALL-03) — never read as
        # live evidence; live audio/track/decks above stays primary, recall
        # is subordinate. The order is structural: recall is the LAST
        # element so it sits AFTER both the live evidence block AND the
        # evidence_corpus footer — pinned by
        # test_evidence_line_recall_block_present's index assertion (recall
        # after recent_moves) and the CR-03 ordering test (recall after
        # corpus footer).  Each ``[recall:<record_id>]`` token is
        # registered in the EvidenceRegistry by the agent BEFORE the
        # prompt snapshot (Plan 65-04 wiring); a fabricated
        # ``[recall:<unregistered>]`` then strips the WHOLE turn via the
        # existing CitationLinter's existence-only branch (the headline
        # RECALL-01 poisoning gate).  The diet/compact path intentionally
        # has NO recall block (diet = ACK_ELIGIBLE_EVENTS incl. HEARTBEAT,
        # which is never a retrieval event — keeping recall off the diet
        # path is correct).
        # Inner separator " || " (double-pipe) distinguishes recall moments
        # from the outer " | "-joined evidence fields — makes a grep over
        # evidence_line unambiguous about field count vs moment count.
        if recall_moments:
            parts = [
                f"[recall:{m.record_id}] {m.signature}" for m in recall_moments
            ]
            e.append(
                "FROM A PAST SESSION (not happening now): " + " || ".join(parts)
            )

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
        recall_moments: "list[Record] | None" = None,
        diet: bool = False,
    ) -> str:
        """Format the per-event prompt body.

        ``registry_snapshot`` (Phase 18 Plan 02) threads through to
        ``evidence_line`` for the evidence-corpus footer. Default None
        preserves the v4 byte-identical output.

        ``recall_moments`` (Phase 65 Plan 04, RECALL-02): optional list of
        past-session ``Record`` objects. Threads through to ``evidence_line``;
        ``None``/``[]`` → no recall block, byte-identical to v5.0. The diet
        branch intentionally skips the recall block — diet events are
        ACK_ELIGIBLE (incl. HEARTBEAT) and are never retrieval events.

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
        evidence = AICoach.evidence_line(
            ev.state,
            registry_snapshot=registry_snapshot,
            recall_moments=recall_moments,
        )
        task = AICoach.task_for_event(ev)
        # Phase 66 (COPILOT-01/02) — conditional recall fragment append.
        # ``recall_fragment_for_event`` returns ``""`` on cold/empty input
        # (the load-bearing byte-identity gate); on hot input it returns
        # a leading-space-prefixed string carrying the transition-shape
        # fragment (TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL) or the
        # vocabulary fragment (PHASE), with the strongest survivor's
        # record_id interpolated for the [recall:<id>] citation. The
        # leading space in each template is the only separator from
        # ``task`` — concatenation here is direct.
        recall_frag = recall_fragment_for_event(ev, recall_moments)
        return f"[{evidence} | event={ev.type}] {task}{recall_frag}"
