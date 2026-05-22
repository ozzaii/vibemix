# SPDX-License-Identifier: Apache-2.0
"""AICoach golden-string tests — every byte matters.

Pins the v4:1331-1433 output byte-for-byte. The MIX_MOVE 'do NOT name controls'
clause and the HEARTBEAT 'don't go silent' clause are LOAD-BEARING IP — tests
would catch any paraphrase or accidental tightening on a refactor.

The v4:1350-1351 anti-hallucination invariant (NO ``phase=`` in evidence_line)
is pinned by exclusion: a state with ``phase`` set to every non-silent label
is fed to evidence_line and the output is asserted to NOT contain ``phase=``.
"""

from __future__ import annotations

import inspect

from vibemix.state import AICoach, Event, MusicState

# ---------- Class shape ----------


def test_aicoach_imports_from_package():
    from vibemix.state import AICoach as AC  # noqa: F401


def test_aicoach_has_no_custom_init():
    """AICoach is static-method-only; no __init__ override means default
    object.__init__ is in effect."""
    assert AICoach.__init__ is object.__init__


def test_aicoach_three_public_methods():
    public = [n for n in dir(AICoach) if not n.startswith("_")]
    assert sorted(public) == ["build_prompt", "evidence_line", "task_for_event"]


def test_aicoach_methods_are_static():
    """All three callable surfaces are @staticmethod (no `self` binding)."""
    for name in ("evidence_line", "task_for_event", "build_prompt"):
        method = inspect.getattr_static(AICoach, name)
        assert isinstance(method, staticmethod), f"{name} must be @staticmethod"


# ---------- evidence_line: structural ----------


def test_evidence_line_silent_state_full_format():
    """Minimal silent state — exact byte-for-byte expected output."""
    state = MusicState()  # audible=False, no history, no moves
    out = AICoach.evidence_line(state)
    assert out == (
        "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
    )


# ---------- evidence_line: recall[…] block (Phase 65, RECALL-02) ----------


def _recall_records():
    """Two populated past-session Record moments for the recall block tests.

    Imported lazily so a future Record relocation only touches this helper. The
    record_id is the Phase 64/65 ``f"{session_id}:{seq}"`` shape (inner colon).
    """
    from vibemix.memory.store import Record

    return [
        Record(
            record_id="20260520-2200:7",
            session_id="20260520-2200",
            ts=120.0,
            kind="coach_line",
            signature="that filter sweep into the drop was clean",
            score=0.91,
        ),
        Record(
            record_id="20260520-2200:12",
            session_id="20260520-2200",
            ts=240.0,
            kind="coach_line",
            signature="you rode the groove a touch long here",
            score=0.82,
        ),
    ]


def test_evidence_line_recall_block_present():
    """RECALL-02 — populated recall_moments → PAST-TENSE fence + [recall:<id>] tokens.

    A non-empty recall_moments list appends the additive, PAST-TENSE-fenced
    block AFTER the live evidence (subordinate ordering — recall is never read
    as something happening now). Both record_id tokens appear verbatim so the
    citation linter can validate them against the registered survivors.

    RED until Plan 65-04 wires the recall_moments kwarg + block into
    evidence_line — until then evidence_line() rejects the kwarg (TypeError) or
    emits no block. That is the intended Wave-0 RED.
    """
    state = MusicState()  # silent baseline — only the recall block is added
    out = AICoach.evidence_line(state, recall_moments=_recall_records())

    # PAST-TENSE structural fence — never read as live.
    fence = "FROM A PAST SESSION (not happening now): "
    assert fence in out
    # Both registered record_id tokens appear verbatim (linter-citable).
    assert "[recall:20260520-2200:7]" in out
    assert "[recall:20260520-2200:12]" in out
    # The signatures ride along inside the block.
    assert "that filter sweep into the drop was clean" in out

    # Subordinate ordering: the recall fence appears AFTER the live evidence.
    assert out.index("recent_moves[8s]") < out.index(fence)


def test_evidence_line_recall_block_after_corpus_footer():
    """Phase 65 review CR-03 — recall block lands AFTER the evidence_corpus footer.

    When BOTH ``registry_snapshot`` AND ``recall_moments`` are populated, the
    evidence-corpus footer (whose counts describe LIVE evidence) MUST appear
    BEFORE the PAST-tense recall fence — otherwise Gemini can read the corpus
    counts as describing the past session, an inversion of meaning the linter
    cannot catch.
    """
    state = MusicState()  # silent baseline — minimum live content
    snapshot = {
        "ev": {"HEARTBEAT": (10.0, 80.0)},
        "aud": {"rms": (5.0,)},
        "mix": {},
    }
    out = AICoach.evidence_line(
        state,
        registry_snapshot=snapshot,
        recall_moments=_recall_records(),
    )
    fence = "FROM A PAST SESSION (not happening now): "
    corpus = "evidence_corpus[ev=2,aud=1,mix=0]"
    assert corpus in out
    assert fence in out
    # Ordering invariant: live-evidence corpus footer FIRST, past-session
    # fence SECOND (recall is the LAST element of the evidence line).
    assert out.index(corpus) < out.index(fence)
    # Recall fence sits at the END of the line (no trailing content after).
    assert out.endswith(
        "[recall:20260520-2200:7] that filter sweep into the drop was clean"
        " || [recall:20260520-2200:12] you rode the groove a touch long here"
    )


def test_evidence_line_recall_empty_no_block():
    """RECALL-02 — empty (and None) recall_moments → emit NOTHING.

    The recall block is gated identically to the decks[…] / registry_snapshot
    gates: ``if recall_moments:`` — both ``[]`` and the default ``None`` are
    falsy, so zero bytes are appended. An empty recall list must yield the EXACT
    same string as the no-kwarg call (the byte-identical-when-empty contract).

    RED until Plan 65-04 adds the recall_moments kwarg with a falsy gate.
    """
    state = MusicState()
    assert AICoach.evidence_line(state, recall_moments=[]) == AICoach.evidence_line(state)


def test_evidence_line_audible_no_recall_byte_identical_v5_baseline(mocker):
    """Phase 65 review WR-05 — the no-recall path is BYTE-IDENTICAL to v5.0.

    The recall block is additive on top of a v5.0 baseline; the cold/feature-off
    path (default ``recall_moments=None``) and the empty-list path
    (``recall_moments=[]``) must both produce the SAME bytes the v5.0 baseline
    produced. ``test_evidence_line_recall_empty_no_block`` proves "None == []"
    relatively (both no-recall calls match); this test pins the ABSOLUTE bytes
    so a future maintainer who accidentally adds a trailing space, reorders a
    field, or shifts the corpus footer also breaks ``recall_moments=None`` —
    not just the recall comparison.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        audible_track="Daft Punk - Around the World",
        audible_track_confidence=0.6,
        audible_deck="A",
        set_start_at=755.0,  # now-set = 245s → 4:05
    )
    # v5.0 baseline string — copied from the live audible-block format pinned
    # by test_evidence_line_audible_block_format below.
    v5_baseline = (
        "hearing[rms=0.094 sub=0.20 low=0.30 mid=0.30 high=0.20 bpm=126] | "
        "track='Daft Punk - Around the World' | deck=A | set_time=4:05 | "
        "recent_moves[8s]: NONE"
    )
    out_default = AICoach.evidence_line(state)
    out_none = AICoach.evidence_line(state, recall_moments=None)
    out_empty = AICoach.evidence_line(state, recall_moments=[])
    assert out_default == v5_baseline
    assert out_none == v5_baseline
    assert out_empty == v5_baseline


def test_evidence_line_audible_block_format(mocker):
    """Pin the exact audible-block format from v4:1336-1339."""
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        audible_track="Daft Punk - Around the World",
        audible_track_confidence=0.6,
        audible_deck="A",
        set_start_at=755.0,  # now-set = 245s → 4:05
    )
    out = AICoach.evidence_line(state)
    # Substring tests for each component (in order):
    assert "hearing[rms=0.094 sub=0.20 low=0.30 mid=0.30 high=0.20 bpm=126]" in out
    assert "track='Daft Punk - Around the World'" in out
    assert "deck=A" in out
    assert "set_time=4:05" in out
    assert "recent_moves[8s]: NONE" in out


def test_evidence_line_track_unknown_below_03():
    """audible_track_confidence < 0.3 → 'track=unknown', title not quoted."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        bands={"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2},
        audible_track="X",
        audible_track_confidence=0.25,
    )
    out = AICoach.evidence_line(state)
    assert "track=unknown" in out
    assert "'X'" not in out


def test_evidence_line_track_quoted_at_exact_03_boundary():
    """v4:1343 uses `>=` so 0.3 itself quotes the title."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        bands={"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2},
        audible_track="X",
        audible_track_confidence=0.3,
    )
    out = AICoach.evidence_line(state)
    assert "track='X'" in out
    assert "track=unknown" not in out


def test_evidence_line_HAS_NO_phase_field():
    """LOAD-BEARING ANTI-HALLUCINATION: v4:1350-1351 removed `phase=`.
    Verify the substring is ABSENT for every non-silent phase label."""
    for phase_value in ("silent", "low", "groove", "build", "drop", "peak", "breakdown"):
        state = MusicState(audible=True, rms=0.05, bpm=120.0, phase=phase_value)
        out = AICoach.evidence_line(state)
        assert "phase=" not in out, f"unexpected phase= field with phase={phase_value!r}"
        # phase_age IS allowed when phase_history is populated; only the literal
        # substring "phase=" (with no underscore) is banned.


def test_evidence_line_phase_age_when_history_present(mocker):
    """phase_history non-empty → `phase_age=...s` (note: trailing 's')."""
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        phase_history=[(988.0, "groove", "build")],
    )
    out = AICoach.evidence_line(state)
    assert "phase_age=12.0s" in out


def test_evidence_line_track_age_when_history_present(mocker):
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        track_history=[(992.5, "Title")],
    )
    out = AICoach.evidence_line(state)
    assert "track_age=7.5s" in out


def test_evidence_line_recent_moves_rendering():
    """Newest-first ordering by age (smallest age = most recent)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        recent_moves=[(5.4, "xfader→A-side"), (2.1, "A_low: flat→killed (big twist)")],
    )
    out = AICoach.evidence_line(state)
    # Sorted ascending by age → 2.1 first, then 5.4.
    assert (
        "recent_moves[8s]: 2.1s ago A_low: flat→killed (big twist), 5.4s ago xfader→A-side" in out
    )


def test_evidence_line_recent_moves_filtered_by_age():
    """Moves with age > 8.0 are filtered out (v4:1362)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        recent_moves=[(2.0, "A_play→ON"), (10.5, "B_low: cut→killed (big twist)")],
    )
    out = AICoach.evidence_line(state)
    assert "A_play→ON" in out
    assert "B_low" not in out  # filtered (age 10.5 > 8.0)


def test_evidence_line_set_arc_only_when_len_ge_2():
    state_short = MusicState(audible=True, rms=0.05, bpm=120.0, long_arc=[0.05])
    out_short = AICoach.evidence_line(state_short)
    assert "set_arc" not in out_short

    state_long = MusicState(audible=True, rms=0.05, bpm=120.0, long_arc=[0.05, 0.06, 0.08])
    out_long = AICoach.evidence_line(state_long)
    assert "set_arc[30s]=[0.05, 0.06, 0.08]" in out_long


def test_evidence_line_phase_history_chain():
    """phase_history → 'silent→low→groove→drop' chain (v4:1376-1382)."""
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        phase_history=[
            (100.0, "silent", "low"),
            (200.0, "low", "groove"),
            (300.0, "groove", "drop"),
        ],
    )
    out = AICoach.evidence_line(state)
    assert "phase_history: silent→low→groove→drop" in out


def test_evidence_line_recent_tracks_at_2_entries():
    state = MusicState(
        audible=True,
        rms=0.05,
        bpm=120.0,
        track_history=[(100.0, "Song A"), (200.0, "Song B"), (300.0, "Song C")],
    )
    out = AICoach.evidence_line(state)
    assert "recent_tracks: 'Song A'→'Song B'→'Song C'" in out


def test_evidence_line_uses_pipe_separator():
    """v4:1389 joins with ' | ' (pipe), NOT comma."""
    state = MusicState()
    out = AICoach.evidence_line(state)
    # The fields are separated by " | " — 4 components in the minimal case
    # (hearing, track, deck, set_time, recent_moves[8s]) — so 4 separators.
    assert out.count(" | ") == 4


# ---------- task_for_event: golden strings ----------


def _ev(type_: str, extra: dict | None = None) -> Event:
    return Event(type=type_, state=MusicState(), extra=extra or {})


def test_task_kaan_spoke_exact_string():
    """2026-05-18 — word-count clauses dropped from prompts; Gemini routinely
    blew past the budget and the clause was just noise. Reactions stay
    short by `style:` rules in the system instruction, not per-prompt budget."""
    out = AICoach.task_for_event(_ev("KAAN_SPOKE"))
    assert (
        out
        == "Kaan just SPOKE — answer him directly, friend tone. Short. Not a music reaction."
    )


def test_task_manual_exact_string():
    out = AICoach.task_for_event(_ev("MANUAL"))
    assert out == (
        "Kaan hit his trigger — react with substance to ONE concrete thing "
        "(audible event or recent move)."
    )


def test_task_track_change_no_prev_track():
    """prev_clause is empty when prev_track is None/missing."""
    out = AICoach.task_for_event(_ev("TRACK_CHANGE", {"new_track": "X"}))
    assert "Track flipped." in out
    assert "(was:" not in out
    assert "React to the NEW track's vibe vs the previous" in out
    assert "heavier, weirder, darker, more euphoric?" in out


def test_task_track_change_with_prev_track():
    """prev_clause uses `!r` (repr → single-quoted)."""
    out = AICoach.task_for_event(_ev("TRACK_CHANGE", {"prev_track": "Old Title"}))
    assert "Track flipped (was: 'Old Title')." in out


def test_task_phase_exact_format():
    out = AICoach.task_for_event(_ev("PHASE", {"prev_phase": "groove", "new_phase": "drop"}))
    assert "Phase shifted: groove→drop." in out
    assert "FEELS like, not the label." in out


def test_task_phase_fallback_when_extras_missing():
    """Missing prev_phase/new_phase → '?' fallback (v4:1407-1408)."""
    out = AICoach.task_for_event(_ev("PHASE"))
    assert "Phase shifted: ?→?." in out


def test_task_layer_arrival_exact_string():
    out = AICoach.task_for_event(_ev("LAYER_ARRIVAL"))
    assert out == (
        "A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
        "riff, pad. Name what arrived and how it feels."
    )


def test_task_mix_move_LOAD_BEARING_anti_slop_clause():
    """2026-05-21 (Kaan-directed) — the move-second is a CHANGE point; the
    cohost puts its ears there and grounds feedback on the audible before→after
    of the move ('hareket ettiğim saniyeyi işaretle ki orda yaşanan değişikliği
    alsın'). The OLD v4 hard ban 'Do NOT name faders/EQs/knobs' is LIFTED — Kaan:
    'eqları seslendirebilir ... tam bir professional coach olmalı, ne hakkında
    konuşacağına o karar verecek.' A pro names the EQ/filter when it's worth it."""
    out = AICoach.task_for_event(
        _ev("MIX_MOVE", {"moves": ["A_play→ON", "A_low: cut→killed (big twist)"]})
    )
    assert "A move just landed [A_play→ON, A_low: cut→killed (big twist)]" in out
    # The move-second is a change point — ground on the audible before→after there.
    assert "CHANGE point" in out
    # The knob-ban is GONE; naming an EQ/filter is now explicitly allowed.
    assert "Do NOT name faders/EQs/knobs/decks/controls" not in out
    assert "Name the EQ" in out
    # The model decides what matters this moment.
    assert "you decide what matters" in out
    # Silence path still present.
    assert "output a single space to stay silent" in out


def test_task_heartbeat_LOAD_BEARING_anti_silence_clause():
    """The 'don't go silent' clause is the v4 anti-mute tightening."""
    out = AICoach.task_for_event(_ev("HEARTBEAT"))
    assert "don't go silent" in out
    assert out == (
        "Steady stretch. ONE sharp observation about the SOUND right "
        "now — groove, texture, what the track is doing musically. "
        "Always reply with something fresh; don't go silent."
    )


def test_task_fallback_unknown_type():
    out = AICoach.task_for_event(_ev("UNKNOWN_TYPE"))
    assert out == "React naturally."


# ---------- Phase 61 Wave-0 gap: KEY_CLASH / TRANSITION harmonic voice ----------
# 61-RESEARCH flagged that NO test fenced the Phase-60 harmonic arms. These two
# fence the live arm text (coach.py:267-316) so a future cell/persona edit cannot
# silently break the DJ-verb move, the both-keys-cited contract, the no-invent
# guard, or the system-owns-the-verdict / past-tense framing. GREEN against the
# current arms (this plan changes no production code). Modeled on
# test_task_mix_move_LOAD_BEARING_anti_slop_clause.


def test_task_key_clash_LOAD_BEARING_dj_verb_cited_no_invent():
    """KEY_CLASH (COACH-01 prescriptive + COACH-04 cited): the arm prescribes a
    DJ-verb move, cites BOTH decks' keys exactly, forbids inventing a key, and
    frames the verdict as the system's (not the LLM's)."""
    out = AICoach.task_for_event(
        _ev(
            "KEY_CLASH",
            {"a_side": "A", "a_camelot": "8A", "b_side": "B", "b_camelot": "2A", "semitones": 3},
        )
    )
    # A DJ-verb move is prescribed.
    assert any(v in out for v in ("kill", "cut", "filter")), f"no DJ verb in: {out!r}"
    # BOTH keys are cited exactly (existence-only [key:...] grammar).
    assert "[key:A:8A]" in out
    assert "[key:B:2A]" in out
    # No-invent guard present.
    assert "Do NOT invent a key" in out
    # System owns the verdict — the LLM narrates, it does not decide the clash.
    assert "you do NOT decide this" in out
    assert "confirmed by the system" in out
    # The pre-computed semitone count is handed in, not derived by the model.
    assert "3 semitones apart" in out
    assert "do NOT compute intervals" in out


def test_task_transition_opportunity_LOAD_BEARING_past_tense_cited_no_invent():
    """TRANSITION_OPPORTUNITY (COACH-04 cited + Pitfall 3 latency): retrospective
    past-tense read only — no present-tense imperative — with both keys cited and
    the no-invent guard."""
    out = AICoach.task_for_event(
        _ev(
            "TRANSITION_OPPORTUNITY",
            {"a_side": "A", "a_camelot": "8A", "b_side": "B", "b_camelot": "9A", "clash": False},
        )
    )
    # Past-tense framing — the moment is already gone; no live advice.
    assert "PAST-TENSE" in out
    assert "no present-tense advice" in out
    assert "the moment's already gone" in out
    # Both keys cited exactly.
    assert "[key:A:8A]" in out
    assert "[key:B:9A]" in out
    # No-invent guard present.
    assert "Do NOT invent a key" in out
    # clash=False → "keys sat fine together" verdict (not the clash branch).
    assert "the keys sat fine together" in out


# ---------- build_prompt: format wrapper ----------


def test_build_prompt_format():
    """v4:1429-1433 format: f'[{evidence} | event={ev.type}] {task}'."""
    ev = _ev("HEARTBEAT")
    out = AICoach.build_prompt(ev)
    assert out.startswith("[")
    # The closing bracket comes immediately after 'event=HEARTBEAT' then space + task.
    assert " | event=HEARTBEAT] " in out
    # The task tail is present:
    assert "Steady stretch." in out


def test_build_prompt_integrates_evidence_and_task():
    """Verify the full chain: evidence + event marker + task all stitched together."""
    ev = _ev("KAAN_SPOKE")
    out = AICoach.build_prompt(ev)
    # Evidence opens the string:
    assert "hearing[silent]" in out
    # Event marker present:
    assert "event=KAAN_SPOKE" in out
    # Task is at the end (after `]`):
    assert out.endswith("Not a music reaction.")


def test_build_prompt_track_change_with_prev_flows_through():
    ms = MusicState()
    ev = Event("TRACK_CHANGE", ms, extra={"prev_track": "A", "new_track": "B"})
    out = AICoach.build_prompt(ev)
    assert "event=TRACK_CHANGE" in out
    assert "(was: 'A')" in out


# =============================================================================
# Phase 18 Plan 02 — AICoach evidence_line + build_prompt registry_snapshot
# =============================================================================


def test_18_02_evidence_line_byte_identical_when_no_snapshot():
    """Test L — backward-compat: existing signature still works.

    AICoach.evidence_line(state) without snapshot kwarg returns the SAME
    string it does today (byte-for-byte). Existing test_coach.py tests stay
    GREEN unchanged (verified by the rest of this file). This test pins
    the no-kwarg path explicitly.
    """
    state = MusicState()  # silent default
    out_no_kwarg = AICoach.evidence_line(state)
    out_none_kwarg = AICoach.evidence_line(state, registry_snapshot=None)
    assert out_no_kwarg == out_none_kwarg
    # Byte-identical to the v4 silent baseline pinned in
    # test_evidence_line_silent_state_full_format above.
    assert out_no_kwarg == (
        "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
    )


def test_18_02_evidence_line_appends_corpus_footer_when_snapshot_present():
    """Test M — snapshot kwarg appended as evidence-corpus footer.

    AICoach.evidence_line(state, registry_snapshot={...}) appends a single
    line "evidence_corpus[ev=N,aud=M,mix=K]" at the end where N/M/K are
    integer counts of observations per source. Only present when snapshot
    is non-None AND has at least one observation; otherwise omitted.
    """
    state = MusicState()
    snapshot = {
        "ev": {"HEARTBEAT": (10.0, 80.0), "MIX_MOVE": (45.0,)},  # 3 obs
        "aud": {"rms": (5.0, 6.0, 7.0, 8.0), "bpm": (5.0,)},     # 5 obs
        "mix": {"phase=drop": (45.0,)},                           # 1 obs
    }
    out = AICoach.evidence_line(state, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=3,aud=5,mix=1]" in out
    # Footer appears once, at the very end (after the last existing pipe)
    assert out.endswith("evidence_corpus[ev=3,aud=5,mix=1]")


def test_18_02_evidence_line_omits_footer_when_snapshot_empty():
    """Empty snapshot dict → footer omitted (no zero-only line)."""
    state = MusicState()
    out_empty = AICoach.evidence_line(state, registry_snapshot={})
    assert "evidence_corpus" not in out_empty

    # All-zero counts (snapshot has source keys but no observations) → omitted
    out_zero_obs = AICoach.evidence_line(state, registry_snapshot={"ev": {}, "aud": {}, "mix": {}})
    assert "evidence_corpus" not in out_zero_obs


def test_18_02_evidence_line_handles_missing_source_keys():
    """Snapshot with only some source keys → counts the present ones, treats
    missing keys as 0. No KeyError."""
    state = MusicState()
    snapshot = {"ev": {"HEARTBEAT": (10.0,)}}  # only ev, no aud/mix
    out = AICoach.evidence_line(state, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=1,aud=0,mix=0]" in out


def test_18_02_build_prompt_threads_snapshot_kwarg():
    """Test N — build_prompt accepts and threads snapshot.

    AICoach.build_prompt(ev, registry_snapshot=...) calls evidence_line with
    the same snapshot. Default None preserves Phase 4 invariant.
    """
    ev = _ev("HEARTBEAT")
    snapshot = {"ev": {"HEARTBEAT": (45.0,)}}
    out = AICoach.build_prompt(ev, registry_snapshot=snapshot)
    assert "evidence_corpus[ev=1,aud=0,mix=0]" in out

    # Default None preserves Phase 4 invariant — same as build_prompt(ev)
    out_default = AICoach.build_prompt(ev)
    out_none = AICoach.build_prompt(ev, registry_snapshot=None)
    assert out_default == out_none


# ---- Phase 66 — recall_fragment_for_event tests (COPILOT-01/02) ----
#
# RED-first contract pinning the recall_fragment_for_event helper + the
# build_prompt integration. Mirrors the Phase 65 byte-identity discipline:
# the helper MUST return "" for cold/empty `recall_moments` so build_prompt
# output stays byte-identical to v5.0 — the load-bearing regression floor
# at test_evidence_line_audible_no_recall_byte_identical_v5_baseline must
# not move.
#
# Fragment-unique substring locks (verified absent from current source at
# Wave 0 land — recorded in 66-VALIDATION.md §Wave 0 Requirements + the
# task <action> grep evidence; the executor reproduced each substring grep
# returning ZERO hits on src/vibemix/state/coach.py + src/vibemix/prompts/matrix.py
# before committing):
#
#   - "in the live audio"        → transition-shape fragment unique marker
#     (from 66-RESEARCH.md TRANSITION_SHAPE_RECALL_FRAGMENT_TPL lines 258-275:
#      "Compare what you heard NOW vs. what's in the past signature... in
#      the live audio")
#
#   - "echo your own past words" → vocabulary fragment unique marker
#     (from 66-RESEARCH.md VOCABULARY_RECALL_FRAGMENT_TPL lines 288-302:
#      "you MAY echo your own past words")
#
# If either substring grows into coach.py / matrix.py for an UNRELATED
# reason before Plan 02 lands, surface a finding (Phase 66 must STOP and
# pick a new fragment-unique substring) — do NOT alter the assertions to
# work around it. The substring-uniqueness invariant is what makes these
# tests RED for the right STRUCTURAL reason today and GREEN for the right
# reason after Plan 02.
#
# Per-test-body imports of `recall_fragment_for_event` wrapped in
# pytest.fail-on-ImportError keep the file COLLECTABLE under pytest even
# while the symbol does not exist (Wave 0 contract: collection stays clean,
# tests fail for the right reason).


def _phase_66_record_stubs(n: int = 1):
    """Return ``n`` minimal Record stubs sorted DESC by implied cosine score.

    Imported lazily (matches the _recall_records pattern above) so a future
    Record relocation only touches the helper. record_ids follow the Phase
    64/65 ``f"{session_id}:{seq}"`` shape with an inner colon. The stubs are
    ordered strongest-first per the Phase 65 cosine_topk contract (sort
    DESC by score), so recall_moments[0] is the strongest survivor — this
    is the ordering the Phase 66 fragment helper relies on for the
    "interpolate ONLY the strongest record_id" structural cap.
    """
    from vibemix.memory.store import Record

    pool = [
        Record(
            record_id="20260520-2200:7",
            session_id="20260520-2200",
            ts=120.0,
            kind="coach_line",
            signature="that filter sweep into the drop was clean",
            score=0.91,
        ),
        Record(
            record_id="20260520-2200:12",
            session_id="20260520-2200",
            ts=240.0,
            kind="coach_line",
            signature="you rode the groove a touch long here",
            score=0.82,
        ),
        Record(
            record_id="20260519-1830:3",
            session_id="20260519-1830",
            ts=60.0,
            kind="coach_line",
            signature="that bass drop punched harder than this one",
            score=0.74,
        ),
    ]
    return pool[:n]


def test_transition_recall_fragment_appears():
    """COPILOT-01 — TRACK_CHANGE/MIX_MOVE/LAYER_ARRIVAL with non-empty
    recall_moments → build_prompt output contains both the Phase 65 PAST-tense
    fence AND the transition-shape fragment's unique substring.

    Fragment-unique substring: "in the live audio" — verified absent from
    src/vibemix/state/coach.py AND src/vibemix/prompts/matrix.py at Wave 0
    land (zero hits in the pre-grep recorded in the section header above).

    RED reason: `recall_fragment_for_event` symbol does not exist in
    vibemix.state.coach yet — Plan 02 Task 2 adds it.
    """
    try:
        from vibemix.state.coach import recall_fragment_for_event  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "recall_fragment_for_event symbol missing from "
            "vibemix.state.coach — Plan 02 Task 2 must add it (COPILOT-01)"
        )

    survivors = _phase_66_record_stubs(n=2)
    for type_ in ("TRACK_CHANGE", "MIX_MOVE", "LAYER_ARRIVAL"):
        ev = _ev(type_)
        out = AICoach.build_prompt(ev, recall_moments=survivors)
        # Phase 65 evidence_line PAST-tense fence rides along (already green).
        assert "FROM A PAST SESSION" in out, (
            f"missing Phase 65 PAST-tense fence on {type_}"
        )
        # Transition-shape fragment unique marker — pinned at Wave 0 from
        # 66-RESEARCH.md TRANSITION_SHAPE_RECALL_FRAGMENT_TPL.
        assert "in the live audio" in out, (
            f"missing transition fragment unique substring on {type_}"
        )


def test_vocabulary_recall_fragment_appears():
    """COPILOT-02 — PHASE event with non-empty recall_moments → build_prompt
    output contains the vocabulary fragment's unique substring.

    Fragment-unique substring: "echo your own past words" — verified absent
    from src/vibemix/state/coach.py AND src/vibemix/prompts/matrix.py at
    Wave 0 land.

    RED reason: `recall_fragment_for_event` symbol does not exist yet —
    Plan 02 Task 2 must add it.
    """
    try:
        from vibemix.state.coach import recall_fragment_for_event  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "recall_fragment_for_event symbol missing from "
            "vibemix.state.coach — Plan 02 Task 2 must add it (COPILOT-02)"
        )

    survivors = _phase_66_record_stubs(n=1)
    ev = _ev("PHASE", {"prev_phase": "groove", "new_phase": "drop"})
    out = AICoach.build_prompt(ev, recall_moments=survivors)
    assert "FROM A PAST SESSION" in out, "missing Phase 65 PAST-tense fence on PHASE"
    assert "echo your own past words" in out, (
        "missing vocabulary fragment unique substring on PHASE"
    )


def test_task_for_event_byte_identical_v5_baseline_no_recall():
    """COPILOT-01/03 — the LOAD-BEARING regression floor.

    The cold-path byte-identity invariant (Phase 65 + Phase 66): when
    recall_moments is None / [] / not passed, build_prompt output is
    byte-identical across all three call shapes. After Plan 02 lands the
    fragment helper, this test catches a broken falsy-gate (i.e. a helper
    that appends a non-empty string on cold input) — the kind of bug that
    breaks every existing v5.0 golden test.

    Pinned across the FULL event-type set (KAAN_SPOKE / MANUAL /
    TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KEY_CLASH
    / TRANSITION_OPPORTUNITY) so a future bug that flips the gate ONLY on a
    specific event type cannot slip through.

    PASSES today (helper does not exist; build_prompt ignores the kwarg
    until Plan 02). MUST stay GREEN after Plan 02 — this is the floor.
    """
    extras = {
        "TRACK_CHANGE": {"prev_track": "Old Title", "new_track": "New Title"},
        "PHASE": {"prev_phase": "groove", "new_phase": "drop"},
        "MIX_MOVE": {"moves": ["A_play→ON"]},
        "KEY_CLASH": {
            "a_side": "A",
            "a_camelot": "8A",
            "b_side": "B",
            "b_camelot": "2A",
            "semitones": 3,
        },
        "TRANSITION_OPPORTUNITY": {
            "a_side": "A",
            "a_camelot": "8A",
            "b_side": "B",
            "b_camelot": "9A",
            "clash": False,
        },
    }
    for type_ in (
        "KAAN_SPOKE",
        "MANUAL",
        "TRACK_CHANGE",
        "PHASE",
        "LAYER_ARRIVAL",
        "MIX_MOVE",
        "HEARTBEAT",
        "KEY_CLASH",
        "TRANSITION_OPPORTUNITY",
    ):
        ev = _ev(type_, extras.get(type_))
        out_default = AICoach.build_prompt(ev)
        out_none = AICoach.build_prompt(ev, recall_moments=None)
        out_empty = AICoach.build_prompt(ev, recall_moments=[])
        # The triple-equality is the contract: None == [] == no-kwarg.
        # A helper that mishandles the falsy gate breaks at least one leg.
        assert out_default == out_none, (
            f"recall_moments=None must be byte-identical to no-kwarg "
            f"on {type_} (cold-path byte-identity floor)"
        )
        assert out_default == out_empty, (
            f"recall_moments=[] must be byte-identical to no-kwarg "
            f"on {type_} (cold-path byte-identity floor)"
        )


def test_only_strongest_survivor_record_id_in_fragment():
    """COPILOT-02 — only the STRONGEST survivor's record_id is interpolated
    into the fragment template, while the FULL survivor list still appears
    in the Phase 65 PAST-tense FROM A PAST SESSION evidence_line block.

    Pins BOTH halves of the contract:
      (a) the fragment portion (the new Phase 66 helper output) contains
          recall_moments[0].record_id EXACTLY ONCE and does NOT contain
          record_ids of the weaker survivors;
      (b) the FULL prompt still contains every survivor's record_id (the
          weaker ones live in the Phase 65 evidence_line block — the LLM
          can pattern-match across all of them, but the citation
          instruction names only the strongest).

    Survivors are constructed in descending cosine-score order per the
    Phase 65 cosine_topk contract.

    RED reason: helper does not exist; recall_moments=... yields no
    fragment portion in build_prompt output today (build_prompt ignores
    the kwarg until Plan 02 adds the integration).
    """
    try:
        from vibemix.state.coach import recall_fragment_for_event  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "recall_fragment_for_event symbol missing from "
            "vibemix.state.coach — Plan 02 Task 2 must add it (COPILOT-02)"
        )

    survivors = _phase_66_record_stubs(n=3)
    strongest, second, third = survivors[0], survivors[1], survivors[2]
    ev = _ev("TRACK_CHANGE", {"prev_track": "X", "new_track": "Y"})
    out = AICoach.build_prompt(ev, recall_moments=survivors)

    # All three record_ids appear in the PAST-tense evidence_line block
    # (Phase 65 — already green; this assertion pins that this contract is
    # not regressed by the Phase 66 fragment integration).
    assert strongest.record_id in out
    assert second.record_id in out
    assert third.record_id in out

    # Locate the fragment portion: everything AFTER the
    # "FROM A PAST SESSION" block. The evidence_line ends at "]" wrapping
    # ` | event=TRACK_CHANGE]` — the fragment is appended to the task tail
    # AFTER that closing bracket (66-PATTERNS.md build_prompt integration).
    # We use the unique transition-shape substring "in the live audio" as
    # the anchor: anything FOLLOWING the anchor is fragment, and the
    # strongest record_id must appear in that tail (the cite-EXACTLY-ONCE
    # instruction interpolates recall_moments[0].record_id once).
    assert "in the live audio" in out, (
        "fragment marker missing — recall_fragment_for_event did not append "
        "the transition-shape fragment for TRACK_CHANGE"
    )
    fragment_start = out.index("in the live audio")
    fragment_portion = out[fragment_start:]

    # The strongest record_id is interpolated into the fragment (the only
    # cite the fragment instructs Gemini to emit).
    assert strongest.record_id in fragment_portion, (
        "strongest survivor's record_id must appear in the fragment portion"
    )
    # The weaker survivors' record_ids must NOT appear in the fragment
    # portion (they ride along ONLY in the upstream evidence_line block).
    assert second.record_id not in fragment_portion, (
        f"second-strongest record_id {second.record_id!r} leaked into the "
        "fragment portion — the structural max-1-per-turn property is broken"
    )
    assert third.record_id not in fragment_portion, (
        f"third-strongest record_id {third.record_id!r} leaked into the "
        "fragment portion — the structural max-1-per-turn property is broken"
    )


def test_transition_wins_track_change_overlap():
    """COPILOT-02 — on TRACK_CHANGE (which is in BOTH the transition-shape
    and the vocabulary event gates per CONTEXT.md Area 1 Q1+Q2),
    transition-shape WINS over vocabulary.

    Rationale (Pitfall 5 + Open Q1 in 66-RESEARCH.md): TRACK_CHANGE is a
    transition moment by definition; the comparison shape ("compare NOW vs
    THEN") is more concrete + actionable than a vocabulary echo. PHASE-only
    is where the vocabulary fragment dominates.

    Asserts via the two unique substrings — transition-shape's marker
    appears, vocabulary's marker does NOT, on a TRACK_CHANGE turn with
    non-empty survivors.

    RED reason: helper does not exist yet.
    """
    try:
        from vibemix.state.coach import recall_fragment_for_event  # noqa: F401
    except ImportError:
        import pytest

        pytest.fail(
            "recall_fragment_for_event symbol missing from "
            "vibemix.state.coach — Plan 02 Task 2 must add it (COPILOT-02)"
        )

    survivors = _phase_66_record_stubs(n=2)
    ev = _ev("TRACK_CHANGE", {"prev_track": "X", "new_track": "Y"})
    out = AICoach.build_prompt(ev, recall_moments=survivors)
    # Transition fragment marker MUST appear on the TRACK_CHANGE overlap.
    assert "in the live audio" in out, (
        "transition-shape fragment must win on TRACK_CHANGE"
    )
    # Vocabulary fragment marker MUST NOT appear — only one fragment per turn.
    assert "echo your own past words" not in out, (
        "vocabulary fragment leaked into a TRACK_CHANGE turn — transition "
        "must win the overlap (Pitfall 5 / Open Q1)"
    )
    # No registry_snapshot was threaded → no evidence_corpus footer should
    # appear in the output. Defense in depth: pins that the recall fragment
    # integration does not accidentally synthesize a corpus footer.
    # (Plan 02 Task 2 fix-up — Wave 0 left this as ``out_default`` which is
    # an undefined name; the intended assertion target is ``out``.)
    assert "evidence_corpus" not in out
