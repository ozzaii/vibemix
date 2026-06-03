# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.debrief.main import _build_cited_critique
from vibemix.debrief.stripper import assert_all_cited, strip_uncited_sentences


def test_debrief_critique_emits_cited_line_for_judged_transition() -> None:
    critique = _build_cited_critique(
        [
            {
                "t": 128.4,
                "kind": "transition_judged",
                "verdict_state": "judged",
                "score": 0.71,
                "components": {"harmonic": 0.75, "bass_collision": 1.0},
                "citation_id": "judge:transition@128.4",
                "track_a": "a",
                "track_b": "b",
            }
        ],
        [],
    )

    assert "[judge:transition@128.4]" in critique
    assert "compatible keys" in critique
    assert "clean low end, one bass ducked" in critique
    assert "blend score 0.71/1" in critique
    cleaned, dropped = strip_uncited_sentences(critique)
    assert cleaned == critique
    assert dropped == 0
    assert_all_cited(critique)


def test_debrief_critique_skips_abstain_transition() -> None:
    critique = _build_cited_critique(
        [
            {
                "kind": "transition_judged",
                "verdict_state": "abstained",
                "score": None,
                "abstain_reason": "routing_disabled",
            }
        ],
        [],
    )

    assert critique == ""
    assert "routing_disabled" not in critique


def test_debrief_critique_judged_clash() -> None:
    critique = _build_cited_critique(
        [
            {
                "kind": "transition_judged",
                "verdict_state": "judged",
                "score": 0.2,
                "components": {"harmonic": 0.0, "bass_collision": 0.0},
                "citation_id": "judge:transition@64.0",
            }
        ],
        [],
    )

    assert "key clash" in critique
    assert "both basslines up, low-end mud" in critique
    assert_all_cited(critique)
