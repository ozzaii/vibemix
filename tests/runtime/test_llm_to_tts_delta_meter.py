# SPDX-License-Identifier: Apache-2.0
"""Plan 41-04 Task 1 — LLMToTTSDeltaMeter primitive tests (LAT-04).

Mirrors the TTFTMeter pattern (tests/runtime/test_ttft.py):
  * Inject ``time_fn`` so tests are deterministic.
  * No-pending no-op contract.
  * Cross-turn state reset.
  * ``log_turn(recorder)`` writes a ``llm_to_tts_delta_ms`` event with
    the integer delta — never the head text (T-41-04-06 mitigation).
"""

from __future__ import annotations

from typing import Any

from vibemix.runtime.llm_to_tts_delta_meter import LLMToTTSDeltaMeter


class _FakeRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))


def test_record_first_sentence_after_event() -> None:
    """start_turn at t0; record_first_sentence at t0+0.4s → delta_ms() == 400."""
    state = [100.0]

    def time_fn() -> float:
        return state[0]

    meter = LLMToTTSDeltaMeter(time_fn=time_fn)
    meter.start_turn()
    state[0] = 100.4
    meter.record_first_sentence()
    assert meter.delta_ms() == 400


def test_multiple_turns_reset_state() -> None:
    """Two consecutive turns; second turn's delta independent of the first."""
    state = [0.0]

    def time_fn() -> float:
        return state[0]

    meter = LLMToTTSDeltaMeter(time_fn=time_fn)
    # Turn 1: delta = 500ms
    state[0] = 10.0
    meter.start_turn()
    state[0] = 10.5
    meter.record_first_sentence()
    assert meter.delta_ms() == 500

    # Turn 2: delta = 200ms — start_turn resets state.
    state[0] = 30.0
    meter.start_turn()
    state[0] = 30.2
    meter.record_first_sentence()
    assert meter.delta_ms() == 200


def test_no_first_sentence_yielded_returns_none() -> None:
    """Turn ends without record_first_sentence → delta_ms() is None."""
    state = [0.0]

    def time_fn() -> float:
        return state[0]

    meter = LLMToTTSDeltaMeter(time_fn=time_fn)
    meter.start_turn()
    state[0] = 1.0  # time advanced but no record_first_sentence call
    assert meter.delta_ms() is None


def test_no_start_turn_no_op() -> None:
    """record_first_sentence with no pending start_turn → no-op (delta None)."""
    meter = LLMToTTSDeltaMeter()
    meter.record_first_sentence()
    assert meter.delta_ms() is None


def test_log_turn_emits_to_recorder() -> None:
    """log_turn writes a llm_to_tts_delta_ms event with the int delta."""
    state = [50.0]

    def time_fn() -> float:
        return state[0]

    meter = LLMToTTSDeltaMeter(time_fn=time_fn)
    meter.start_turn()
    state[0] = 50.35
    meter.record_first_sentence()

    recorder = _FakeRecorder()
    meter.log_turn(recorder)

    assert len(recorder.events) == 1
    kind, fields = recorder.events[0]
    assert kind == "llm_to_tts_delta_ms"
    assert fields["delta_ms"] == 350
    assert isinstance(fields["delta_ms"], int)


def test_log_turn_no_delta_no_event() -> None:
    """Turn without first-sentence yield → log_turn writes NO event (skip)."""
    meter = LLMToTTSDeltaMeter()
    meter.start_turn()
    recorder = _FakeRecorder()
    meter.log_turn(recorder)
    assert recorder.events == []


def test_log_turn_payload_excludes_head_text() -> None:
    """T-41-04-06 mitigation — delta payload MUST NOT carry head content."""
    state = [10.0]

    def time_fn() -> float:
        return state[0]

    meter = LLMToTTSDeltaMeter(time_fn=time_fn)
    meter.start_turn()
    state[0] = 10.1
    meter.record_first_sentence()
    recorder = _FakeRecorder()
    meter.log_turn(recorder)

    fields = recorder.events[0][1]
    # No content/text keys allowed — only metric metadata.
    assert "text" not in fields
    assert "head" not in fields
    assert "content" not in fields
