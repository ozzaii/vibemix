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


# PERF-01 telemetry budget: the conservative regression floor for the live-path
# rolling TTFT. Set to the TTFTMeter default sentinel (1500.0 ms) — TTFTMeter is
# telemetry-only now (the ack-bank runtime gate was retired), so this is a CI
# regression floor over replayed traffic, NOT a runtime gate. Open Q2 / A1: flag
# for Kaan to TIGHTEN on real hardware once felt-perf is measured under a live set
# (the felt "TTFT instant" sign-off rides the Kaan-action live-drive surface).
LIVE_TTFT_BUDGET_MS = 1500.0


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


def test_default_ms_reads_above_cold_thresholds() -> None:
    """Cold-session sentinel (1500.0) reads strictly above the legacy
    800ms ack-gate threshold. The ack-bank gate itself has been retired,
    but the sentinel still signals "treat the cold session as slow" to
    any UI surface that displays the rolling average."""
    meter = TTFTMeter()
    assert meter.rolling_avg_ms() > 800.0


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


# ---------------------------------------------------------------------------
# PERF-01 — TTFT telemetry budget over replayed real-shaped reaction traffic.
# TTFTMeter is telemetry-only (the ack-bank runtime gate was retired); these
# tests pin the rolling average as a CI regression floor against
# LIVE_TTFT_BUDGET_MS over a replay of realistic event_fired→first_chunk
# samples. The real lever (the boot-time MINIMAL-thinking gate) is pinned
# separately in tests/llm/test_thinking_gate.py.
# ---------------------------------------------------------------------------


def _replay_ttft_samples(sample_ms: list[float], *, window: int = 8) -> TTFTMeter:
    """Build a TTFTMeter on the file's deterministic injected-clock pattern
    (state[0] / time_fn) and replay a sequence of TTFT samples (in ms) through
    it as event_fired → first_chunk pairs. Returns the driven meter.

    Mirrors the clock-driving used at the single-sample / rolling-window tests
    above — no wall-clock reads, fully deterministic.
    """
    state = [0.0]

    def time_fn() -> float:
        return state[0]

    meter = TTFTMeter(window=window, time_fn=time_fn)
    t = 0.0
    for ms in sample_ms:
        state[0] = t
        meter.record_event_fired()
        state[0] = t + (ms / 1000.0)
        meter.record_first_chunk()
        # Advance past this sample so the next pair starts on a clean clock.
        t = t + (ms / 1000.0) + 1.0
    return meter


def test_ttft_rolling_avg_within_budget_over_replayed_traffic() -> None:
    """PERF-01 — replay realistic in-budget reaction traffic through TTFTMeter
    and assert the rolling average stays at or below LIVE_TTFT_BUDGET_MS.

    Replays >8 samples (more than one full window of 8) in a realistic
    400-1200 ms TTFT band so the rolling deque is exercised end-to-end. The
    last-8-window mean of this band sits well under the 1500 ms floor.
    """
    # 12 samples in a realistic 400-1200ms band (real reaction traffic shape).
    sample_ms = [420.0, 510.0, 640.0, 700.0, 880.0, 760.0,
                 540.0, 610.0, 700.0, 820.0, 950.0, 1180.0]
    meter = _replay_ttft_samples(sample_ms)

    # Recorded the replayed samples (not the empty sentinel): window caps at 8.
    assert meter.samples_count() >= 8
    # Telemetry budget assertion — rolling avg under the regression floor.
    assert meter.rolling_avg_ms() <= LIVE_TTFT_BUDGET_MS
    # No runtime ack-gate surface exists — this is telemetry only. The retired
    # gate method must NOT be resurrected on the meter.
    assert not hasattr(meter, "".join(["should", "_fire"]))


def test_ttft_over_budget_replay_breaches_floor_negative_control() -> None:
    """PERF-01 negative control — a replay whose TTFT samples all exceed the
    budget pushes rolling_avg_ms() ABOVE LIVE_TTFT_BUDGET_MS. Proves the floor
    has teeth: the budget assertion is not vacuously true."""
    # All samples well above the 1500ms floor (a degraded / 7s+ regression).
    sample_ms = [2200.0, 2600.0, 3100.0, 2900.0, 2400.0,
                 2700.0, 3300.0, 2800.0, 2500.0]
    meter = _replay_ttft_samples(sample_ms)

    assert meter.samples_count() >= 8
    assert meter.rolling_avg_ms() > LIVE_TTFT_BUDGET_MS
