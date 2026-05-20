# SPDX-License-Identifier: Apache-2.0
"""BRINGUP-05 — stability soak harness tests.

Three layers (mirrors ``tests/recording/test_60min_soak.py``):

  * **unit** (default run) — the underrun classifier + ``SoakCounters`` against
    a REAL ``PlaybackQueue``: empty/partial pulls count as underruns, full
    pulls do not.
  * **slow** (``pytest -m slow``) — a SHORT synthetic soak driving a real
    ``PlaybackQueue`` at a scaled tick count, asserting bounded RSS growth +
    zero underruns in steady state.
  * **deselect guard** (default run) — a subprocess ``pytest -m "not slow"``
    that proves the slow soak is filtered out of the default run.

The real ≥30-min DJ-set soak is Kaan-action: ``python -m vibemix.runtime.soak
--seconds 1800 --attach``. Engineering ships the harness + the short automated
run only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.audio.levels import Levels
from vibemix.audio.buffers import PlaybackQueue
from vibemix.runtime.soak import (
    SoakCounters,
    SoakResult,
    assert_healthy,
    is_underrun,
    run_soak,
    sample_rss,
)


# ---------------------------------------------------------------------------
# Unit — underrun classifier + SoakCounters against the REAL PlaybackQueue.
# ---------------------------------------------------------------------------


def test_is_underrun_classifies_full_partial_empty():
    """is_underrun: a full pull (chunk == requested, audio was pending) is
    NOT an underrun; an all-zero pull while audio was expected IS; a
    shorter-than-requested (partial) pull IS."""
    requested = 100
    full = b"\x01" * 100
    empty = b"\x00" * 100
    partial = b"\x01" * 40 + b"\x00" * 60  # held 40 bytes, padded the rest

    # Full chunk, audio was pending → healthy.
    assert is_underrun(full, requested, had_pending=True) is False
    # All-zero pad while audio was expected → underrun.
    assert is_underrun(empty, requested, had_pending=True) is True
    # Held fewer bytes than requested → underrun (the queue couldn't satisfy).
    assert is_underrun(partial, requested, had_pending=True, held=40) is True
    # No audio was expected (silence) → an all-zero pull is NOT an underrun.
    assert is_underrun(empty, requested, had_pending=False) is False


def test_underrun_counter_against_real_playback_queue():
    """A REAL PlaybackQueue (not a mock): a full pull after a matching push
    is not an underrun; a pull on the now-empty queue IS counted."""
    levels = Levels()
    pq = PlaybackQueue(levels)
    counters = SoakCounters()

    n = 480 * 2  # 480 frames int16 = 960 bytes (a 20ms-ish chunk @24kHz)
    payload = (b"\x10\x00") * 480  # non-zero PCM, exactly n bytes

    # Push then pull the full payload → no underrun.
    pq.push(payload)
    chunk = pq.pull(n)
    assert len(chunk) == n
    counters.observe_pull(chunk, n, had_pending=True, held=n)
    assert counters.underruns == 0
    assert counters.pulls == 1

    # Pull again on the empty queue while audio was still expected → underrun.
    chunk2 = pq.pull(n)
    assert chunk2 == b"\x00" * n  # PlaybackQueue zero-pads an empty pull
    counters.observe_pull(chunk2, n, had_pending=True, held=0)
    assert counters.underruns == 1
    assert counters.pulls == 2

    # A pull during genuine silence (no audio expected) is NOT an underrun.
    chunk3 = pq.pull(n)
    counters.observe_pull(chunk3, n, had_pending=False, held=0)
    assert counters.underruns == 1  # unchanged
    assert counters.pulls == 3


def test_soak_counters_partial_pull_counts_as_underrun():
    """A partial-fill pull (queue held fewer bytes than requested, padded the
    rest) is counted as an underrun against the real queue."""
    levels = Levels()
    pq = PlaybackQueue(levels)
    counters = SoakCounters()

    n = 960
    pq.push(b"\x10\x00" * 200)  # 400 bytes < 960 requested
    chunk = pq.pull(n)
    assert len(chunk) == n  # zero-padded up to n
    counters.observe_pull(chunk, n, had_pending=True, held=400)
    assert counters.underruns == 1


# ---------------------------------------------------------------------------
# RSS sampler — smoke (default run).
# ---------------------------------------------------------------------------


def test_sample_rss_returns_positive_int_for_self():
    rss = sample_rss()  # self
    assert isinstance(rss, int)
    assert rss > 0


def test_assert_healthy_raises_on_growth_and_underruns():
    base = 100 * 1024 * 1024
    # Growth over budget → raises.
    bad_growth = SoakResult(
        baseline_rss=base,
        final_rss=base + 50 * 1024 * 1024,
        max_rss=base + 50 * 1024 * 1024,
        samples=[base, base + 50 * 1024 * 1024],
        underruns=0,
        pulls=10,
        duration_s=1.0,
    )
    with pytest.raises(AssertionError):
        assert_healthy(bad_growth, max_growth_bytes=5 * 1024 * 1024)

    # Underruns over max → raises.
    bad_underruns = SoakResult(
        baseline_rss=base,
        final_rss=base,
        max_rss=base,
        samples=[base, base],
        underruns=3,
        pulls=10,
        duration_s=1.0,
    )
    with pytest.raises(AssertionError):
        assert_healthy(bad_underruns, max_growth_bytes=5 * 1024 * 1024)

    # Healthy → no raise.
    healthy = SoakResult(
        baseline_rss=base,
        final_rss=base + 1024 * 1024,
        max_rss=base + 1024 * 1024,
        samples=[base, base + 1024 * 1024],
        underruns=0,
        pulls=10,
        duration_s=1.0,
    )
    assert_healthy(healthy, max_growth_bytes=5 * 1024 * 1024)  # must not raise


# ---------------------------------------------------------------------------
# slow — short synthetic soak (deselected from the default run).
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_short_synthetic_soak_bounded_rss_zero_underruns():
    """A short synthetic soak drives a real PlaybackQueue in steady state
    (push then pull every tick), asserting bounded RSS growth + zero
    underruns. Scaled to a tiny wall-clock window so the slow lane is fast."""
    levels = Levels()
    pq = PlaybackQueue(levels)

    result = run_soak(duration_s=1.0, tick_hz=200, queue=pq)

    assert isinstance(result, SoakResult)
    assert result.pulls > 0
    assert result.duration_s >= 1.0
    # Steady-state push-then-pull never underruns; a few MB growth budget.
    assert_healthy(result, max_growth_bytes=20 * 1024 * 1024, max_underruns=0)
    assert result.underruns == 0


# ---------------------------------------------------------------------------
# Deselect guard — proves the slow soak is filtered from the default run.
# ---------------------------------------------------------------------------


def test_slow_marker_deselects_soak_from_default_pytest_run() -> None:
    """`pytest -m "not slow" --collect-only` against THIS file deselects the
    slow synthetic soak. Belt-and-braces guarantee the default run never
    executes the soak loop (copied from test_60min_soak.py's guard shape)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "not slow",
            "-q",
            str(Path(__file__)),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = (result.stdout + result.stderr).lower()
    assert "deselect" in out or "no tests" in out or "no tests ran" in out, (
        "pytest -m 'not slow' should deselect the soak test; "
        f"got rc={result.returncode}.\nFULL OUTPUT:\n{out[:2000]}"
    )
    # The fast unit + guard tests must remain collectable in the default run.
    assert "test_underrun_counter_against_real_playback_queue" in out


# ---------------------------------------------------------------------------
# CLI smoke — `python -m vibemix.runtime.soak --seconds N` runs + exits 0.
# ---------------------------------------------------------------------------


@pytest.mark.cli
def test_soak_cli_runs_short_and_exits_zero() -> None:
    """`python -m vibemix.runtime.soak --seconds 1` runs a short self soak
    and prints a result summary, exiting 0 on a healthy run."""
    repo_root = Path(__file__).resolve().parents[2]
    env_src = str(repo_root / "src")
    result = subprocess.run(
        [sys.executable, "-m", "vibemix.runtime.soak", "--seconds", "1"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(repo_root),
        env={"PYTHONPATH": env_src, "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert result.returncode == 0, (
        f"soak CLI exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "rss" in combined or "underrun" in combined or "soak" in combined
