# SPDX-License-Identifier: Apache-2.0
"""StrippedRateTracker — Plan 20-01 Task 1.

Pins the rolling-15s-window stripped-rate math + one-shot bypass semantics
that prevent the linter itself from inducing a silence-streak DoS (Pitfall 2,
threat T-20-01-02). The one-shot reset must be tested explicitly: without it,
every response in a sustained breach window emits [unverified] and the strip
mechanism becomes functionally disabled.

All time tests use a manual clock list (``t = [100.0]``;
``time_fn=lambda: t[0]``) — deterministic > sleep-based mock-the-wall-clock.
"""

from __future__ import annotations

from vibemix.coach import (
    STRIPPED_RATE_THRESHOLD,
    STRIPPED_RATE_WINDOW_S,
    StrippedRateTracker,
)


# ---------------------------------------------------------------------------
# (a) test_initial_rate_zero
# ---------------------------------------------------------------------------


def test_initial_rate_zero() -> None:
    """No records yet → rate()==0.0."""
    tracker = StrippedRateTracker()
    assert tracker.rate() == 0.0
    assert tracker.should_bypass() is False


# ---------------------------------------------------------------------------
# (b) test_rate_simple_math
# ---------------------------------------------------------------------------


def test_rate_simple_math() -> None:
    """record True, True, False → rate == 2/3."""
    t = [100.0]
    tracker = StrippedRateTracker(time_fn=lambda: t[0])
    tracker.record(True)
    tracker.record(True)
    tracker.record(False)
    assert tracker.rate() == 2 / 3


# ---------------------------------------------------------------------------
# (c) test_window_eviction
# ---------------------------------------------------------------------------


def test_window_eviction() -> None:
    """Entries older than window_s evicted on every record() call.

    Record True at t=0, True at t=10, True at t=20 with window_s=15:
    at t=20 only entries from t>=5 survive (the t=0 entry is evicted).
    """
    t = [0.0]
    tracker = StrippedRateTracker(window_s=15.0, time_fn=lambda: t[0])
    tracker.record(True)  # t=0
    t[0] = 10.0
    tracker.record(True)  # t=10
    t[0] = 20.0
    tracker.record(True)  # t=20

    # t=0 is now 20s old → evicted; only t=10 and t=20 survive.
    assert tracker.rate() == 1.0  # 2/2 stripped — same arithmetic but lock the eviction


def test_window_eviction_keeps_recent_falses() -> None:
    """Recent False entries are NOT evicted; the rate reflects them."""
    t = [0.0]
    tracker = StrippedRateTracker(window_s=15.0, time_fn=lambda: t[0])
    tracker.record(True)  # t=0 → will evict
    t[0] = 10.0
    tracker.record(False)  # t=10
    t[0] = 20.0
    tracker.record(True)  # t=20

    # t=0 evicted; surviving = (False@10, True@20) → rate = 1/2
    assert tracker.rate() == 0.5


# ---------------------------------------------------------------------------
# (d) test_should_bypass_below_threshold
# ---------------------------------------------------------------------------


def test_should_bypass_below_threshold() -> None:
    """Rate 0.3 vs threshold 0.4 → should_bypass() False."""
    t = [100.0]
    tracker = StrippedRateTracker(threshold=0.4, time_fn=lambda: t[0])
    # 3 stripped + 7 not → rate 0.3
    for _ in range(3):
        tracker.record(True)
    for _ in range(7):
        tracker.record(False)
    assert abs(tracker.rate() - 0.3) < 1e-9
    assert tracker.should_bypass() is False


# ---------------------------------------------------------------------------
# (e) test_should_bypass_above_threshold_fires_once
# ---------------------------------------------------------------------------


def test_should_bypass_above_threshold_fires_once() -> None:
    """Rate 0.5 → should_bypass() True on FIRST call, False on SECOND.

    One-shot semantics: in a sustained breach window the bypass must NOT
    fire repeatedly — otherwise every response in the breach becomes
    [unverified] and the strip mechanism is disabled (T-20-01-02 mitigation).
    """
    t = [100.0]
    tracker = StrippedRateTracker(threshold=0.4, time_fn=lambda: t[0])
    for _ in range(5):
        tracker.record(True)
    for _ in range(5):
        tracker.record(False)
    assert tracker.rate() == 0.5

    # First call — bypass fires.
    assert tracker.should_bypass() is True
    # Second call within the same breach — bypass MUST NOT fire again.
    assert tracker.should_bypass() is False
    # Third call still no.
    assert tracker.should_bypass() is False


# ---------------------------------------------------------------------------
# (f) test_bypass_rearms_after_recovery
# ---------------------------------------------------------------------------


def test_bypass_rearms_after_recovery() -> None:
    """Bypass re-arms after the rate falls back to <= threshold.

    Sequence: trip bypass (rate>thr) → record many False until rate<=thr →
    next high-rate trip fires bypass again.
    """
    t = [100.0]
    tracker = StrippedRateTracker(window_s=15.0, threshold=0.4, time_fn=lambda: t[0])

    # Phase 1 — trip the bypass.
    for _ in range(5):
        tracker.record(True)
    assert tracker.rate() == 1.0
    assert tracker.should_bypass() is True
    assert tracker.should_bypass() is False  # one-shot

    # Phase 2 — recover. Many False records drag the rate below threshold.
    # Stay inside the same window (no time advance) to keep the True entries
    # in the deque as we drown them with Falses.
    for _ in range(20):
        tracker.record(False)
    # 5 True + 20 False → rate = 5/25 = 0.2 < 0.4
    assert tracker.rate() == 0.2

    # The recovery itself does NOT fire bypass — it just re-arms.
    assert tracker.should_bypass() is False

    # Phase 3 — new breach. Pump in stripped responses again.
    for _ in range(15):
        tracker.record(True)
    # 20 True + 20 False → rate = 0.5
    assert tracker.rate() == 0.5
    # Bypass fires AGAIN — re-armed after recovery.
    assert tracker.should_bypass() is True
    assert tracker.should_bypass() is False  # one-shot again


# ---------------------------------------------------------------------------
# (g) test_injected_time_fn
# ---------------------------------------------------------------------------


def test_injected_time_fn_is_actually_used() -> None:
    """The injected time_fn drives every now-stamp inside the tracker.

    Construct a tracker with a constant clock function — eviction is
    inert (no time delta). Without injected time_fn, time.monotonic would
    advance and the test would be flaky.
    """
    calls: list[int] = []

    def _clock() -> float:
        calls.append(1)
        return 50.0

    tracker = StrippedRateTracker(time_fn=_clock)
    tracker.record(True)
    tracker.record(False)
    tracker.record(True)

    # The clock was queried at least once per record().
    assert len(calls) >= 3


# ---------------------------------------------------------------------------
# Constants lock — pin the public defaults
# ---------------------------------------------------------------------------


def test_default_constants_locked() -> None:
    """STRIPPED_RATE_THRESHOLD=0.4 + STRIPPED_RATE_WINDOW_S=15.0 are the contract."""
    assert STRIPPED_RATE_THRESHOLD == 0.4
    assert STRIPPED_RATE_WINDOW_S == 15.0
