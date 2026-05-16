# SPDX-License-Identifier: Apache-2.0
"""Pitfall 2 — synthetic stripped-heavy session must trip bypass before silence.

The Phase 20 design pin: a 10-invalid-response burst in 12 seconds MUST trip
the StrippedRateTracker bypass BEFORE the cohost crosses an 8-second silence
streak. Without the bypass, every invalid response strips → no AI text → 30+
seconds of dead-air. The bypass is the trust gate that prevents the linter
itself from being the failure mode.

This test isolates the timing math at the StrippedRateTracker layer (no
agent integration needed — the integration coverage lives in
tests/agent/test_dj_cohost_linter.py). Manual clock list keeps the
contract deterministic.
"""

from __future__ import annotations

from vibemix.coach import StrippedRateTracker


def test_pitfall2_stripped_burst_trips_bypass_before_8s_silence() -> None:
    """10 invalid responses in 12s → bypass fires < 8s elapsed.

    Cadence: 1 stripped response every 1.2s. Window=15s, threshold=0.4.
    After the 4th record at t=4.8s, the rate (4 stripped / 4 total = 1.0)
    is well above threshold and the FIRST should_bypass() call must
    return True. 4.8s < 8.0s — the silence-streak ceiling is honored.
    """
    t = [0.0]
    tracker = StrippedRateTracker(
        window_s=15.0,
        threshold=0.4,
        time_fn=lambda: t[0],
    )

    cadence_s = 1.2
    silence_ceiling_s = 8.0
    first_bypass_t: float | None = None

    for i in range(10):
        t[0] = i * cadence_s
        tracker.record(stripped=True)
        if first_bypass_t is None and tracker.should_bypass():
            first_bypass_t = t[0]
            break  # one-shot fired — that's the only thing we need to assert

    assert first_bypass_t is not None, (
        "StrippedRateTracker never fired bypass during 10-invalid burst — "
        "cohost would silence-streak indefinitely (Pitfall 2 unmitigated)"
    )
    assert first_bypass_t < silence_ceiling_s, (
        f"bypass fired at t={first_bypass_t}s, after the {silence_ceiling_s}s "
        f"silence-streak ceiling — Pitfall 2 mitigation insufficient"
    )


def test_pitfall2_bypass_fires_inside_first_few_strips() -> None:
    """Sanity — at threshold=0.4 with rate=1.0 the bypass fires by record 2.

    With 1 stripped record the rate is 1/1=1.0, well above 0.4.
    First should_bypass() at i==0 must return True. Locks the
    "instant-trip on hot start" property.
    """
    t = [0.0]
    tracker = StrippedRateTracker(window_s=15.0, threshold=0.4, time_fn=lambda: t[0])
    tracker.record(stripped=True)
    assert tracker.should_bypass() is True
