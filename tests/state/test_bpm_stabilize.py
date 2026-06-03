# SPDX-License-Identifier: Apache-2.0
"""BPM median stabilizer — rejects subdivision-lock outliers without smearing.

Root cause (measured on a real psytrance track via the live ws_bus + an offline
estimate_bpm sweep, 2026-05-21): ``estimate_bpm`` is BIMODAL on dense material —
~130 BPM dominates (146/221 windows ≈ 66%) with a ~194-200 BPM subdivision-lock
cluster (≈28%, the autocorr grabbing the hi-hat layer instead of the kick).

The state loop took ONE raw sample per 3 s tick, so genre flickered to
``unknown``/``house`` whenever a 200 landed, which in turn destabilised the genre
profile and let phase classification fall back to the no-hysteresis path → the
phase flicker seen live.

A lower-median over a short ring rejects the >180 outliers and always returns a
real observed sample. A mean/EMA would average 130+200 into the ~165 cross-genre
GAP (``unknown``), which is strictly worse — hence median, not EMA.
"""
from vibemix.state.refresh import _stabilize_bpm


def test_drops_out_of_range_outliers_and_medians_rest():
    # the real bimodal pattern: mostly 130, transient subdivision locks at ~200
    assert _stabilize_bpm([130.0, 130.0, 200.0, 130.0, 194.0]) == 130.0


def test_all_outliers_returns_zero_unknown():
    # honest: no in-range sample yet -> 0.0 (genre stays 'unknown', not fabricated)
    assert _stabilize_bpm([200.0, 194.0]) == 0.0
    assert _stabilize_bpm([]) == 0.0


def test_pass_through_stable_in_range():
    assert _stabilize_bpm([128.0, 130.0, 132.0]) == 130.0


def test_never_manufactures_a_between_sample_gap_value():
    # even-length valid set must yield a REAL observed sample, never the mean
    # (130+176)/2 = 153 would land in the techno/hard_tek 'unknown' gap.
    out = _stabilize_bpm([130.0, 176.0])
    assert out in (130.0, 176.0)


def test_hard_tek_upper_band_survives():
    # 176 is in the valid range (<=180); it must NOT be dropped as an outlier
    assert _stabilize_bpm([176.0, 200.0, 176.0]) == 176.0


def test_previous_bpm_holds_on_in_range_alternate_lock():
    # Live 2026-06-03: the public counter hopped across several plausible
    # in-range locks (166.7 -> 171.4 -> 150 -> 125). A single far-away median
    # must not replace an already visible BPM without a small agreeing cluster.
    assert _stabilize_bpm([166.7, 171.4, 150.0], previous=171.4) == 171.4
    assert _stabilize_bpm([166.7, 171.4, 150.0, 125.0, 150.0], previous=171.4) == 171.4
    assert _stabilize_bpm([162.2, 125.0, 111.1, 111.1, 111.1], previous=162.2) == 162.2


def test_previous_bpm_switches_after_cluster_forms():
    assert _stabilize_bpm([150.0, 150.0, 125.0, 150.0, 150.0], previous=171.4) == 150.0


def test_previous_bpm_allows_small_drift():
    assert _stabilize_bpm([166.7, 169.0], previous=166.7) == 169.0


def test_rolling_ring_replay_never_leaks_out_of_range():
    # Replay the measured bimodal distribution through a rolling ring of 5.
    # Stabilized output must never exceed BPM_VALID_MAX and must settle at 130.
    import random
    from statistics import median

    rng = random.Random(0)
    samples = []
    for _ in range(300):
        r = rng.random()
        if r < 0.66:
            samples.append(130.0)
        elif r < 0.94:
            samples.append(rng.choice([194.0, 200.0]))
        else:
            samples.append(rng.choice([103.0, 130.0, 176.0]))

    ring: list[float] = []
    out: list[float] = []
    for s in samples:
        ring.append(s)
        if len(ring) > 5:
            del ring[0]
        st = _stabilize_bpm(ring)
        if st > 0:
            out.append(st)

    assert out, "expected at least one stabilized reading"
    assert max(out) <= 180.0, f"out-of-range BPM leaked: max={max(out)}"
    assert median(out) == 130.0
