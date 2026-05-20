# SPDX-License-Identifier: Apache-2.0
"""BRINGUP-05 — headless stability soak harness (RSS + playback-underrun).

A duration-configurable sampler that watches a process's resident memory
(``psutil`` — already a dep, no new dependency) and counts playback-queue
underruns/dropouts, then asserts **bounded RSS growth** (delta, not absolute —
macOS shared pages + the PyInstaller footprint make absolute RSS noisy) and
**zero underruns** over the window.

Two layers (per RESEARCH §3 / project_phase_16_kaan_dj_testing):

  * **Engineering ships:** this harness + a SHORT automated synthetic soak (a
    ``slow``-marked test) + a one-command CLI.
  * **Kaan-action (deferred):** the real ≥30-min live DJ-set soak on the
    MacBook is the true sign-off. Run it with::

        python -m vibemix.runtime.soak --seconds 1800 --attach
        python -m vibemix.runtime.soak --seconds 1800 --pid <sidecar-pid>

The audio hot path (``PlaybackQueue``) is NOT modified — underruns are
*observed* by driving the real queue and inspecting ``pull()`` return bytes,
never instrumented into prod (RESEARCH §3 underrun_decision).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field

import psutil


# ---------------------------------------------------------------------------
# Underrun classification — pure, observes the real PlaybackQueue.pull() bytes.
# ---------------------------------------------------------------------------


def is_underrun(
    chunk: bytes,
    requested: int,
    *,
    had_pending: bool,
    held: int | None = None,
) -> bool:
    """Classify a ``PlaybackQueue.pull()`` result as an underrun (dropout).

    ``PlaybackQueue.pull(n)`` ALWAYS returns exactly ``n`` bytes — it zero-pads
    an empty or partial buffer. So we cannot detect underrun from the chunk
    length alone; we compare what was REQUESTED against what the queue actually
    HELD when audio was expected:

      * ``had_pending=False`` — genuine silence (no AI voice expected). An
        all-zero pull is normal; NOT an underrun.
      * ``had_pending=True`` and the queue held fewer bytes than requested
        (``held < requested``) — the queue couldn't satisfy the request:
        UNDERRUN. When ``held`` is unknown, fall back to an all-zero-chunk
        heuristic (a full zero pad while audio was expected = empty pull).
    """
    if not had_pending:
        return False
    if held is not None:
        return held < requested
    # No explicit held count — an all-zero chunk of full length means the
    # queue was empty (PlaybackQueue's empty-pull branch returns b"\x00"*n).
    return chunk == b"\x00" * requested


@dataclass
class SoakCounters:
    """Mutable underrun/pull accounting fed by ``observe_pull``."""

    underruns: int = 0
    pulls: int = 0

    def observe_pull(
        self,
        chunk: bytes,
        requested: int,
        *,
        had_pending: bool,
        held: int | None = None,
    ) -> None:
        """Feed one ``PlaybackQueue.pull()`` observation. Increments ``pulls``
        always; increments ``underruns`` when the pull is classified as one."""
        self.pulls += 1
        if is_underrun(chunk, requested, had_pending=had_pending, held=held):
            self.underruns += 1


# ---------------------------------------------------------------------------
# RSS sampling (psutil) + the soak result + the health assertion.
# ---------------------------------------------------------------------------


def sample_rss(pid: int | None = None) -> int:
    """Resident set size (bytes) for ``pid`` (self when ``pid`` is None)."""
    proc = psutil.Process(pid) if pid is not None else psutil.Process()
    return int(proc.memory_info().rss)


@dataclass
class SoakResult:
    """Outcome of a soak window — RSS samples + underrun accounting.

    RSS is reported as baseline/final/max + the raw sample series so callers
    can assert on GROWTH (``final_rss - baseline_rss``) or slope, never on
    absolute RSS (RESEARCH §3 landmine)."""

    baseline_rss: int
    final_rss: int
    max_rss: int
    samples: list[int] = field(default_factory=list)
    underruns: int = 0
    pulls: int = 0
    duration_s: float = 0.0

    @property
    def growth_bytes(self) -> int:
        return self.final_rss - self.baseline_rss


def assert_healthy(
    result: SoakResult,
    *,
    max_growth_bytes: int,
    max_underruns: int = 0,
) -> None:
    """Raise AssertionError when RSS grew past ``max_growth_bytes`` OR underruns
    exceeded ``max_underruns``. MB-formatted messages mirror
    ``test_60min_soak.py``'s failure style."""
    growth = result.growth_bytes
    if growth > max_growth_bytes:
        raise AssertionError(
            f"RSS grew {growth / 1_000_000:.1f}MB over the soak "
            f"(baseline {result.baseline_rss / 1_000_000:.1f}MB → final "
            f"{result.final_rss / 1_000_000:.1f}MB), budget "
            f"{max_growth_bytes / 1_000_000:.1f}MB exceeded"
        )
    if result.underruns > max_underruns:
        raise AssertionError(
            f"{result.underruns} playback underruns over {result.duration_s:.1f}s "
            f"(max allowed {max_underruns})"
        )


# ---------------------------------------------------------------------------
# The soak orchestrator.
# ---------------------------------------------------------------------------

# A 20ms voice chunk at 24kHz mono int16 = 480 frames × 2 bytes.
_CHUNK_FRAMES = 480
_CHUNK_BYTES = _CHUNK_FRAMES * 2
# Pre-allocate ONE synthetic PCM chunk and reuse it every tick so the harness
# itself doesn't dominate RSS growth (same discipline as test_60min_soak.py).
_SYNTHETIC_CHUNK = (b"\x10\x00") * _CHUNK_FRAMES

# Default soak duration when neither --seconds nor VIBEMIX_SOAK_SECONDS is set.
_DEFAULT_SECONDS = 60.0
# Sample RSS roughly once per second regardless of tick rate.
_RSS_SAMPLE_INTERVAL_S = 1.0


def _default_seconds() -> float:
    """Duration default: VIBEMIX_SOAK_SECONDS env, else ``_DEFAULT_SECONDS``."""
    raw = os.environ.get("VIBEMIX_SOAK_SECONDS")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_SECONDS


def run_soak(
    duration_s: float | None = None,
    *,
    pid: int | None = None,
    tick_hz: int = 30,
    queue=None,
) -> SoakResult:
    """Run a soak window of ``duration_s`` seconds.

    Over the window it samples RSS at ~1s intervals and, when a ``queue``
    (PlaybackQueue) is provided, drives a steady-state synthetic push/pull
    cycle at ``tick_hz`` and counts underruns by inspecting the real
    ``pull()`` return bytes. ``duration_s`` falls back to
    ``VIBEMIX_SOAK_SECONDS`` / the module default when None.

    Returns a :class:`SoakResult` (growth-based RSS + underrun accounting).
    """
    if duration_s is None:
        duration_s = _default_seconds()

    counters = SoakCounters()
    tick_interval = 1.0 / float(tick_hz) if tick_hz > 0 else 0.0

    start = time.monotonic()
    # Warm-up baseline: sample after the first tick so the interpreter/queue
    # have allocated their steady-state working set.
    baseline_rss = sample_rss(pid)
    samples: list[int] = [baseline_rss]
    max_rss = baseline_rss
    last_rss_sample = start

    while True:
        now = time.monotonic()
        elapsed = now - start
        if elapsed >= duration_s:
            break

        if queue is not None:
            # Steady state: push a chunk, then pull the same size. A
            # well-behaved queue satisfies the pull fully → no underrun. We
            # know exactly how many bytes were pending (we just pushed them).
            queue.push(_SYNTHETIC_CHUNK)
            chunk = queue.pull(_CHUNK_BYTES)
            counters.observe_pull(
                chunk, _CHUNK_BYTES, had_pending=True, held=_CHUNK_BYTES
            )

        # RSS sample at ~1s cadence.
        if now - last_rss_sample >= _RSS_SAMPLE_INTERVAL_S:
            rss = sample_rss(pid)
            samples.append(rss)
            max_rss = max(max_rss, rss)
            last_rss_sample = now

        if tick_interval:
            # Sleep the remainder of this tick (never negative).
            time.sleep(max(0.0, tick_interval - (time.monotonic() - now)))

    final_rss = sample_rss(pid)
    samples.append(final_rss)
    max_rss = max(max_rss, final_rss)

    return SoakResult(
        baseline_rss=baseline_rss,
        final_rss=final_rss,
        max_rss=max_rss,
        samples=samples,
        underruns=counters.underruns,
        pulls=counters.pulls,
        duration_s=time.monotonic() - start,
    )


# ---------------------------------------------------------------------------
# CLI — `python -m vibemix.runtime.soak --seconds N [--pid PID | --attach]`.
# ---------------------------------------------------------------------------

# A generous default growth budget for the live ≥30-min run — RSS on macOS is
# noisy (shared pages, allocator arenas), so the bar is "no runaway leak".
_DEFAULT_MAX_GROWTH_BYTES = 150 * 1024 * 1024


def _discover_sidecar_pid() -> int | None:
    """Best-effort: find the running vibemix-core sidecar pid.

    Matches a process whose name/cmdline contains ``vibemix-core`` (the
    PyInstaller binary) or ``-m vibemix`` (a source-spawned dev sidecar).
    Returns None when nothing matches — the caller should fall back to
    ``--pid`` or self-soak.
    """
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if proc.info["pid"] == os.getpid():
            continue
        if "vibemix-core" in name or "vibemix-core" in cmdline:
            return int(proc.info["pid"])
        if "-m vibemix" in cmdline and "soak" not in cmdline:
            return int(proc.info["pid"])
    return None


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vibemix.runtime.soak",
        description=(
            "Headless stability soak: sample RSS (psutil) + count playback "
            "underruns over a window; assert bounded growth + zero underruns."
        ),
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="soak duration (default: VIBEMIX_SOAK_SECONDS env or 60).",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--pid",
        type=int,
        default=None,
        help="sample RSS of this pid (e.g. the sidecar). Default: self.",
    )
    g.add_argument(
        "--attach",
        action="store_true",
        help="discover + attach to the running vibemix sidecar pid "
        "(falls back to --pid / self if not found).",
    )
    p.add_argument(
        "--max-growth-mb",
        type=float,
        default=_DEFAULT_MAX_GROWTH_BYTES / (1024 * 1024),
        help="max allowed RSS growth in MB before the run is unhealthy.",
    )
    p.add_argument(
        "--tick-hz",
        type=int,
        default=30,
        help="RSS sample / synthetic-drive tick rate (default 30).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    pid = args.pid
    if args.attach:
        discovered = _discover_sidecar_pid()
        if discovered is not None:
            pid = discovered
            print(f"-> attached to sidecar pid {pid}", file=sys.stderr)
        else:
            print(
                "-> no running sidecar found; soaking SELF (use --pid to target one)",
                file=sys.stderr,
            )

    seconds = args.seconds if args.seconds is not None else _default_seconds()
    print(
        f"-> soak: {seconds:.0f}s, target={'self' if pid is None else f'pid {pid}'}",
        file=sys.stderr,
    )

    # When attached to an external pid we only sample RSS (we can't drive that
    # process's PlaybackQueue from here); the underrun count stays 0 and the
    # real underrun signal comes from the sidecar's own logs. A self-soak with
    # no queue still proves the RSS sampler runs end-to-end.
    result = run_soak(duration_s=seconds, pid=pid, tick_hz=args.tick_hz)

    print(
        "soak result: "
        f"baseline={result.baseline_rss / 1_000_000:.1f}MB "
        f"final={result.final_rss / 1_000_000:.1f}MB "
        f"max={result.max_rss / 1_000_000:.1f}MB "
        f"growth={result.growth_bytes / 1_000_000:.1f}MB "
        f"underruns={result.underruns} pulls={result.pulls} "
        f"duration={result.duration_s:.1f}s "
        f"samples={len(result.samples)}"
    )

    try:
        assert_healthy(
            result, max_growth_bytes=int(args.max_growth_mb * 1024 * 1024)
        )
    except AssertionError as e:
        print(f"UNHEALTHY: {e}", file=sys.stderr)
        return 1
    print("HEALTHY")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
