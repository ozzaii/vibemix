# SPDX-License-Identifier: Apache-2.0
"""§EARNED-LIVE-MASTERED-VERIFY backend wiring — coach_loop skill-credit glue.

Phase 103 (v11.0 "Earned") live wiring. The co-host event loop credits the
v11.0 skill(s) a CITED live event demonstrates via the (until-now ORPHANED)
``learn/skill_recognizer.recognize`` spine. This suite pins the new thin glue
helper ``runtime/coach.py::_credit_live_skill_demo`` — the never-raises boundary
that closes the real ``EvidenceRegistry.has`` over the citation gate, computes
the session-relative ``t_session`` the EventDetector actually wrote
(``event_detector.py:508`` — ``max(0.0, now - state.set_start_at)``, wall clock),
and persists the live-portion on credit.

The MAST-03 anti-slop control is the SAME event differing ONLY in whether its
citation resolves: cited → credit; un-cited → ZERO credit (no bar moves). The
``recognize`` engine itself is exhaustively unit-tested in
``tests/learn/test_skill_recognizer.py``; this suite proves the LIVE wiring
threads the real registry + real ``LearnProgress`` + the real ``set_start_at``
clock correctly, and that a credit failure never wedges the reaction loop.
"""
from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibemix.learn.progress import LearnProgress, load_progress
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree
from vibemix.runtime.coach import _credit_live_skill_demo
from vibemix.state.evidence_registry import EvidenceRegistry


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    """Make one skill Competent in-place (mirror test_skill_recognizer fixture):
    complete its manifest lessons first-try AND set its gating recital flag."""
    spec = SKILL_MANIFEST[skill_id]
    for lid in spec.lesson_ids:
        progress.lessons[lid] = {
            "completed": True,
            "completed_at": "2026-05-29T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
    assert SkillTree().compute(progress)[skill_id].competent is True, (
        f"fixture error: {skill_id} not Competent"
    )


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


@pytest.fixture()
def _redirect_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """save_progress() must write to tmp, NOT clobber the real
    ~/.cache/vibemix/learn-progress.json (CLAUDE.md cache-path gotcha)."""
    monkeypatch.setenv(
        "VIBEMIX_LEARN_PROGRESS_PATH", str(tmp_path / "learn-progress.json")
    )
    return tmp_path / "learn-progress.json"


def _state(t_into_set: float = 10.0) -> SimpleNamespace:
    # The helper reads only ``state.set_start_at``. Place the set start so the
    # helper's ``time.time() - set_start_at`` lands ~``t_into_set``, matching the
    # citation we write (well within the ±1.0s ``has`` tolerance).
    return SimpleNamespace(set_start_at=time.time() - t_into_set)


def _event(ev_type: str, moves=None) -> SimpleNamespace:
    # Mirrors the REAL state/event.py::Event shape the recognizer reads: .type +
    # .extra (no session-relative time attr — that rides via the helper's event_t).
    return SimpleNamespace(
        type=ev_type, extra=({"moves": list(moves)} if moves else {})
    )


def test_cited_layer_arrival_credits_transitions(_redirect_progress: Path) -> None:
    """MAST-03 positive control: a Competent ``transitions`` + a cited
    LAYER_ARRIVAL → live_proof_count for transitions increments by exactly 1,
    and the credit is persisted to the (redirected) progress file."""
    progress = LearnProgress()
    _make_competent(progress, "transitions")
    reg = EvidenceRegistry()
    reg.write("ev", "LAYER_ARRIVAL", 10.0)  # the citation the EventDetector wrote
    state = _state(10.0)

    credited = _credit_live_skill_demo(
        _event("LAYER_ARRIVAL"),
        state,
        evidence_registry=reg,
        learn_progress=progress,
    )

    assert credited == ["transitions"]
    assert _count(progress, "transitions") == 1
    # persisted, not just mutated in memory
    reloaded, _ = load_progress()
    assert int(reloaded.skills.get("transitions", {}).get("live_proof_count", 0)) == 1


def test_uncited_layer_arrival_grants_zero_credit(_redirect_progress: Path) -> None:
    """MAST-03 negative control: SAME Competent skill + SAME event, but NO
    citation written → recognize's gate denies → ZERO credit, no bar moves."""
    progress = LearnProgress()
    _make_competent(progress, "transitions")
    reg = EvidenceRegistry()  # empty — no citation written
    state = _state(10.0)

    credited = _credit_live_skill_demo(
        _event("LAYER_ARRIVAL"),
        state,
        evidence_registry=reg,
        learn_progress=progress,
    )

    assert credited == []
    assert _count(progress, "transitions") == 0


def test_gate_off_when_handles_absent_is_noop() -> None:
    """None registry/progress (boot-IPC-failure / Learn-absent path) → [] with
    no I/O. The live caller passes both; legacy/test callers may pass neither."""
    assert (
        _credit_live_skill_demo(
            _event("LAYER_ARRIVAL"),
            _state(),
            evidence_registry=None,
            learn_progress=None,
        )
        == []
    )
    assert (
        _credit_live_skill_demo(
            _event("LAYER_ARRIVAL"),
            _state(),
            evidence_registry=EvidenceRegistry(),
            learn_progress=None,
        )
        == []
    )


def test_never_raises_on_broken_progress(_redirect_progress: Path) -> None:
    """A garbage progress object must degrade to [] (never wedge the reaction
    loop) — the helper's defensive guard, belt-and-braces over recognize's own
    never-raises posture."""
    reg = EvidenceRegistry()
    reg.write("ev", "LAYER_ARRIVAL", 10.0)
    broken = SimpleNamespace()  # not a LearnProgress — no .skills / .lessons

    out = _credit_live_skill_demo(
        _event("LAYER_ARRIVAL"),
        _state(10.0),
        evidence_registry=reg,
        learn_progress=broken,
    )

    assert out == []


def test_cited_mix_move_credits_both_eq_and_deck(_redirect_progress: Path) -> None:
    """One cited MIX_MOVE carrying BOTH an EQ-band move and a play move credits
    BOTH eq_mixing and deck_control from the single "ev"/"MIX_MOVE" citation —
    proving the helper plumbs event.extra["moves"] through to the recognizer's
    move-substring resolution end-to-end (one event, two distinct skills)."""
    progress = LearnProgress()
    _make_competent(progress, "eq_mixing")
    _make_competent(progress, "deck_control")
    reg = EvidenceRegistry()
    reg.write("ev", "MIX_MOVE", 10.0)  # one citation, keyed on the event type
    state = _state(10.0)

    credited = _credit_live_skill_demo(
        _event("MIX_MOVE", moves=["A_low: open→killed (big twist)", "A_play→cue"]),
        state,
        evidence_registry=reg,
        learn_progress=progress,
    )

    assert set(credited) == {"eq_mixing", "deck_control"}
    assert _count(progress, "eq_mixing") == 1
    assert _count(progress, "deck_control") == 1


def test_unset_set_start_at_self_cancels(_redirect_progress: Path) -> None:
    """The realistic unset-clock edge: set_start_at == 0.0 makes the helper
    compute t_session ≈ time.time() (a unix-sized value) — IDENTICAL to what the
    EventDetector wrote with the same `now - 0.0`, so they still match within
    ±1.0s and credit resolves (no silent denial from the unset default)."""
    progress = LearnProgress()
    _make_competent(progress, "transitions")
    reg = EvidenceRegistry()
    reg.write("ev", "LAYER_ARRIVAL", time.time())  # what _fire writes when set_start_at==0
    state = SimpleNamespace(set_start_at=0.0)

    credited = _credit_live_skill_demo(
        _event("LAYER_ARRIVAL"),
        state,
        evidence_registry=reg,
        learn_progress=progress,
    )

    assert credited == ["transitions"]
    assert _count(progress, "transitions") == 1


def test_never_raises_on_raising_registry(_redirect_progress: Path) -> None:
    """The other half of the never-raises contract: a registry whose `has`
    raises must degrade to [] (credit failure must never wedge the reaction
    loop), not propagate out of the helper."""

    class _BoomRegistry:
        def has(self, *a: object, **k: object) -> bool:
            raise RuntimeError("registry boom")

    progress = LearnProgress()
    _make_competent(progress, "transitions")

    out = _credit_live_skill_demo(
        _event("LAYER_ARRIVAL"),
        _state(10.0),
        evidence_registry=_BoomRegistry(),
        learn_progress=progress,
    )

    assert out == []
    assert _count(progress, "transitions") == 0


def test_unmapped_event_credits_nothing(_redirect_progress: Path) -> None:
    """An event type with no EVENT_SKILL_MAP entry (e.g. HEARTBEAT) credits
    nothing even when cited — no proxy-credit, no new detector."""
    progress = LearnProgress()
    _make_competent(progress, "transitions")
    reg = EvidenceRegistry()
    reg.write("ev", "HEARTBEAT", 10.0)

    credited = _credit_live_skill_demo(
        _event("HEARTBEAT"),
        _state(10.0),
        evidence_registry=reg,
        learn_progress=progress,
    )

    assert credited == []
    assert _count(progress, "transitions") == 0
