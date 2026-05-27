# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from vibemix.intel.gold_sampling import sample_transition_candidates

FIXTURES = Path(__file__).parent / "fixtures"


def test_transition_sampler_pulls_non_flattering_review_pool() -> None:
    candidates = json.loads((FIXTURES / "transition_pairs.json").read_text(encoding="utf-8"))

    items = sample_transition_candidates(candidates, n=5, threshold=0.62)

    assert [item.review_item_id for item in items] == [
        "rev_001",
        "rev_002",
        "rev_003",
        "rev_004",
        "rev_005",
    ]
    assert {item.sample_reason for item in items} >= {
        "top_scorer",
        "near_threshold",
        "high_score_high_risk",
        "low_confidence_or_negative",
    }
    assert "tr_004" in {item.candidate_id for item in items}


def test_transition_sampler_is_deterministic_and_bounds_n() -> None:
    candidates = json.loads((FIXTURES / "transition_pairs.json").read_text(encoding="utf-8"))

    first = sample_transition_candidates(candidates, n=3)
    second = sample_transition_candidates(candidates, n=3)

    assert first == second
    assert len(first) == 3


def test_transition_sampler_handles_empty_and_zero_n() -> None:
    assert sample_transition_candidates([], n=5) == ()
    assert sample_transition_candidates([{"candidate_id": "tr_001", "score": 0.9}], n=0) == ()
