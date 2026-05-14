# SPDX-License-Identifier: Apache-2.0
"""TTFTMeter primitive tests — Plan 19-05 Task 1.

Rolling-average meter that records (event_fired_at, first_chunk_at) pairs
and exposes the average in milliseconds. Default sentinel (1500.0 ms) is
chosen so the FIRST event after warmup passes the AckBank TTFT gate
(>800 ms) — without this, the very first ack of a session could never
fire because there's no prior measurement.
"""

from __future__ import annotations

import pytest

from vibemix.runtime.ttft import TTFTMeter


def test_empty_meter_returns_default_ms() -> None:
    """Empty meter (no record_first_chunk yet) → rolling_avg_ms == default_ms."""
    meter = TTFTMeter()
    assert meter.rolling_avg_ms() == 1500.0
    assert meter.samples_count() == 0


def test_single_sample_records_correctly() -> None:
    """event_fired at t=100.0, first_chunk at t=100.5 → rolling_avg_ms == 500.0."""
    state = [100.0]

    def time_fn() -> float:
        return state[0]

    meter = TTFTMeter(time_fn=time_fn)
    meter.record_event_fired()
    state[0] = 100.5
    meter.record_first_chunk()
    assert meter.rolling_avg_ms() == 500.0
    assert meter.samples_count() == 1


def test_rolling_window_caps_at_window() -> None:
    """Push 12 samples; only the last 8 contribute to the average."""
    state = [0.0]

    def time_fn() -> float:
        return state[0]

    meter = TTFTMeter(window=8, time_fn=time_fn)

    # Samples 1..12: each is (i*100)ms TTFT.
    for i in range(1, 13):
        state[0] = float(i)  # event_fired at t=i
        meter.record_event_fired()
        state[0] = float(i) + (i / 10.0)  # first_chunk at t=i + i*0.1 → i*100ms
        meter.record_first_chunk()

    assert meter.samples_count() == 8
    # Last 8 samples: 500ms, 600ms, 700ms, ..., 1200ms → mean = (500+...+1200)/8 = 850
    expected = sum(range(500, 1300, 100)) / 8
    assert meter.rolling_avg_ms() == expected


def test_first_chunk_without_pending_is_noop() -> None:
    """record_first_chunk with no pending event_fired → no sample recorded."""
    meter = TTFTMeter()
    meter.record_first_chunk()
    assert meter.rolling_avg_ms() == 1500.0
    assert meter.samples_count() == 0


def test_record_event_fired_overwrites_pending() -> None:
    """Two consecutive record_event_fired → record_first_chunk measures from
    the SECOND event_fired. The first was preempted/lost."""
    state = [10.0]

    def time_fn() -> float:
        return state[0]

    meter = TTFTMeter(time_fn=time_fn)
    meter.record_event_fired()  # pending at t=10
    state[0] = 11.0
    meter.record_event_fired()  # pending now overwritten to t=11
    state[0] = 11.5
    meter.record_first_chunk()  # measures 11.5 - 11.0 = 500ms, NOT 1500ms

    assert meter.rolling_avg_ms() == 500.0
    assert meter.samples_count() == 1


def test_default_ms_passes_ack_gate() -> None:
    """Sentinel default_ms (1500.0) MUST be greater than ACK_TTFT_GATE_MS (800.0)
    so the first event of a session can fire an ack."""
    from vibemix.agent.ack_bank import ACK_TTFT_GATE_MS

    meter = TTFTMeter()
    assert meter.rolling_avg_ms() > ACK_TTFT_GATE_MS


def test_uses_injected_time_fn() -> None:
    """The injected time_fn drives all timing — tests are deterministic."""
    state = [50.0]

    def time_fn() -> float:
        return state[0]

    meter = TTFTMeter(time_fn=time_fn)
    meter.record_event_fired()
    state[0] = 50.123
    meter.record_first_chunk()
    assert meter.rolling_avg_ms() == pytest.approx(123.0)
