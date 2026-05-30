# SPDX-License-Identifier: Apache-2.0
"""Judge verdict -> events.jsonl serialization (Step 5).

The pure serialization the (deferred) live-guard wiring will hand to
recorder.log_event. Both judged AND abstained verdicts persist — abstains are
load-bearing for calibration and debrief. Honest-null: abstain score stays None.
"""
from __future__ import annotations

import json

from vibemix.intel.transition_judge import (
    TRANSITION_JUDGED_KIND,
    TransitionVerdict,
    verdict_event_fields,
)


def test_kind_constant():
    assert TRANSITION_JUDGED_KIND == "transition_judged"


def test_judged_verdict_fields_are_complete():
    v = TransitionVerdict(
        verdict_state="judged", score=0.375, confidence=1.0,
        components={"harmonic": 0.75, "bass_collision": 0.0},
        risk_flags=("bass_collision",),
    )
    f = verdict_event_fields(v, track_a="t1", track_b="t2")
    assert f["verdict_state"] == "judged"
    assert f["score"] == 0.375
    assert f["confidence"] == 1.0
    assert f["components"] == {"harmonic": 0.75, "bass_collision": 0.0}
    assert f["risk_flags"] == ["bass_collision"]
    assert f["track_a"] == "t1" and f["track_b"] == "t2"
    assert "abstain_reason" not in f


def test_abstained_verdict_persists_with_none_score():
    # Honest-null: an abstain is recorded (calibration needs it) but never with a
    # fabricated score.
    v = TransitionVerdict(
        verdict_state="abstained", score=None, confidence=0.0,
        abstain_reason="routing_disabled",
    )
    f = verdict_event_fields(v, track_a="t1", track_b="t2")
    assert f["verdict_state"] == "abstained"
    assert f["score"] is None
    assert f["abstain_reason"] == "routing_disabled"
    assert "components" not in f  # nothing to report
    assert "risk_flags" not in f


def test_citation_id_threads_through_when_present():
    v = TransitionVerdict(verdict_state="judged", score=0.9, confidence=1.0,
                          components={"harmonic": 0.75, "bass_collision": 1.0})
    f = verdict_event_fields(v, track_a="t1", track_b="t2", citation_id="judge:abc123")
    assert f["citation_id"] == "judge:abc123"


def test_fields_are_json_serializable():
    # events.jsonl is JSONL — the payload MUST round-trip through json.
    v = TransitionVerdict(
        verdict_state="judged", score=0.5, confidence=0.5,
        components={"harmonic": 0.5}, risk_flags=("harmonic_clash",),
    )
    f = verdict_event_fields(v, track_a="t1", track_b=None)
    line = json.dumps({"t": 1.234, "kind": TRANSITION_JUDGED_KIND, **f})
    back = json.loads(line)
    assert back["kind"] == "transition_judged"
    assert back["track_b"] is None
    assert back["risk_flags"] == ["harmonic_clash"]
