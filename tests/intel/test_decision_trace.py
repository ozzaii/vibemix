# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.intel.decision_trace import (
    AgentDecisionTrace,
    GateResult,
    stable_payload_hash,
)


def test_trace_redacts_paths_vectors_and_audio_refs() -> None:
    trace = AgentDecisionTrace(
        trace_id="trace_001",
        mode="live",
        intent="live_next_pill",
        decision_source="deterministic",
        input_snapshot_id="/Users/ozai/private/snapshot.json",
        context_packet_id="ctx_001",
        candidate_ids=("tr_001",),
        selected_candidate_id="tr_001",
        selected_proposal_id=None,
        gate_results=(GateResult("candidate_slate", "pass", "candidates_available"),),
        model_call_id=None,
        validation_status="accepted",
        validation_errors=(),
        final_action="select",
        final_payload_hash=stable_payload_hash({"path": "/tmp/private.wav", "candidate": "tr_001"}),
        suppressed_reasons=("vector:raw_001", "audio:raw_live"),
        latency_ms={"total": 12},
    )

    text = str(trace.to_redacted_dict())

    assert "/Users/ozai" not in text
    assert "/tmp/private.wav" not in text
    assert "vector:raw_001" not in text
    assert "audio:raw_live" not in text
    assert "tr_001" in text


def test_payload_hash_is_stable_after_redaction() -> None:
    first = stable_payload_hash(
        {
            "candidate_id": "tr_001",
            "path": "/Users/ozai/private.wav",
            "nested": {"vector": [1.0, 0.0], "safe": "cue A"},
        }
    )
    second = stable_payload_hash(
        {
            "candidate_id": "tr_001",
            "path": "/different/private.wav",
            "nested": {"vector": [0.0, 1.0], "safe": "cue A"},
        }
    )

    assert first == second
    assert first.startswith("sha256:")
