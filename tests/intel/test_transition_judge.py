# SPDX-License-Identifier: Apache-2.0
"""The Vibe Judge — abstain-by-construction is the anti-slop spine.

A confidently-wrong quality score is its own hallucination class. These tests
pin that the Judge returns verdict_state='abstained' (NOT a number) whenever its
inputs are untrustworthy — BEFORE any scoring logic is written. Honest-null is
the law: the hakem shuts up rather than lie.
"""
from __future__ import annotations

from vibemix.intel.transition_judge import judge_transition, TransitionVerdict
from vibemix.state.live_signal import LiveSignalFrame, LaneObservation


# Sentinel so a test can pass an *explicit* bands=None (lane has no spectrum)
# distinct from "not specified -> use the default heavy bands".
_DEFAULT_BANDS = object()


def _lane(*, active=True, trusted=True, camelot="8A", bands=_DEFAULT_BANDS, rms=0.2):
    resolved = {"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1} if bands is _DEFAULT_BANDS else bands
    return LaneObservation(
        active=active,
        source_trusted=trusted,
        camelot=camelot,
        bands=resolved,
        rms=rms,
        track_id="t1",
    )


def test_abstains_when_policy_not_supported_verdict():
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="watch",  # not 'supported_verdict'
        routing_enabled=True,
        lanes={"A": _lane(), "B": _lane(camelot="9A")},
    )
    verdict = judge_transition(frame)
    assert isinstance(verdict, TransitionVerdict)
    assert verdict.verdict_state == "abstained"
    assert verdict.score is None
    assert verdict.abstain_reason == "policy_not_supported_verdict"


def test_abstains_when_routing_disabled():
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="supported_verdict",
        routing_enabled=False,  # master-only rig: no per-lane isolation
        lanes={"A": _lane(), "B": _lane(camelot="9A")},
    )
    verdict = judge_transition(frame)
    assert verdict.verdict_state == "abstained"
    assert verdict.abstain_reason == "routing_disabled"


def test_abstains_when_too_few_trustworthy_signals():
    # Both lanes present BUT cross-letter/unknown keys (harmonic abstains) AND no
    # bands (bass-collision abstains) -> < MIN_TRUSTWORTHY_SIGNALS.
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="supported_verdict",
        routing_enabled=True,
        lanes={
            "A": _lane(camelot=None, bands=None),
            "B": _lane(camelot=None, bands=None),
        },
    )
    verdict = judge_transition(frame)
    assert verdict.verdict_state == "abstained"
    assert verdict.abstain_reason == "insufficient_trustworthy_signals"


# --- harmonic signal (the one structurally-sound dimension) ---


def test_harmonic_clash_scores_zero_and_flags():
    # 8A vs 3A is a real same-letter clash (verified against harmonics.is_clash).
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A"), "B": _lane(camelot="3A")},
    )
    v = judge_transition(frame)
    assert "harmonic" in v.components
    assert v.components["harmonic"] == 0.0
    assert "harmonic_clash" in v.risk_flags


def test_harmonic_compatible_capped_at_prior():
    # 8A vs 9A is adjacent = compatible; the prior is capped, never 1.0.
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A"), "B": _lane(camelot="9A")},
    )
    v = judge_transition(frame)
    assert "harmonic" in v.components
    assert v.components["harmonic"] <= 0.75  # adjacency is a prior, not audible truth


def test_harmonic_abstains_on_untrusted_source():
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A", trusted=False), "B": _lane(camelot="9A")},
    )
    v = judge_transition(frame)
    assert "harmonic" not in v.components  # abstained on harmonic; bass may still carry


# --- bass-collision signal (coarse binary, capture-only) ---


def test_bass_collision_both_bass_present_is_mud():
    heavy = {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}  # both basslines up = mud
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A", bands=heavy), "B": _lane(camelot="9A", bands=heavy)},
    )
    v = judge_transition(frame)
    assert v.components["bass_collision"] == 0.0  # collision = mud = bad
    assert "bass_collision" in v.risk_flags


def test_bass_collision_one_killed_is_clean():
    heavy = {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}
    eqd_out = {"sub": 0.02, "low": 0.05, "mid": 0.43, "high": 0.5}  # bass EQ'd out cleanly
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A", bands=heavy), "B": _lane(camelot="9A", bands=eqd_out)},
    )
    v = judge_transition(frame)
    assert v.components["bass_collision"] == 1.0  # clean swap


def test_bass_collision_abstains_without_bands():
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A", bands=None), "B": _lane(camelot="9A", bands=None)},
    )
    v = judge_transition(frame)
    assert "bass_collision" not in v.components  # honest-null; harmonic still carries


def test_judged_blends_harmonic_and_bass():
    # Compatible keys + clean bass swap -> a judged verdict averaging both.
    heavy = {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}
    eqd_out = {"sub": 0.02, "low": 0.05, "mid": 0.43, "high": 0.5}
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane(camelot="8A", bands=heavy), "B": _lane(camelot="9A", bands=eqd_out)},
    )
    v = judge_transition(frame)
    assert v.verdict_state == "judged"
    assert v.score is not None
    assert set(v.components.keys()) == {"harmonic", "bass_collision"}
    assert v.confidence == 1.0  # both signals fired
