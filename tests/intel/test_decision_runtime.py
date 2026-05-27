# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

from vibemix.intel.agent_contract import AgentDecision
from vibemix.intel.context_compiler import compile_transition_context
from vibemix.intel.decision_runtime import (
    DecisionRuntimePolicy,
    RuntimeInputSnapshot,
    decide,
)
from vibemix.intel.transition_scorer import (
    LivePosition,
    SectionRecord,
    TransitionScoringInput,
    score_transition_slate,
)


class _Model:
    def __init__(self, decision: AgentDecision | BaseException) -> None:
        self.decision = decision
        self.called = False

    def decide(self, envelope):  # type: ignore[no-untyped-def]
        self.called = True
        if isinstance(self.decision, BaseException):
            raise self.decision
        return self.decision


def _section(section_id: str, track_id: str, role: str, cue_slot: str = "A") -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id=track_id,
        role=role,
        confidence=0.9,
        start_s=0.0,
        end_s=64.0,
        start_beat=0,
        bar_count=32,
        bpm=128.0,
        camelot="8A",
        energy_mean=50.0,
        cue_slot=cue_slot,
        cue_source="dj",
        cue_confidence=0.95,
    )


def _snapshot(
    *,
    mode: str = "live",
    current_track: bool = True,
    exact_timing: bool = True,
    blend: bool = False,
    include_candidates: bool = True,
) -> RuntimeInputSnapshot:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    live_position = (
        LivePosition(remaining_bars=16, playhead_confidence=0.95)
        if exact_timing
        else LivePosition(remaining_bars=16, playhead_confidence=0.55)
    )
    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,) if include_candidates else (),
            mode=mode,  # type: ignore[arg-type]
            live_position=live_position if mode == "live" else None,
        )
    )
    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode=mode,  # type: ignore[arg-type]
        intent="live_next_pill" if mode == "live" else "transition_slate",
        current={
            "track_id": "t1" if current_track else None,
            "blend_suppressed": blend,
        },
        candidates=slate,
    )
    return RuntimeInputSnapshot("snap_001", envelope)


def test_live_pill_uses_deterministic_path_by_default() -> None:
    model = _Model(
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            spoken_text="Model copy",
            confidence=0.9,
        )
    )

    result = decide("live", "live_next_pill", _snapshot(), model_backend=model)

    assert model.called is False
    assert result.decision_source == "deterministic"
    assert result.emitted
    assert result.final_decision.candidate_id == "tr_001"
    assert result.final_decision.timing_text == "in 16 bars"
    assert result.trace.decision_source == "deterministic"


def test_live_pill_suppresses_when_no_current_track() -> None:
    result = decide("live", "live_next_pill", _snapshot(current_track=False))

    assert result.final_decision.action == "suppress"
    assert not result.emitted
    assert "no_current_track" in result.trace.suppressed_reasons


def test_live_pill_blocks_exact_timing_in_blend() -> None:
    result = decide("live", "live_next_pill", _snapshot(blend=True))

    assert result.final_decision.action == "suppress"
    assert result.final_decision.timing_text is None
    assert "blend_active" in result.trace.suppressed_reasons


def test_live_pill_drops_timing_when_playhead_is_weak() -> None:
    result = decide("live", "live_next_pill", _snapshot(exact_timing=False))

    assert result.final_decision.action == "select"
    assert result.final_decision.timing_text is None
    assert "cue A" in result.final_decision.spoken_text
    assert "bars" not in result.final_decision.spoken_text


def test_live_pill_degrades_bad_model_text_to_deterministic_copy() -> None:
    model = _Model(
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            timing_text="in 16 bars",
            spoken_text="Use cue A in 16 bars.",
            confidence=0.9,
        )
    )

    result = decide(
        "live",
        "live_next_pill",
        _snapshot(),
        model_backend=model,
        policy=DecisionRuntimePolicy(deterministic_live_default=False, allow_model_in_live=True),
    )

    assert model.called is True
    assert result.decision_source == "model_degraded_to_deterministic"
    assert result.final_decision.spoken_text.startswith("Next good entry")
    assert result.final_decision.cited_claim_ids
    assert result.emitted


def test_live_pill_suppresses_unknown_candidate_action() -> None:
    model = _Model(
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_999",
            cue_slot="A",
            spoken_text="Take this one.",
            confidence=0.9,
        )
    )

    result = decide(
        "live",
        "live_next_pill",
        _snapshot(),
        model_backend=model,
        policy=DecisionRuntimePolicy(deterministic_live_default=False, allow_model_in_live=True),
    )

    assert result.decision_source == "model_rejected_suppress"
    assert result.final_decision.action == "suppress"
    assert not result.emitted


def test_prep_allows_ask_but_live_pill_rejects_ask() -> None:
    prep_model = _Model(
        AgentDecision(
            schema_version="intel_context_v1",
            action="ask",
            spoken_text="Do you want the safer path?",
            confidence=0.8,
        )
    )
    prep_result = decide(
        "prep", "transition_slate", _snapshot(mode="prep"), model_backend=prep_model
    )
    assert prep_result.decision_source == "model_validated"
    assert prep_result.final_decision.action == "ask"

    live_model = _Model(
        AgentDecision(
            schema_version="intel_context_v1",
            action="ask",
            spoken_text="Do you want the safer path?",
            confidence=0.8,
        )
    )
    live_result = decide(
        "live",
        "live_next_pill",
        _snapshot(),
        model_backend=live_model,
        policy=DecisionRuntimePolicy(deterministic_live_default=False, allow_model_in_live=True),
    )
    assert live_result.decision_source == "model_rejected_suppress"
    assert live_result.final_decision.action == "suppress"


def test_model_unavailable_uses_deterministic_fallback() -> None:
    result = decide(
        "prep",
        "transition_slate",
        _snapshot(mode="prep"),
        model_backend=_Model(RuntimeError("offline")),
    )

    assert result.decision_source == "model_degraded_to_deterministic"
    assert result.final_decision.action == "select"
    assert result.trace.model_call_id is None
    assert any("model_unavailable" in gate.reason for gate in result.trace.gate_results)


def test_no_candidates_holds_in_prep() -> None:
    result = decide("prep", "transition_slate", _snapshot(mode="prep", include_candidates=False))

    assert result.final_decision.action == "hold"
    assert not result.emitted
    assert "no_candidates" in result.trace.suppressed_reasons


def test_mode_argument_must_match_snapshot_envelope() -> None:
    snapshot = _snapshot(mode="prep")
    with pytest.raises(ValueError, match="mode/intent"):
        decide("live", "live_next_pill", snapshot)
