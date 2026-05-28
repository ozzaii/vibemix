# SPDX-License-Identifier: Apache-2.0
"""Skill-recognizer unit suite — the MAST-02/03 anti-slop spine.

Phase 103 Plan 02 (v11.0 "Earned"). ``skill_recognizer.recognize`` maps a
detected live event to the skill(s) it demonstrates via a reverse map keyed on
the REAL ``state/event_detector.py`` event-type string literals, then grants
mastery credit ONLY when an INJECTED citation predicate resolves true. The
headline product spine is MAST-03: a fabricated / un-cited event grants ZERO
mastery credit — the SAME event differing only in its citation predicate is the
positive-vs-negative control (``test_uncited_event_grants_zero_mastery_credit``).

The second headline is the honest-uncreditable decision (Finding #1): in v11.0
``beatmatching`` + ``harmonic_mixing`` have NO clean citable production event
(sync is sub-significance MIDI; harmonic events default-OFF). They are NEVER
proxy-credited — no map entry, no MIX_MOVE resolution, capped at Competent. The
unsignalled-skills test makes both Competent first, so the assertion isolates
the no-creditable-event reason (NOT an accidental Competent gate).

The recognizer is exercised entirely offline with synthetic events (a tiny
SimpleNamespace, never a real MusicState) + synthetic predicates
(``cited``/``uncited``). One integration-flavored test (Task 3) proves the live
``EvidenceRegistry.has``-wrapping predicate shape resolves; the rest stay
registry-free for purity.

REQ-IDs: MAST-02 (reverse map over the existing taxonomy — no new detectors),
MAST-03 (HEADLINE citation gate; un-cited/fabricated → zero credit).
"""
from __future__ import annotations

from types import SimpleNamespace

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_recognizer import recognize
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree

# A fixed injected timestamp — recognize/record_live_demo never call a clock;
# the caller supplies ``now`` so the credit path stays deterministic.
_NOW = "2026-05-29T12:00:00Z"


# --- synthetic citation predicates (keep the engine island-clean) ----------
def _cited(_s: str, _k: str, _t: float) -> bool:
    """Every citation resolves — the live event IS grounded."""
    return True


def _uncited(_s: str, _k: str, _t: float) -> bool:
    """No citation resolves — the event is fabricated / un-cited."""
    return False


def _event(ev_type: str, *, t: float = 10.0, moves=None):
    """A synthetic Event stand-in: a tiny object with ``.type`` / ``.extra`` /
    ``.t_session``. NOT a real MusicState — the recognizer must never require
    one (it consumes only the string contract)."""
    extra = {"moves": list(moves)} if moves else {}
    return SimpleNamespace(type=ev_type, extra=extra, t_session=t)


# --- Competent fixtures (mirror test_skill_tree.py::_competent_eq_progress) --
def _complete_all(progress: LearnProgress, lesson_ids, *, strikes: int = 0) -> None:
    for lid in lesson_ids:
        progress.lessons[lid] = {
            "completed": True,
            "completed_at": "2026-05-29T00:00:00Z",
            "strikes_used": int(strikes),
        }


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    """Make one skill Competent in-place: complete its manifest lessons
    first-try AND set its gating recital flag."""
    spec = SKILL_MANIFEST[skill_id]
    _complete_all(progress, spec.lesson_ids, strikes=0)
    setattr(progress, spec.gate, True)


def _competent_progress(*skill_ids: str) -> LearnProgress:
    """A LearnProgress where each named skill is Competent (so recognize is
    not a MAST-01 no-op for it)."""
    progress = LearnProgress()
    for skill_id in skill_ids:
        _make_competent(progress, skill_id)
    for skill_id in skill_ids:
        assert SkillTree().compute(progress)[skill_id].competent is True, (
            f"fixture error: {skill_id} is not Competent"
        )
    return progress


def _count(progress: LearnProgress, skill_id: str) -> int:
    block = progress.skills.get(skill_id, {})
    return int(block.get("live_proof_count", 0) or 0)


# ---------------------------------------------------------------------------
# MAST-03 positive control: a cited event credits a Competent skill
# ---------------------------------------------------------------------------
def test_cited_event_grants_credit() -> None:
    """A Competent eq_mixing + a cited MIX_MOVE carrying an EQ-band move →
    live_proof_count for eq_mixing increments by exactly 1."""
    progress = _competent_progress("eq_mixing")
    ev = _event("MIX_MOVE", moves=["A_low: open→killed (big twist)"])

    credited = recognize(ev, citation_check=_cited, progress=progress, now=_NOW)

    assert "eq_mixing" in credited
    assert _count(progress, "eq_mixing") == 1


# ---------------------------------------------------------------------------
# MAST-03 HEADLINE: an un-cited / fabricated event grants ZERO credit
# ---------------------------------------------------------------------------
def test_uncited_event_grants_zero_mastery_credit() -> None:
    """The anti-slop spine: the SAME MIX_MOVE event, fed with a citation
    predicate that resolves False, grants ZERO credit. Only the citation
    differs between this and ``test_cited_event_grants_credit`` — proving the
    citation gate is the SOLE arbiter (a fabricated event cannot fake mastery).
    """
    progress = _competent_progress("eq_mixing")
    ev = _event("MIX_MOVE", moves=["A_low: open→killed (big twist)"])

    credited = recognize(ev, citation_check=_uncited, progress=progress, now=_NOW)

    assert credited == []  # nothing credited
    assert _count(progress, "eq_mixing") == 0  # the bar did not move


# ---------------------------------------------------------------------------
# MAST-02: the reverse map credits the 4 clean skills from REAL event types
# ---------------------------------------------------------------------------
def test_event_skill_map_credits_real_events() -> None:
    """A cited LAYER_ARRIVAL credits transitions; a cited PHASE (and
    PHRASE_BOUNDARY) credits phrasing_performance; a cited MIX_MOVE with a
    ``_play→``/``xfader`` move credits deck_control; an unmapped event type
    (HEARTBEAT) credits nothing."""
    progress = _competent_progress(
        "transitions", "phrasing_performance", "deck_control"
    )

    # LAYER_ARRIVAL → transitions.
    credited = recognize(
        _event("LAYER_ARRIVAL", t=11.0),
        citation_check=_cited,
        progress=progress,
        now=_NOW,
    )
    assert credited == ["transitions"]
    assert _count(progress, "transitions") == 1

    # PHASE → phrasing_performance.
    credited = recognize(
        _event("PHASE", t=12.0),
        citation_check=_cited,
        progress=progress,
        now=_NOW,
    )
    assert credited == ["phrasing_performance"]
    assert _count(progress, "phrasing_performance") == 1

    # PHRASE_BOUNDARY → phrasing_performance (the genre-chain variant).
    credited = recognize(
        _event("PHRASE_BOUNDARY", t=13.0),
        citation_check=_cited,
        progress=progress,
        now=_NOW,
    )
    assert credited == ["phrasing_performance"]
    assert _count(progress, "phrasing_performance") == 2

    # MIX_MOVE with a play-toggle move → deck_control.
    credited = recognize(
        _event("MIX_MOVE", t=14.0, moves=["A_play→ON"]),
        citation_check=_cited,
        progress=progress,
        now=_NOW,
    )
    assert credited == ["deck_control"]
    assert _count(progress, "deck_control") == 1

    # An unmapped event type credits nothing.
    credited = recognize(
        _event("HEARTBEAT", t=15.0),
        citation_check=_cited,
        progress=progress,
        now=_NOW,
    )
    assert credited == []


# ---------------------------------------------------------------------------
# MAST-02 HEADLINE (anti-slop): beatmatching/harmonic_mixing never auto-master
# ---------------------------------------------------------------------------
def test_unsignalled_skills_never_auto_master() -> None:
    """Finding #1 — honest-uncreditable: beatmatching + harmonic_mixing have no
    clean citable production event in v11.0, so NO event of ANY type (cited or
    not) ever advances them. Both are made Competent first, so the ONLY thing
    stopping Mastered is the ABSENCE of a creditable event (the honest decision),
    not an accidental Competent gate. Feed a cited stream of EVERY mapped event
    type and assert both stay live_proof_count=0 / mastered=False."""
    # Make every skill Competent — including the two unsignalled ones.
    progress = _competent_progress(
        "eq_mixing",
        "transitions",
        "phrasing_performance",
        "deck_control",
        "beatmatching",
        "harmonic_mixing",
    )

    # A cited stream of every mapped event type (distinct timestamps so dedup
    # does not collapse them).
    stream = [
        _event("MIX_MOVE", t=20.0, moves=["A_low: open→killed (big twist)"]),
        _event("MIX_MOVE", t=21.0, moves=["A_play→ON"]),
        _event("LAYER_ARRIVAL", t=22.0),
        _event("PHASE", t=23.0),
        _event("PHRASE_BOUNDARY", t=24.0),
    ]
    for ev in stream:
        recognize(ev, citation_check=_cited, progress=progress, now=_NOW)

    for unsignalled in ("beatmatching", "harmonic_mixing"):
        assert _count(progress, unsignalled) == 0, (
            f"{unsignalled} was proxy-credited — it must be honest-uncreditable"
        )
        sp = SkillTree().compute(progress)[unsignalled]
        assert sp.mastered is False
        # And the recognizer's own derived view agrees they never master.
        assert sp.stage != "mastered"


# ---------------------------------------------------------------------------
# MAST-04: event-identity dedup — no double-count of one fire
# ---------------------------------------------------------------------------
def test_event_identity_dedup_no_double_count() -> None:
    """Feeding the SAME ``(type, round(t,1))`` MIX_MOVE twice in one
    recognize-batch credits eq_mixing exactly once. BUT one MIX_MOVE that maps
    to BOTH eq_mixing AND deck_control credits each once (NOT a double-count)."""
    # (a) same identity twice → one credit. A shared ``seen`` set threads the
    # identity across the two calls in the batch.
    progress = _competent_progress("eq_mixing")
    ev = _event("MIX_MOVE", t=30.0, moves=["A_low: open→killed (big twist)"])
    seen: set = set()
    recognize(ev, citation_check=_cited, progress=progress, now=_NOW, _seen=seen)
    recognize(ev, citation_check=_cited, progress=progress, now=_NOW, _seen=seen)
    assert _count(progress, "eq_mixing") == 1  # second call is a no-op

    # (b) one event crediting TWO distinct skills is correct, not a double-count.
    progress2 = _competent_progress("eq_mixing", "deck_control")
    both = _event(
        "MIX_MOVE",
        t=31.0,
        moves=["A_low: open→killed (big twist)", "A_play→ON"],
    )
    credited = recognize(both, citation_check=_cited, progress=progress2, now=_NOW)
    assert set(credited) == {"eq_mixing", "deck_control"}
    assert _count(progress2, "eq_mixing") == 1
    assert _count(progress2, "deck_control") == 1


# ---------------------------------------------------------------------------
# MAST-03 + MAST-04: un-cited events never reach Mastered, even over threshold
# ---------------------------------------------------------------------------
def test_uncited_does_not_reach_mastered_even_over_threshold() -> None:
    """N un-cited events never flip Mastered — the citation gate composes with
    the threshold flip. A flood of fabricated events cannot fake a Mastered
    skill no matter how many of them there are."""
    progress = _competent_progress("eq_mixing")
    threshold = SKILL_MANIFEST["eq_mixing"].mastered_threshold

    for i in range(threshold * 3):
        ev = _event(
            "MIX_MOVE",
            t=40.0 + i,  # distinct identities so dedup is not the reason
            moves=["A_low: open→killed (big twist)"],
        )
        recognize(ev, citation_check=_uncited, progress=progress, now=_NOW)

    assert _count(progress, "eq_mixing") == 0
    sp = SkillTree().compute(progress)["eq_mixing"]
    assert sp.mastered is False
    assert sp.stage != "mastered"
