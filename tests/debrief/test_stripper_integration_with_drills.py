# SPDX-License-Identifier: Apache-2.0
"""Plan 29-07 Task 1: per-field citation gate on drills.

Each of behavior / impact / action_recommended MUST contain ≥ 1
citation. Drills without are dropped, retried, then surfaced as a typed
DrillsGenerationError.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief.drills import (
    Drill,
    Drills,
    DrillsGenerationError,
    generate_drills,
)


SNAPSHOT = {
    "ev": {"MIX_MOVE": [83.0], "PHASE": [120.0]},
    "track": {"t1": [60.0]},
}


def _make_response(drills_list: list[Drill]):
    parsed = Drills(drills=drills_list)
    return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())


def _ok_drill() -> Drill:
    return Drill(
        situation="S",
        behavior="B [ev:MIX_MOVE@01:23]",
        impact="I [ev:PHASE@02:00]",
        action_recommended="A [track:t1]",
        citation="[ev:MIX_MOVE@01:23]",
    )


def _drill_missing_behavior_citation() -> Drill:
    return Drill(
        situation="S",
        behavior="B uncited",  # no citation!
        impact="I [ev:PHASE@02:00]",
        action_recommended="A [track:t1]",
        citation="[ev:MIX_MOVE@01:23]",  # canonical citation resolves fine
    )


def test_drill_with_uncited_behavior_triggers_retry():
    """First attempt has 1 drill with uncited behavior → retry with all-good."""
    bad = _drill_missing_behavior_citation()
    good = _ok_drill()
    client = MagicMock()
    client.models.generate_content.side_effect = [
        _make_response([bad, good, good]),
        _make_response([good, good, good]),
    ]
    drills = generate_drills(client, "critique", ["c"], SNAPSHOT, max_retries=2)
    assert len(drills.drills) == 3
    assert client.models.generate_content.call_count == 2


def test_all_drills_pass_per_field_check():
    client = MagicMock()
    client.models.generate_content.return_value = _make_response(
        [_ok_drill() for _ in range(3)]
    )
    drills = generate_drills(client, "critique", ["c"], SNAPSHOT)
    assert len(drills.drills) == 3
    assert client.models.generate_content.call_count == 1


def test_persistent_uncited_field_raises_after_retries():
    bad = _drill_missing_behavior_citation()
    client = MagicMock()
    client.models.generate_content.return_value = _make_response(
        [bad, bad, bad]
    )
    with pytest.raises(DrillsGenerationError) as ei:
        generate_drills(client, "critique", ["c"], SNAPSHOT, max_retries=2)
    assert ei.value.reason == "drills_generation_failed"
