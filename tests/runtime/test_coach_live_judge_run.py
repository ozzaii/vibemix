# SPDX-License-Identifier: Apache-2.0
"""4d — the live Judge RUN glue (`_run_live_judge`), the coach_loop producer.

`_credit_judged_transition` (tested in test_coach_judge_join.py) is the *credit*
half. `_run_live_judge` is the *producer*: on a transition it resolves per-lane
meta from the SAME deck-state the prompt reads (read-only — single-writer
respected), assembles the typed `LiveSignalFrame` from the live capture rings,
runs `judge_and_record` (grounds `[judge:transition@t]` + persists the row), then
feeds `_credit_judged_transition`. Abstain-first by construction:

- No capture            -> returns None, nothing happens.
- Master-only rig       -> routing disabled -> Judge abstains "routing_disabled",
  no citation, no credit (Kaan's CURRENT rig — the honest-null default).
- Non-supported policy  -> Judge abstains "policy_not_supported_verdict".
- Full two-deck rig     -> compatible camelot + per-lane bass -> JUDGED, writes
  the `[ev:transition_judged]` credit-gate citation, credits harmonic_mixing.
- A producer hiccup     -> returns None, never raises (must not wedge reactions).
"""
from __future__ import annotations

import time

import numpy as np

from vibemix.audio.constants import INPUT_SR_TARGET
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, SkillTree
from vibemix.runtime.coach import _run_live_judge
from vibemix.state.deck_state import DeckTrack
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.music_state import MusicState

# --- helpers --------------------------------------------------------------


def _competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lid in spec.lesson_ids:
        progress.lessons[lid] = {
            "completed": True, "completed_at": "2026-05-30T00:00:00Z", "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
    assert SkillTree().compute(progress)[skill_id].competent is True


def _count(progress: LearnProgress, skill_id: str) -> int:
    return int(progress.skills.get(skill_id, {}).get("live_proof_count", 0) or 0)


def _two_deck_state(camelot_a: str = "8A", camelot_b: str = "8A",
                    source: str = "rekordbox_xml") -> MusicState:
    st = MusicState()
    st.set_start_at = time.time()
    st.deck_state.decks = {
        "A": DeckTrack(title="A", track_id="t1", camelot=camelot_a,
                       source=source, confidence=1.0),
        "B": DeckTrack(title="B", track_id="t2", camelot=camelot_b,
                       source=source, confidence=1.0),
    }
    return st


def _bass_pcm(n: int = INPUT_SR_TARGET) -> np.ndarray:
    # A 55 Hz tone parks the energy in sub/low so band_energy_ratios returns a
    # real per-lane spectrum -> the Judge's bass_collision signal is non-null.
    t = np.arange(n) / float(INPUT_SR_TARGET)
    return (0.5 * np.sin(2.0 * np.pi * 55.0 * t)).astype(np.float32)


class _Routing:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled


class _Buf:
    def __init__(self, pcm: np.ndarray) -> None:
        self._pcm = pcm

    def snapshot(self, n: int) -> np.ndarray:
        return self._pcm[:n]


class _Capture:
    """A minimal DeckAudioCapture stand-in (only the fields the adapter reads)."""

    def __init__(self, *, enabled: bool, bands_pcm: np.ndarray | None = None,
                 rms: float = 0.5) -> None:
        self.routing = _Routing(enabled)
        self.last_rms = {"A": rms, "B": rms}
        self.buffers = (
            {"A": _Buf(bands_pcm), "B": _Buf(bands_pcm)} if bands_pcm is not None else {}
        )


# --- tests ----------------------------------------------------------------


def test_run_live_judge_none_capture_returns_none():
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    out = _run_live_judge(
        None, _two_deck_state(), policy="supported_verdict",
        evidence_registry=reg, recorder=None, learn_progress=prog,
    )
    assert out is None
    assert _count(prog, "harmonic_mixing") == 0


def test_run_live_judge_master_only_abstains_no_credit():
    # Kaan's CURRENT rig: routing disabled -> the Judge abstains by construction.
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    st = _two_deck_state()
    verdict = _run_live_judge(
        _Capture(enabled=False), st, policy="supported_verdict",
        evidence_registry=reg, recorder=None, learn_progress=prog,
    )
    assert verdict is not None and verdict.verdict_state == "abstained"
    assert _count(prog, "harmonic_mixing") == 0
    assert not reg.has("ev", "transition_judged", 0.0, tol=5.0)


def test_run_live_judge_blocked_policy_abstains_no_credit():
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    st = _two_deck_state()
    verdict = _run_live_judge(
        _Capture(enabled=True, bands_pcm=_bass_pcm()), st, policy="blocked",
        evidence_registry=reg, recorder=None, learn_progress=prog,
    )
    assert verdict is not None and verdict.verdict_state == "abstained"
    assert _count(prog, "harmonic_mixing") == 0


def test_run_live_judge_full_rig_judges_and_credits_harmonic():
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    st = _two_deck_state(camelot_a="8A", camelot_b="8A")
    verdict = _run_live_judge(
        _Capture(enabled=True, bands_pcm=_bass_pcm()), st, policy="supported_verdict",
        evidence_registry=reg, recorder=None, learn_progress=prog,
    )
    assert verdict is not None and verdict.verdict_state == "judged"
    assert verdict.components.get("harmonic") == 0.75
    assert _count(prog, "harmonic_mixing") == 1
    # the recognizer's credit-gate citation [ev:transition_judged] was grounded
    assert reg.has("ev", "transition_judged", max(0.0, time.time() - st.set_start_at), tol=2.0)


def test_run_live_judge_full_rig_collects_voice_line():
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    st = _two_deck_state(camelot_a="8A", camelot_b="8A")
    lines: list[str] = []
    verdict = _run_live_judge(
        _Capture(enabled=True, bands_pcm=_bass_pcm()),
        st,
        policy="supported_verdict",
        evidence_registry=reg,
        recorder=None,
        learn_progress=prog,
        judge_voice_lines=lines,
    )
    assert verdict is not None and verdict.verdict_state == "judged"
    assert len(lines) == 1
    assert lines[0].startswith("[judge:transition@")
    assert "compatible keys" in lines[0]


def test_run_live_judge_abstain_collects_no_voice_line():
    reg = EvidenceRegistry()
    prog = LearnProgress()
    _competent(prog, "harmonic_mixing")
    st = _two_deck_state()
    lines: list[str] = []
    verdict = _run_live_judge(
        _Capture(enabled=False),
        st,
        policy="supported_verdict",
        evidence_registry=reg,
        recorder=None,
        learn_progress=prog,
        judge_voice_lines=lines,
    )
    assert verdict is not None and verdict.verdict_state == "abstained"
    assert lines == []


def test_run_live_judge_never_raises_on_broken_capture():
    st = _two_deck_state()

    class _Broken:
        def __init__(self) -> None:
            self.routing = _Routing(True)
            self.last_rms: dict = {}

        @property
        def buffers(self):
            raise RuntimeError("boom")

    assert _run_live_judge(
        _Broken(), st, policy="supported_verdict",
        evidence_registry=EvidenceRegistry(), recorder=None, learn_progress=LearnProgress(),
    ) is None
