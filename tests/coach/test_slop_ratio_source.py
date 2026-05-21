# SPDX-License-Identifier: Apache-2.0
"""Plan 55-03 Task 1 — pins StrippedRateTracker.slop_ratio() as the REAL
cumulative stripped/total metric LIVE-04 wants.

slop_ratio() is the lifetime-of-session "what fraction of model turns got
stripped" signal — DISTINCT from the 15s rolling rate() (the bypass-guard).
Both are driven off the SAME record() decisions: total bumps on every
record(), stripped bumps on record(True). slop_ratio() = stripped/total,
0.0 cold-start (never NaN/None). The cumulative counters are NOT windowed and
NOT evicted, so slop_ratio() survives a window roll that drops rate().

This REPLACES the count-derived 1/(1+mean) placeholder in __main__.py's
_citation_telemetry() (closed in Task 4). The 15s rolling rate() +
one-shot should_bypass() are UNCHANGED — locked by
tests/coach/test_stripped_rate_tracker.py.

All time tests use a manual clock list (``t = [100.0]``;
``time_fn=lambda: t[0]``) — deterministic, mirroring the existing tracker test.
"""

from __future__ import annotations

import math

from vibemix.coach import StrippedRateTracker


# ---------------------------------------------------------------------------
# Cold-start — 0.0, never NaN/None
# ---------------------------------------------------------------------------


def test_slop_ratio_cold_start_is_zero() -> None:
    """A fresh tracker.slop_ratio() == 0.0 (no records yet)."""
    tracker = StrippedRateTracker()
    assert tracker.slop_ratio() == 0.0


def test_slop_ratio_cold_start_never_nan_or_none() -> None:
    """Cold-start returns a real float 0.0 — never NaN, never None.

    Pins the no-divide-by-zero contract: _cum_total == 0 must short-circuit
    to 0.0, not compute 0/0.
    """
    tracker = StrippedRateTracker()
    value = tracker.slop_ratio()
    assert value is not None
    assert isinstance(value, float)
    assert not math.isnan(value)
    assert value == 0.0


# ---------------------------------------------------------------------------
# Rises on a strip — cumulative stripped/total
# ---------------------------------------------------------------------------


def test_slop_ratio_one_strip_is_one() -> None:
    """After a single record(True): slop_ratio() == 1.0 (1 stripped / 1 total)."""
    tracker = StrippedRateTracker()
    tracker.record(True)
    assert tracker.slop_ratio() == 1.0


def test_slop_ratio_strip_then_clean_is_half() -> None:
    """record(True) then record(False): slop_ratio() == 0.5 (1 stripped / 2 total)."""
    tracker = StrippedRateTracker()
    tracker.record(True)
    tracker.record(False)
    assert tracker.slop_ratio() == 0.5


def test_slop_ratio_clean_only_is_zero() -> None:
    """A run of clean record(False) keeps slop_ratio() at 0.0 (0 stripped / N total)."""
    tracker = StrippedRateTracker()
    for _ in range(5):
        tracker.record(False)
    assert tracker.slop_ratio() == 0.0


# ---------------------------------------------------------------------------
# Cumulative — survives window eviction that drops the rolling rate()
# ---------------------------------------------------------------------------


def test_slop_ratio_is_cumulative_not_windowed() -> None:
    """slop_ratio() is lifetime; rate() is the 15s rolling window — distinct.

    Record True at t=0, then advance the injected clock PAST window_s, then
    record(False) at t=20 (window_s=15). The t=0 True entry is evicted from
    the rolling deque, so rate() reflects only the surviving False (0.0).
    But slop_ratio() is cumulative — it still counts BOTH records: 1/2.
    This proves the two signals diverge under window eviction.
    """
    t = [0.0]
    tracker = StrippedRateTracker(window_s=15.0, time_fn=lambda: t[0])

    tracker.record(True)  # t=0 — will be evicted from the rolling window
    t[0] = 20.0
    tracker.record(False)  # t=20 — only this survives the 15s window

    # Rolling window: t=0 evicted, only False@20 remains → rate 0.0.
    assert tracker.rate() == 0.0
    # Cumulative: both records counted → 1 stripped / 2 total = 0.5.
    assert tracker.slop_ratio() == 0.5


def test_slop_ratio_strip_raises_both_signals() -> None:
    """A strip raises BOTH slop_ratio() and rate() on the same record(True).

    Same-window (no time advance) so the rolling deque keeps every entry —
    the cumulative counters bump on the identical record() call that drives
    the rolling window.
    """
    t = [100.0]
    tracker = StrippedRateTracker(time_fn=lambda: t[0])
    tracker.record(False)  # clean baseline
    assert tracker.slop_ratio() == 0.0
    assert tracker.rate() == 0.0

    tracker.record(True)  # strip — both must rise
    assert tracker.slop_ratio() == 0.5  # 1 stripped / 2 total
    assert tracker.rate() == 0.5  # 1 stripped / 2 in-window
