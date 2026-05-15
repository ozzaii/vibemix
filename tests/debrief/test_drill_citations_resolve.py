# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-06: drill citation resolution against EvidenceRegistry snapshot.

The orchestrator (Plan 29-01 Task 2) validates that every drill's
``citation`` field looks up against the snapshot at ±2.0s tolerance
(Phase 20 ``mode="debrief"`` band). Drills with unresolvable citations
trigger a re-prompt; after retries exhaust, the orchestrator raises
:class:`DrillsGenerationError`.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief.drills import (
    Drill,
    Drills,
    DrillsGenerationError,
    _citation_resolves,
    generate_drills,
)


# ---------------------------------------------------------------------------
# Unit — _citation_resolves
# ---------------------------------------------------------------------------


SNAPSHOT = {
    "ev": {
        "MIX_MOVE": [83.0, 105.0],
        "PHASE": [120.0],
    },
    "track": {
        "54830": [687.889, 705.877],
    },
}


def test_resolves_with_exact_timestamp():
    assert _citation_resolves("[ev:MIX_MOVE@01:23]", SNAPSHOT)


def test_resolves_within_tolerance():
    # 83.0 in snapshot, citation @01:24.5 (84.5s) — within 2.0s.
    assert _citation_resolves("[ev:MIX_MOVE@01:24.5]", SNAPSHOT)


def test_does_not_resolve_outside_tolerance():
    # @02:00 = 120s, snapshot has MIX_MOVE at 83 + 105 — both > 2s away.
    assert not _citation_resolves("[ev:MIX_MOVE@02:00]", SNAPSHOT, tol=2.0)


def test_resolves_without_timestamp_when_key_present():
    assert _citation_resolves("[track:54830]", SNAPSHOT)


def test_does_not_resolve_unknown_source():
    assert not _citation_resolves("[bogus:thing@1]", SNAPSHOT)


def test_does_not_resolve_unknown_key():
    assert not _citation_resolves("[ev:NOPE@01:23]", SNAPSHOT)


def test_does_not_resolve_malformed_tag():
    assert not _citation_resolves("not a citation", SNAPSHOT)


# ---------------------------------------------------------------------------
# Integration — generate_drills with mocked Gemini client
# ---------------------------------------------------------------------------


def _drills_response(drills_list: list[Drill]):
    parsed = Drills(drills=drills_list)
    return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())


def _ok_drill(citation: str = "[ev:MIX_MOVE@01:23]") -> Drill:
    return Drill(
        situation="S",
        behavior=f"B {citation}",
        impact=f"I {citation}",
        action_recommended=f"A {citation}",
        citation=citation,
    )


def test_generate_drills_happy_path():
    client = MagicMock()
    client.models.generate_content.return_value = _drills_response(
        [_ok_drill() for _ in range(3)]
    )
    drills = generate_drills(client, "cited critique", ["c1", "c2"], SNAPSHOT)
    assert len(drills.drills) == 3


def test_generate_drills_retries_on_unresolvable_citation():
    """First attempt has bad citation; second attempt all good."""
    bad_drill = _ok_drill(citation="[ev:NOPE@99:99]")
    good_drill = _ok_drill(citation="[ev:MIX_MOVE@01:23]")
    client = MagicMock()
    client.models.generate_content.side_effect = [
        _drills_response([bad_drill, good_drill, good_drill]),
        _drills_response([good_drill, good_drill, good_drill]),
    ]
    drills = generate_drills(client, "cited", ["c"], SNAPSHOT, max_retries=2)
    assert len(drills.drills) == 3
    assert client.models.generate_content.call_count == 2


def test_generate_drills_raises_after_retries_exhausted():
    bad_drill = _ok_drill(citation="[ev:NOPE@99:99]")
    client = MagicMock()
    client.models.generate_content.return_value = _drills_response(
        [bad_drill, bad_drill, bad_drill]
    )
    with pytest.raises(DrillsGenerationError) as ei:
        generate_drills(client, "cited", ["c"], SNAPSHOT, max_retries=2)
    assert ei.value.reason == "drills_generation_failed"
    # max_retries=2 → 1 initial + 2 retries = 3 total attempts.
    assert client.models.generate_content.call_count == 3
