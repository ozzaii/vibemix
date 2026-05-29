# SPDX-License-Identifier: Apache-2.0
"""Learn session events must be useful to the existing debrief seam."""
from __future__ import annotations

from vibemix.debrief.main import _build_cited_critique
from vibemix.debrief.profile_writeback import write_back_profile


def test_debrief_critique_consumes_learn_action_events_with_registry_citation() -> None:
    critique = _build_cited_critique(
        [
            {
                "t": 12.4,
                "kind": "learn_action_observed",
                "lesson_id": "L1.03",
                "step_id": "L1.03.practice",
                "observed_control_id": "eq_hi:A",
                "expected_control_id": "eq_hi:A",
                "source": "midi",
                "matched": True,
                "evidence_time": 12.3,
            }
        ],
        [],
    )

    assert "Learn L1.03 step L1.03.practice" in critique
    assert "learner matched eq_hi:A via midi" in critique
    assert "[midi:eq_hi:A@12.300]" in critique


def test_debrief_critique_keeps_cited_learn_tutor_lines() -> None:
    critique = _build_cited_critique(
        [
            {
                "t": 20.0,
                "kind": "learn_tutor_speak",
                "lesson_id": "L3.02",
                "tts_marker": "L302.prepared_pool",
                "text": "your prepared pool has five playable tracks.",
                "citations": ["[track:abc123]"],
            },
            {
                "t": 22.0,
                "kind": "learn_tutor_speak",
                "lesson_id": "L1.01",
                "tts_marker": "L101.beat0",
                "text": "uncited fixture copy should not become debrief evidence.",
                "citations": [],
            },
        ],
        [],
    )

    assert "Learn tutor L3.02 L302.prepared_pool" in critique
    assert "[track:abc123]" in critique
    assert "uncited fixture copy" not in critique


def test_profile_writeback_receives_structured_learn_events() -> None:
    seen: dict = {}
    learn_event = {
        "t": 12.4,
        "kind": "learn_action_observed",
        "lesson_id": "L1.03",
        "observed_control_id": "eq_hi:A",
        "matched": True,
    }

    wrote = write_back_profile(
        [learn_event],
        {"midi": {"eq_hi:A": [12.3]}},
        consent_loader=lambda: True,
        prior_loader=lambda: {"preferred_genre": "house"},
        builder=lambda prior, events, evidence, *, consent: seen.update(
            prior=prior,
            events=events,
            evidence=evidence,
            consent=consent,
        )
        or {"preferred_genre": "house"},
        saver=lambda _profile: None,
    )

    assert wrote is True
    assert seen["events"] == [learn_event]
    assert seen["evidence"] == {"midi": {"eq_hi:A": [12.3]}}
    assert seen["consent"] is True
