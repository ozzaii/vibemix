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


def _lane(*, active=True, trusted=True, camelot="8A", bands=None, rms=0.2):
    return LaneObservation(
        active=active,
        source_trusted=trusted,
        camelot=camelot,
        bands=bands if bands is not None else {"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1},
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
