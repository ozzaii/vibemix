# SPDX-License-Identifier: Apache-2.0
"""The live Judge producer: judge_and_record — ground + persist, abstain-first.

JUDGED  -> write a resolvable [judge:] citation (the voiced verdict atom) +
           log a transition_judged row carrying a real score.
ABSTAIN -> log the abstain (calibration/debrief need it) with NO citation and
           score=None (honest-null: nothing to ground, nothing voiced).
Non-fatal: a None registry/recorder never raises (the live loop is per-loop
defensive).
"""
from __future__ import annotations

from vibemix.intel.transition_judge import TRANSITION_JUDGED_KIND
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.live_signal import LaneObservation, LiveSignalFrame
from vibemix.state.transition_judge_runtime import judge_and_record


class _FakeRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: object) -> None:
        self.events.append((kind, fields))


def _lane(camelot: str) -> LaneObservation:
    return LaneObservation(
        active=True, source_trusted=True, camelot=camelot,
        bands={"sub": 0.3, "low": 0.3, "mid": 0.2, "high": 0.2}, rms=0.2, track_id="t",
    )


def _judged_frame(t: float = 128.4) -> LiveSignalFrame:
    # Two trusted compatible keys (harmonic 0.75) + both basslines up (bass 0.0)
    # = 2 non-null signals -> JUDGED.
    return LiveSignalFrame(
        t_session=t, policy="supported_verdict", routing_enabled=True,
        lanes={"A": _lane("8A"), "B": _lane("9A")},
    )


def _abstained_frame(t: float = 50.0) -> LiveSignalFrame:
    return LiveSignalFrame(
        t_session=t, policy="supported_verdict", routing_enabled=False,
        lanes={"A": _lane("8A"), "B": _lane("9A")},
    )


def test_judged_writes_resolvable_citation_and_logs_row():
    reg = EvidenceRegistry()
    rec = _FakeRecorder()
    verdict = judge_and_record(_judged_frame(), registry=reg, recorder=rec,
                               track_a="t1", track_b="t2")
    assert verdict.verdict_state == "judged"
    # The voiced atom resolves under Invariant #2.
    assert reg.has("judge", "transition@128.4", 128.4) is True
    kind, fields = rec.events[-1]
    assert kind == TRANSITION_JUDGED_KIND
    assert fields["citation_id"] == "judge:transition@128.4"
    assert fields["score"] is not None
    assert fields["track_a"] == "t1" and fields["track_b"] == "t2"


def test_abstained_grounds_nothing_but_records_the_silence():
    reg = EvidenceRegistry()
    rec = _FakeRecorder()
    verdict = judge_and_record(_abstained_frame(), registry=reg, recorder=rec,
                               track_a="t1", track_b="t2")
    assert verdict.verdict_state == "abstained"
    # Honest-null: no fabricated citation.
    assert reg.snapshot().get("judge", {}) == {}
    kind, fields = rec.events[-1]
    assert kind == TRANSITION_JUDGED_KIND
    assert fields["score"] is None
    assert "citation_id" not in fields  # nothing voiced -> no citation field
    assert fields["abstain_reason"] == "routing_disabled"


def test_none_registry_and_recorder_never_raise():
    verdict = judge_and_record(_judged_frame(), registry=None, recorder=None,
                               track_a=None, track_b=None)
    assert verdict.verdict_state == "judged"
