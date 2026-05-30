# SPDX-License-Identifier: Apache-2.0
"""4d — the live Judge join (post-judge credit glue).

``judge_and_record`` writes a ``[judge:transition@t]`` citation, but the v11
recognizer gates Mastered credit on an ``[ev:transition_judged]`` citation
(skill_recognizer.py:261 hardcodes ``citation_check("ev", ev_type, t)``). So the
live caller must ALSO write the ``ev`` atom for a JUDGED verdict, then feed the
existing ``_credit_live_skill_demo`` path. ``_credit_judged_transition`` is that
glue: on JUDGED it grounds the ev-citation + credits the demonstrated skill; on
ABSTAINED (honest-null) it credits nothing and writes no citation. Never raises.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree
from vibemix.runtime.coach import _credit_judged_transition
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.music_state import MusicState


def _competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lid in spec.lesson_ids:
        progress.lessons[lid] = {
            "completed": True, "completed_at": "2026-05-30T00:00:00Z", "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
    assert SkillTree().compute(progress)[skill_id].competent is True


def _verdict(state: str, components: dict) -> SimpleNamespace:
    return SimpleNamespace(verdict_state=state, components=components)


def _state() -> MusicState:
    st = MusicState()
    st.set_start_at = time.time()
    return st


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


def test_judged_compatible_verdict_writes_ev_citation_and_credits_harmonic():
    reg = EvidenceRegistry()
    prog = LearnProgress(); _competent(prog, "harmonic_mixing")
    st = _state()

    credited = _credit_judged_transition(
        _verdict("judged", {"harmonic": 0.75}), st,
        evidence_registry=reg, learn_progress=prog,
    )

    assert "harmonic_mixing" in credited
    assert _count(prog, "harmonic_mixing") == 1
    # the recognizer's credit-gate citation [ev:transition_judged] was grounded
    assert reg.has("ev", "transition_judged", max(0.0, time.time() - st.set_start_at), tol=1.0)


def test_abstained_verdict_credits_nothing_and_writes_no_citation():
    reg = EvidenceRegistry()
    prog = LearnProgress(); _competent(prog, "harmonic_mixing")
    st = _state()

    credited = _credit_judged_transition(
        _verdict("abstained", {}), st,
        evidence_registry=reg, learn_progress=prog,
    )

    assert credited == []
    assert _count(prog, "harmonic_mixing") == 0
    # abstain-first: no [ev:transition_judged] citation, so nothing can credit
    assert not reg.has("ev", "transition_judged", 0.0, tol=2.0)


def test_judged_clash_verdict_credits_no_skill():
    # A JUDGED-but-CLASH verdict (harmonic 0.0) is a real judged event, but a
    # clash is NOT a harmonic-mixing demonstration — credit stays zero.
    reg = EvidenceRegistry()
    prog = LearnProgress(); _competent(prog, "harmonic_mixing")
    st = _state()

    credited = _credit_judged_transition(
        _verdict("judged", {"harmonic": 0.0}), st,
        evidence_registry=reg, learn_progress=prog,
    )

    assert credited == []
    assert _count(prog, "harmonic_mixing") == 0


def test_never_raises_on_broken_inputs():
    # A producer hiccup must never wedge the reaction loop.
    st = _state()
    assert _credit_judged_transition(None, st, evidence_registry=None, learn_progress=None) == []
    assert _credit_judged_transition(
        _verdict("judged", {"harmonic": 0.75}), st,
        evidence_registry=EvidenceRegistry(), learn_progress=object(),  # no .skills
    ) == []
