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

Named-track confidence gate:
    evidence_line quotes the track name only when
    ``audible_track_confidence >= 0.5``. Below that, the prompt prints
    ``track=unknown`` so Sven does not anchor on a stale nowplaying title.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from vibemix.state.deck_context import (
    DECK_CONTEXT_MIN_CONF,
    DECK_CONTEXT_TRUSTED_SOURCES,
    render_audio_window_context,
    render_deck_audio_context,
    render_deck_change_context,
    render_deck_context,
    render_deck_lane_context,
    render_deck_reference_context,
    render_deck_source_context,
    render_grounding_ref_context,
    render_live_evidence_context,
    render_mixer_context,
    render_move_context,
    render_move_effect_context,
    sanitize_historical_move_signature_for_prompt,
)
from vibemix.state.deltas import DELTA_FLOOR, render_delta
from vibemix.state.event import Event
from vibemix.state.music_state import MusicState

if TYPE_CHECKING:  # pragma: no cover — typing-only, keeps prompt_builder.py import-light
    # Forward reference for Phase 65 RECALL-02 — the recall_moments list is a
    # list[Record] from vibemix.memory.store. Imported under TYPE_CHECKING so
    # state/prompt_builder.py never pulls memory/ at module import time (the no-live-
    # path / no-extraction static gates over memory/ still hold; the coupling
    # here is one-way and lazy, only for the type hint).
    from vibemix.memory.store import Record

# ---- Plan 19-02 — prompt diet caps + ack-eligible event set ----
# 4 chars/token proxy (cl100k empirical English baseline; project has no
# tiktoken dep). PROMPT_TOKEN_CAP_FULL is asserted via test on diet=False;
# the runtime invariant for diet=False is v4 byte-identity, NOT a cap check.
PROMPT_TOKEN_CAP_ACK = 800
PROMPT_TOKEN_CAP_FULL = 1500
# Events the compact prompt builder can safely represent. Runtime dispatch is
# allowed to choose a stricter subset for the short audio window; Sven's live
# product path keeps MIX_MOVE/LAYER_ARRIVAL on the full master-output ear.
ACK_ELIGIBLE_EVENTS: frozenset[str] = frozenset(
    {"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}
)


def _current_event_grounding_ref_context(
    ev: Event,
    registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
) -> str | None:
    """Render the current event's own exact citation when EventDetector registered it."""

    if not registry_snapshot:
        return None
    observed = registry_snapshot.get("ev", {}).get(ev.type)
    if not observed:
        return None
    try:
        latest = max(float(t) for t in observed)
    except (TypeError, ValueError):
        return None
    return f"grounding_refs[[ev:{ev.type}@{latest:.1f}]]"


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
    'delta is the whole point. Examples of shape: "that blend sat longer '
    'than the same one you ran last set", "killed the bass earlier this '
    'time around", "cleaner cut than the version you ran before". '
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
    'Examples: "same call you made on the last drop like this", '
    '"your line from the last set still holds". Hard rules: cite '
    "[recall:{record_id}] EXACTLY ONCE; do NOT invent a past phrasing; "
    "do NOT claim it's a habit ('you always', 'you tend to'); do NOT "
    "recommend a next move. If your live reaction wouldn't naturally "
    "echo the past, OMIT the callback — a forced echo is the failure "
    "mode this phase guards."
)

COMPACT_TRANSITION_RECALL_FRAGMENT_TPL: str = (
    " Past memory: compare this move in the live audio with [recall:{record_id}]; "
    "cite once only on a true match."
)

COMPACT_VOCABULARY_RECALL_FRAGMENT_TPL: str = (
    " Past wording memory: echo [recall:{record_id}] once only if it fits now."
)


def recall_fragment_for_event(
    ev: Event,
    recall_moments: list[Record] | None,
    *,
    compact: bool = False,
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
        if compact:
            return COMPACT_TRANSITION_RECALL_FRAGMENT_TPL.format(record_id=strongest.record_id)
        return TRANSITION_SHAPE_RECALL_FRAGMENT_TPL.format(record_id=strongest.record_id)
    if ev.type == "PHASE":
        if compact:
            return COMPACT_VOCABULARY_RECALL_FRAGMENT_TPL.format(record_id=strongest.record_id)
        return VOCABULARY_RECALL_FRAGMENT_TPL.format(record_id=strongest.record_id)
    # Other event types (KAAN_SPOKE, MANUAL, HEARTBEAT, KEY_CLASH,
    # TRANSITION_OPPORTUNITY) → no fragment. The byte-identity guarantee
    # for these types is preserved by returning "".
    return ""


def compact_recall_context_for_event(recall_moments: list[Record] | None) -> str:
    """Return a compact past-session block for diet prompts.

    Full prompts carry the recall block inside ``evidence_line``. Diet prompts
    intentionally skip the full evidence footer, so when recall is hot we need
    a tiny equivalent block or the fragment would mention a "past signature"
    the model cannot see. Cold/empty input returns zero bytes.
    """
    if not recall_moments:
        return ""
    parts = [
        f"[recall:{m.record_id}] {_compact_recall_signature(m.signature)}"
        for m in recall_moments[:3]
    ]
    return " FROM A PAST SESSION (not happening now): " + " || ".join(parts)


def _compact_recall_signature(signature: str, *, cap: int = 120) -> str:
    return sanitize_historical_move_signature_for_prompt(signature, cap=cap)


def _clean_genre_label(raw: object, *, max_len: int = 48) -> str | None:
    """Bound a source/detected genre label before it enters the prompt."""
    text = " ".join(str(raw or "").split())
    if not text:
        return None
    text = "".join(ch for ch in text if ch.isalnum() or ch in {" ", "_", "-", "/", "&", "+"})
    text = text.strip(" -_/&+")
    if not text:
        return None
    return text[:max_len]


def _source_genre_from_decks(state: MusicState) -> str | None:
    """Return a citable deck/library genre when one trusted track owns it.

    Source metadata should outrank DSP/prototype guessing, but only when the
    deck itself is citable: real track id, trusted provenance, and confidence at
    the same deck-context floor used for harmonic/key evidence.
    """
    decks = getattr(getattr(state, "deck_state", None), "decks", None) or {}
    candidates: list[tuple[float, str]] = []
    for deck in decks.values():
        if not getattr(deck, "track_id", None):
            continue
        if float(getattr(deck, "confidence", 0.0) or 0.0) < DECK_CONTEXT_MIN_CONF:
            continue
        source = str(getattr(deck, "source", "") or "").strip().lower()
        if source not in DECK_CONTEXT_TRUSTED_SOURCES:
            continue
        label = _clean_genre_label(getattr(deck, "genre", None))
        if label is not None:
            candidates.append((float(getattr(deck, "confidence", 0.0) or 0.0), label))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


# ---- Plan 96-01 — Course 3 proactive tutor lens confidence floors ----
#
# Above floors → forward-looking count-in language ("breakdown in 16
# beats — get ready") permitted. Below ANY → downgrade to retrospective
# narration ("that was a breakdown — see how the bass dropped out").
#
# CONTEXT.md §Claude's Discretion: defaults are tunable in P98 ear-pass.
# Named constants so the ear-pass diff is one edit per floor.
_COUNT_IN_BPM_FLOOR: float = 0.8
_COUNT_IN_PHRASE_FLOOR: float = 0.7


def _count_in_eligible(state: MusicState) -> bool:
    """True iff Course 3 proactive lens can use forward-looking
    count-in language this turn. False → retrospective narration only.

    All three confidence floors must hold:
      - ``bpm_confidence >= _COUNT_IN_BPM_FLOOR`` (0.8)
      - ``phrase_position_confidence >= _COUNT_IN_PHRASE_FLOOR`` (0.7)
      - ``next_phrase_at is not None``

    Plan 96-01 (Invariant #3 binding) — the runtime conditional that
    keeps fabricated count-ins uncitable-by-construction. Combined with
    the AST gate (tests/learn/test_no_speculative_phrase.py) preventing
    learn/ from computing its own phrase data, a fabricated "breakdown
    in N beats" turn cannot survive either structural or conditional
    enforcement.
    """
    return (
        state.bpm_confidence >= _COUNT_IN_BPM_FLOOR
        and state.phrase_position_confidence >= _COUNT_IN_PHRASE_FLOOR
        and state.next_phrase_at is not None
    )


class AICoach:
    """Builds the per-event prompt. Single persona is set at session-open via
    SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task."""

    @staticmethod
    def evidence_line(
        state: MusicState,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
        recall_moments: list[Record] | None = None,
        audio_capture_context: dict[str, object] | None = None,
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
            # Phase 78 (PERCEIVE-01) — Δ-phrasing for the scalars that moved
            # since the prior tick. ADDITIVE + gated exactly like the decks[…] /
            # recent_moves[8s] blocks: when `prev_perceive` is the falsy default
            # ({}) the loop produces ZERO appends and the v8.0 cold-path golden
            # stays byte-identical. The RAW scalars above are NOT removed (CONTEXT
            # contract — the Δ-line is alongside, not instead). render_delta
            # abstains (returns None) on cold prior OR a sub-floor move, so a fact
            # that didn't meaningfully move is never asserted as a 0% delta
            # (anti-slop invariant #2/#3).
            prev = state.prev_perceive
            if prev:
                deltas = []
                for label, cur, key in (
                    ("kick density", b["sub"], "sub"),
                    ("RMS", state.rms, "rms"),
                    ("onset density", state.onset_density, "onset_density"),
                ):
                    phr = render_delta(label, cur, prev.get(key), floor=DELTA_FLOOR)
                    if phr is not None:
                        deltas.append(phr)
                if deltas:
                    e.append("Δ[" + "; ".join(deltas) + "]")
        else:
            e.append("hearing[silent]")

        if state.audible_track and state.audible_track_confidence >= 0.5:
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
        # The raw deck block stays here for backward prompt continuity. The
        # bounded deck_context[...] packet below adds the explicit transition
        # gate and is also safe for the diet path.
        if state.deck_state.decks:
            resolved = {
                s: d for s, d in state.deck_state.decks.items() if d.camelot and d.confidence >= 0.3
            }
            if resolved:
                parts = [
                    f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm"
                    for s, d in sorted(resolved.items())
                ]
                e.append("decks[" + " | ".join(parts) + "]")
                # One Mind S1 — feed the brain the VALIDATED harmonic+tempo
                # RELATION between the two loaded decks, not just their raw keys.
                # Computed deterministically by the unified TrackRelation engine
                # (S6). Closes the recon's failure case: the brain calling a key
                # clash a "smooth harmonic mix". With the relation stated in the
                # prompt, the brain reasons on ground truth instead of inferring
                # compatibility from two Camelot codes itself. Grounding INPUT
                # only — Invariant #2 deepened the RIGHT way (better evidence),
                # never invented (Invariant #3, it's computed from trusted deck
                # state). We deliberately do NOT route the brain's free text
                # through the pill's decision-claim contract: that contract keys
                # on claim-IDs, but the live brain speaks EvidenceRegistry
                # citations, so it would mass-reject every harmonic phrase and
                # over-strip the reaction — weakening the gate, not deepening it
                # (see S1 KAAN-ACTION note). Lazy import keeps coach import-light;
                # gated to >=2 resolved decks so <2 stays byte-identical (golden).
                if len(resolved) >= 2:
                    try:
                        from vibemix.library.track_relation import compute_relation

                        ordered = sorted(resolved.items())
                        (sa, da), (sb, db) = ordered[0], ordered[1]
                        rel = compute_relation(
                            src_track_id=sa,
                            dst_track_id=sb,
                            cosine=0.0,
                            src_camelot=da.camelot,
                            dst_camelot=db.camelot,
                            src_bpm=da.bpm if (da.bpm and da.bpm > 0) else None,
                            dst_bpm=db.bpm if (db.bpm and db.bpm > 0) else None,
                        )
                        verdict = (
                            "harmonic-clash"
                            if rel.harmonic_clash
                            else "harmonic-ok"
                            if rel.harmonic_compatible
                            else "harmonic-drift"
                        )
                        why = rel.why()
                        e.append(f"blend[{why} {verdict}]" if why else f"blend[{verdict}]")
                    except Exception:  # pragma: no cover — grounding is best-effort
                        pass
            else:
                e.append("decks=unknown")
            deck_context = render_deck_context(state)
            if deck_context:
                e.append(deck_context)
            deck_lane_context = render_deck_lane_context(state)
            if deck_lane_context:
                e.append(deck_lane_context)
            deck_reference_context = render_deck_reference_context(state)
            if deck_reference_context:
                e.append(deck_reference_context)
        deck_source_context = render_deck_source_context(state)
        if deck_source_context:
            e.append(deck_source_context)

        mixer_context = render_mixer_context(state)
        if mixer_context:
            e.append(mixer_context)
        deck_audio_context = render_deck_audio_context(state)
        if deck_audio_context:
            e.append(deck_audio_context)

        # WIRE #4 — auto-detected genre. ADDITIVE + gated exactly like the
        # decks[…] block above so the default MusicState (detected_genre=
        # "unknown") emits ZERO bytes and the v4/silent-state golden stays
        # byte-identical. Floor of 0.5 is the anti-hallucination confidence
        # gate, matching the named-track quote floor. Below
        # floor / unknown → nothing. NOT added to _evidence_line_compact
        # (diet/ack path stays lean).
        source_genre = _source_genre_from_decks(state)
        if source_genre is not None:
            e.append(f"genre={source_genre}")
        elif state.detected_genre != "unknown" and state.genre_confidence >= 0.5:
            detected_genre = _clean_genre_label(state.detected_genre)
            if detected_genre is not None:
                e.append(f"genre={detected_genre}")

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

        grounding_refs = render_grounding_ref_context(
            state,
            registry_snapshot=registry_snapshot,
            audio_capture_context=audio_capture_context,
        )
        if grounding_refs:
            e.append(grounding_refs)
        live_evidence_context = render_live_evidence_context(
            state,
            audio_capture_context=audio_capture_context,
        )
        if live_evidence_context:
            e.append(live_evidence_context)

        # Phase 78 (PERCEIVE-02) — multi-scale trajectory narrative. ADDITIVE +
        # gated exactly like the decks[…] / recent_moves blocks: a falsy ""
        # (cold MusicState, no phases/moves) appends ZERO bytes → the v8.0
        # byte-identity golden holds. _tick_once recomputes this each tick from
        # the already-bounded fields. NOT added to _evidence_line_compact — like
        # decks[…], the trajectory is substantive full-payload, off the diet path.
        if state.trajectory_narrative:
            e.append(f"trajectory[{state.trajectory_narrative}]")

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
        # has its own compact recall block only when recall_moments is hot;
        # cold diet prompts still emit zero recall bytes.
        # Inner separator " || " (double-pipe) distinguishes recall moments
        # from the outer " | "-joined evidence fields — makes a grep over
        # evidence_line unambiguous about field count vs moment count.
        if recall_moments:
            parts = [
                f"[recall:{m.record_id}] "
                f"{sanitize_historical_move_signature_for_prompt(m.signature)}"
                for m in recall_moments
            ]
            e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))

        # Phase 96 (Plan 96-01) — Course 3 proactive tutor lens marker.
        # ADDITIVE + gated: the cold path (session_active=False) emits
        # zero bytes so the v8.0 byte-identical golden stays green. When
        # the Course 3 runtime sets state.session_active=True (lens on),
        # we emit ONE marker token per turn:
        #
        #   lens=retrospective_only            — downgrade (any floor fails)
        #   lens=count_in_eligible[next@<t>]   — forward-looking permitted
        #
        # The marker is read by build_tutor_system_instruction (P92-01) +
        # the Plan 96-03 proactive lens wrapper, which converts the marker
        # into per-turn prompt instructions: retrospective_only =
        # "no forward-looking count-in language permitted this turn";
        # count_in_eligible = "count-in language permitted, cite via
        # [cue:<anchor_id>] when referencing the next boundary at <t>".
        #
        # Trust-the-audio (Invariant #3) binding — Plan 96-01 lands the
        # AST gate that prevents learn/ from ever computing its own
        # phrase data; the marker here is the runtime conditional.
        # Together they make a fabricated "breakdown in 16 beats" turn
        # uncitable-by-construction.
        if state.session_active:
            if _count_in_eligible(state):
                e.append(f"lens=count_in_eligible[next@{state.next_phrase_at:.1f}]")
                if getattr(state, "next_phrase_cue_id", None):
                    e.append(f"cue_anchor={state.next_phrase_cue_id}")
            else:
                e.append("lens=retrospective_only")
            drop_eta = getattr(state, "predicted_drop_in_sec", None)
            if drop_eta is not None:
                e.append(f"drop_incoming[eta@{float(drop_eta):.0f}s]")
                if getattr(state, "predicted_drop_cue_id", None):
                    e.append(f"drop_cue_anchor={state.predicted_drop_cue_id}")

        return " | ".join(e)

    @staticmethod
    def _evidence_line_compact(
        state: MusicState,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
        include_live_evidence: bool = True,
        audio_capture_context: dict[str, object] | None = None,
    ) -> str:
        """Plan 19-02 — compact evidence_line for the diet path.

        Drops phase_age / track_age / set_arc / phase_history / recent_tracks
        from the full evidence_line (saves ~400 token-proxy chars on a
        maximally-populated state). The 6s audio window in DJCoHostAgent.
        llm_node is the safety net that recovers grounding for the dropped
        history fields. ``deck_context[...]`` and compact
        ``deck_lanes_context[...]`` are gated onto this path because MIX_MOVE
        needs the one-deck-vs-two-deck guard and the lane routing map while
        staying cheap.

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

        if state.audible_track and state.audible_track_confidence >= 0.5:
            e.append(f"track={state.audible_track!r}")
        else:
            e.append("track=unknown")

        e.append(f"deck={state.audible_deck}")
        deck_context = render_deck_context(state, compact=True)
        if deck_context:
            e.append(deck_context)
        deck_lane_context = render_deck_lane_context(state, compact=True)
        if deck_lane_context:
            e.append(deck_lane_context)
        mixer_context = render_mixer_context(state)
        if mixer_context:
            e.append(mixer_context)
        deck_audio_context = render_deck_audio_context(state)
        if deck_audio_context:
            e.append(deck_audio_context)
        e.append(f"set_time={int(state.set_seconds // 60)}:{int(state.set_seconds % 60):02d}")

        recent_8s = [(age, label) for age, label in state.recent_moves if age <= 8.0]
        if recent_8s:
            recent_8s.sort(key=lambda x: x[0])
            mv = ", ".join(f"{age:.1f}s ago {label}" for age, label in recent_8s)
            e.append(f"recent_moves[8s]: {mv}")
        else:
            e.append("recent_moves[8s]: NONE")

        grounding_refs = render_grounding_ref_context(
            state,
            registry_snapshot=registry_snapshot,
            audio_capture_context=audio_capture_context,
        )
        if grounding_refs:
            e.append(grounding_refs)
        live_evidence_context = (
            render_live_evidence_context(
                state,
                audio_capture_context=audio_capture_context,
            )
            if include_live_evidence
            else None
        )
        if live_evidence_context:
            e.append(live_evidence_context)

        return " | ".join(e)

    @staticmethod
    def task_for_event(ev: Event) -> str:
        t = ev.type
        ev_extra = ev.extra if isinstance(ev.extra, dict) else {}

        def _with_grounded_receipts(base: str) -> str:
            receipt_lines = []
            receipt_keys = []
            for key in (
                "energy_read_voice_line",
                "move_grade_voice_line",
                "next_suggestion_voice_line",
                "set_progress_voice_line",
                "transition_verdict_voice_line",
                "judge_evidence_line",
            ):
                line = ev_extra.get(key)
                if isinstance(line, str) and line.strip():
                    receipt_keys.append(key)
                    receipt_lines.append(line.strip())
            if not receipt_lines:
                return base
            next_hint = (
                " If next_suggestion_voice_line is present on an otherwise "
                "plain track or phase read, prefer turning that citable receipt "
                "into one forward nudge over describing the current track."
                if "next_suggestion_voice_line" in receipt_keys
                else ""
            )
            return (
                f"{base} {' '.join(receipt_lines)} These are grounded receipt "
                "contexts, not commands; do not force them if the live sound is "
                f"more important.{next_hint}"
            )

        if t == "KAAN_SPOKE":
            return (
                "Kaan just SPOKE — answer him directly, friend tone. Short. Not a music reaction."
            )
        if t == "MANUAL":
            return (
                "Kaan hit his trigger — react with substance to ONE concrete thing "
                "(audible event or recent move)."
            )
        if t == "TRACK_CHANGE":
            judge_line = ev_extra.get("judge_evidence_line")
            if isinstance(judge_line, str) and judge_line.strip():
                return _with_grounded_receipts(
                    f"{judge_line.strip()}. Use that measured Judge verdict as "
                    "the hard transition read. Keep the bracketed citation exactly, "
                    "translate the measured key/low-end result into one short DJ "
                    "reaction, and do not add fader, EQ, or deck-control causes "
                    "that are not in the Judge line. If it is not worth saying, "
                    "output a single space to stay silent."
                )
            prev = ev_extra.get("prev_track")
            prev_clause = f" (was: {prev!r})" if prev else ""
            if isinstance(ev_extra.get("next_suggestion_voice_line"), str):
                return _with_grounded_receipts(
                    f"Track flipped{prev_clause}. You have a grounded forward "
                    "receipt. If it fits the live sound, turn it into one short "
                    "next-move nudge with the exact citations. Do not just "
                    "describe the new track. Avoid uncited source-detail prose "
                    "like bassline/drums/synth/vocal; lead with the suggested "
                    "artist or title and copy both receipt citations."
                )
            return _with_grounded_receipts(
                f"Track flipped{prev_clause}. React to the NEW track's vibe vs "
                "the previous — heavier, weirder, darker, more euphoric?"
            )
        if t == "PHASE":
            new = ev_extra.get("new_phase", "?")
            prev = ev_extra.get("prev_phase", "?")
            # The evidence-poor exit is SILENCE (the single-space contract the
            # TRACK_CHANGE judge branch already uses), NOT a "sound-only read"
            # license: the first end-to-end shipped judge run (2026-06-09,
            # product-floor replay → OpenRouter judge) scored every sound-only
            # PHASE read friend=0 / should_NOT_have_spoken — "pure sound
            # narration". Rare + earned: a line must carry a point, or nothing.
            return (
                f"Phase shifted: {prev}→{new}. React to what the new section "
                "FEELS like, not the label. Speak only if you have a point a "
                "friend at the booth would bother saying out loud — a "
                "feel-read with an opinion, or a grounded opportunity. If "
                "recent_moves[8s] is NONE or live_evidence blocks transition "
                "proof, do not give next-time advice or timing prescriptions "
                "— and when plain sound description is all you have, "
                "output a single space to stay silent."
            )
        if t == "LAYER_ARRIVAL":
            return (
                "A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
                "riff, pad. Name what arrived and how it feels."
            )
        if t == "MIX_MOVE":
            moves = ev_extra.get("moves", [])
            mv = ", ".join(moves)
            raw_audio_capture_context = ev_extra.get("audio_capture_context")
            audio_capture_context = (
                raw_audio_capture_context if isinstance(raw_audio_capture_context, dict) else None
            )
            audio_window_context = render_audio_window_context(ev.state, moves)
            move_context = render_move_context(ev.state, moves)
            change_context = render_deck_change_context(ev.state, moves)
            effect_context = render_move_effect_context(
                ev.state,
                moves,
                audio_capture_context=audio_capture_context,
            )
            live_evidence_context = render_live_evidence_context(
                ev.state,
                moves,
                audio_capture_context=audio_capture_context,
            )
            context_bits = [
                bit
                for bit in (
                    audio_window_context,
                    move_context,
                    change_context,
                    effect_context,
                    live_evidence_context,
                )
                if bit
            ]
            move_clause = f"{' '.join(context_bits)}. " if context_bits else ""
            return (
                f"A controller move was observed [{mv}]. {move_clause}"
                "recent_moves[8s] gives seconds ago; that is a CHANGE point. "
                "Hear before→after: energy, lows, space, tension. "
                "Use deck_context, deck_reference_context, deck_source_context, "
                "deck_audio_context, audio_window_context, "
                "deck_change_context, move_effect_context, live_evidence, and move_context "
                "as the hard deck gate: transition_block/watch => do NOT call this "
                "a transition or blend/switch/segue/handoff/bridge/layer. "
                "Use them only with transition_candidate + audio/move support; "
                "don't grade quality without strong two-deck support. live_evidence categories, "
                "not causal proof or skill grade. "
                "Ground feedback on before→after; give a fix if needed. "
                "Name the EQ, filter, or move if that's worth flagging; "
                "you're a pro, you decide what matters. If nothing changed, read the "
                "mix or output a single space to stay silent."
            )
        if t == "HEARTBEAT":
            return _with_grounded_receipts(
                "Steady stretch. Turn what you hear into where the set should "
                "go next — one forward read Kaan can act on: a move to set up, "
                "a layer to bring in, or an energy to hold or lift. "
                "Ground it in the audio you just heard. "
                "If you cite, copy an exact bracket from grounding_refs; never "
                "invent a timestamp from BPM/RMS values. "
                "If there is no grounded forward read worth interrupting for, output a single "
                "space to stay silent."
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
            return _with_grounded_receipts(
                f"You just blended deck {a_side} ({a_cam}) into deck {b_side} "
                f"({b_cam}) — {verdict}. Give Kaan the PAST-TENSE read on how that "
                f"blend sat harmonically — nothing else, no present-tense advice, "
                f"the moment's already gone. Cite both keys: [key:{a_side}:{a_cam}] "
                f"and [key:{b_side}:{b_cam}]. Do NOT invent a key. If there's "
                f"nothing worth saying, output a single space to stay silent."
            )
        # WIRE #2 (Phase 17 genre-chain → prompt boundary). The 8 genre-chain
        # detectors fire Events carrying MEASURED payloads in ev.extra; before
        # this wire they all hit the "React naturally." fallthrough below and the
        # measurement was discarded — the deepest perception in the system never
        # reached Gemini. Each branch hands the model the SPECIFIC measured fact
        # and tells it to narrate THAT in working-DJ language, grounded only in
        # the number. These are MIX_MOVE narrate-style (NOT KEY_CLASH forced
        # [key:] cites): the measurements are not registry-citable tokens, so a
        # forced [citation] would have no registry survivor and the existence-only
        # CitationLinter would strip the whole turn. Every branch keeps the
        # "output a single space to stay silent" escape so a non-notable event
        # produces no slop.
        if t == "ACID_LINE_ENTRY":
            formant = ev.extra.get("formant_hz")
            q = ev.extra.get("resonance_q")
            return (
                f"A 303-style acid line is OPENING UP — the system measured the "
                f"filter cutoff sitting around {formant} Hz with resonance Q "
                f"climbing to {q}. That's a real filter sweep with the resonance "
                f"biting. React to how that acid line FEELS as it opens — squelchy, "
                f"tense, peaking — grounded only in that measured sweep. If it's not "
                f"worth a call, output a single space to stay silent."
            )
        if t == "KICK_SWAP":
            prev = ev.extra.get("prev_centroid_hz")
            new = ev.extra.get("new_centroid_hz")
            delta = ev.extra.get("delta_hz")
            return (
                f"The KICK TONE just shifted — the system measured the kick-band "
                f"centroid move from {prev} Hz to {new} Hz ({delta} Hz jump). That's "
                f"a new kick character within the track. React to how the kick FEELS "
                f"now — punchier, boomier, tighter, dirtier — grounded only in that "
                f"measured tone shift. If it's not worth a call, output a single "
                f"space to stay silent."
            )
        if t == "SUB_LAYER_ARRIVAL":
            prev = ev.extra.get("prev_sub")
            new = ev.extra.get("new_sub")
            jump = ev.extra.get("sub_jump")
            return (
                f"A SUB-BASS layer just ARRIVED — the system measured the sub band "
                f"jump from {prev} to {new} (+{jump}) under a stable tempo. That's "
                f"real low-end weight landing under the track. React to what that "
                f"new sub DOES to the groove — fills it out, adds weight, makes it "
                f"move — grounded only in that measured sub jump. If it's not worth "
                f"a call, output a single space to stay silent."
            )
        if t == "KICK_DENSITY_SHIFT":
            prev = ev.extra.get("prev_density")
            new = ev.extra.get("new_density")
            delta = ev.extra.get("delta")
            denser = isinstance(delta, (int, float)) and delta > 0
            direction = "denser" if denser else "sparser"
            move_target = (
                "hold the extra drive, trim a competing layer, or set up the next phrase"
                if denser
                else "use the added space, place the next layer, or wait for the next phrase"
            )
            return (
                (
                    f"The KICK PATTERN density shifted — the system measured it move "
                    f"from {prev} to {new} ({delta:+}); the pattern got {direction}. "
                    "Hand the DJ one forward nudge from that change: "
                    f"{move_target}. Ground it only in the measured density shift. "
                    "When the measured shift is the reason to speak, copy the current "
                    "event bracket from grounding_refs and keep the line to one "
                    "forward nudge. If it's not worth a call, output a single space "
                    "to stay silent."
                )
                if isinstance(delta, (int, float))
                else (
                    f"The KICK PATTERN density shifted — the system measured it move "
                    f"from {prev} to {new}. Hand the DJ one forward nudge from that "
                    "measured shift. When the measured shift is the reason to speak, "
                    "copy the current event bracket from grounding_refs and keep the "
                    "line to one forward nudge. If it's not worth a call, output a "
                    "single space to stay silent."
                )
            )
        if t == "DISTORTION_CLIMB":
            db = ev.extra.get("distortion_db")
            pos = ev.extra.get("chain_position")
            return (
                f"SATURATION is CLIMBING — the system measured distortion rising to "
                f"{db} dB (step {pos} in this session's climb). The track is getting "
                f"dirtier, more driven. React to how that grit/saturation FEELS as it "
                f"builds — grounded only in that measured distortion climb. If it's "
                f"not worth a call, output a single space to stay silent."
            )
        if t == "BREAKDOWN_KICK_KILL":
            drop = ev.extra.get("sub_drop")
            new = ev.extra.get("new_sub")
            return (
                f"The KICK and SUB just DROPPED OUT — a breakdown — the system "
                f"measured the sub fall by {drop} (down to {new}) while the track is "
                f"still playing. The floor just opened up. React to that breakdown "
                f"moment — the tension, the suspended feel, what's left without the "
                f"low-end — grounded only in that measured drop. If it's not worth a "
                f"call, output a single space to stay silent."
            )
        if t == "REENTRY_KICK_LAND":
            age = ev.extra.get("kill_age_s")
            sub = ev.extra.get("sub_at_reentry")
            return (
                f"The KICK just LANDED BACK IN after a breakdown — the system "
                f"measured it return {age}s after the kill, on the downbeat, with the "
                f"sub back at {sub}. That's the drop hitting after the tension. React "
                f"to that re-entry moment — the release, the punch coming back — "
                f"grounded only in that measured landing. If it's not worth a call, "
                f"output a single space to stay silent."
            )
        if t == "PHRASE_BOUNDARY":
            bars = ev.extra.get("phrase_length_bars")
            bpm = ev.extra.get("bpm")
            return (
                f"A PHRASE just CLOSED on the downbeat — the system measured a "
                f"{bars}-bar phrase boundary at {bpm} BPM. That's a natural switch "
                f"point — the spot where a section turns over. React to where the "
                f"track sits at this turn, or flag it as a mix/transition window if "
                f"that's what it is — grounded only in that measured phrase "
                f"boundary. If there's nothing worth saying, output a single space "
                f"to stay silent."
            )
        return "React naturally."

    @staticmethod
    def build_prompt(
        ev: Event,
        *,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
        recall_moments: list[Record] | None = None,
        diet: bool = False,
        audio_capture_context: dict[str, object] | None = None,
    ) -> str:
        """Format the per-event prompt body.

        ``registry_snapshot`` (Phase 18 Plan 02) threads through to
        ``evidence_line`` for the evidence-corpus footer. Default None
        preserves the v4 byte-identical output.

        ``recall_moments`` (Phase 65 Plan 04, RECALL-02): optional list of
        past-session ``Record`` objects. Threads through to ``evidence_line``
        in full prompts, and through a compact past-session block in diet
        prompts. ``None``/``[]`` → no recall block, byte-identical to v5.0.

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
                raise ValueError(f"diet path only valid for ACK_ELIGIBLE_EVENTS; got {ev.type}")
            evidence = AICoach._evidence_line_compact(
                ev.state,
                registry_snapshot=registry_snapshot,
                include_live_evidence=ev.type != "MIX_MOVE",
                audio_capture_context=audio_capture_context,
            )
            event_ref = _current_event_grounding_ref_context(ev, registry_snapshot)
            if event_ref:
                evidence = f"{evidence} | {event_ref}"
            task = AICoach.task_for_event(ev)
            recall_context = compact_recall_context_for_event(recall_moments)
            recall_frag = recall_fragment_for_event(ev, recall_moments, compact=True)
            return f"[{evidence}] {task}{recall_context}{recall_frag}"
        evidence = AICoach.evidence_line(
            ev.state,
            registry_snapshot=registry_snapshot,
            recall_moments=recall_moments,
            audio_capture_context=audio_capture_context,
        )
        event_ref = _current_event_grounding_ref_context(ev, registry_snapshot)
        if event_ref:
            evidence = f"{evidence} | {event_ref}"
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
