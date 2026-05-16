#!/usr/bin/env python3
"""Day-Zero proxy load test for vibemix.

Fires N concurrent HTTPS requests/second at a target URL for M seconds
and reports min/median/p95/p99 latency, error rate, and a pass/fail verdict
against p99<budget + error_rate<budget gates.

Default target: local-mock (autonomous safety — never DDOS prod).
Switch to live with --target https://api.altidus.world/vibemix/healthz.
Default profile: 100 RPS × 300s × 20 concurrent in-flight.

Run modes:
  --dry-run        Synthesize latency samples (no HTTP). Used by tests + offline rehearsal.
  --dry-run-seed N Seed the synthetic generator for deterministic test runs.
  --json           Machine-readable summary on stdout (human log still on stderr).

Exit code: 0 on PASS (p99 < budget AND error_rate < budget), 1 on FAIL.

Usage from Kaan during launch:
  python3 scripts/dayzero/proxy_load_test.py \\
      --target https://api.altidus.world/vibemix/healthz \\
      --rps 100 --duration 300

Stdlib + httpx only. No locust, no test-framework dep.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import random
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional


# Sentinel target value — never resolves to a real network call.
LOCAL_MOCK_TARGET: str = "local-mock"
LOCAL_MOCK_ENDPOINT: str = "http://127.0.0.1:0/mock"

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


# ---------------------------------------------------------------------------
# Sample collection
# ---------------------------------------------------------------------------

@dataclass
class Sample:
    """One request observation."""
    t_start_ms: float
    t_end_ms: float
    status: int
    latency_ms: float
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status < 300 and self.error is None


# ---------------------------------------------------------------------------
# Synthetic (dry-run) generator
# ---------------------------------------------------------------------------

def synthesize_samples(rps: int, duration_s: float, seed: Optional[int]) -> list[Sample]:
    """Generate deterministic-when-seeded latency samples.

    Distribution:
      - Center: gauss(mu=200ms, sigma=50ms)
      - Outliers: 0.5% chance of uniform(600ms, 1200ms)
      - Errors:   1% chance of status=599 (synthetic-failure)
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    total_n = int(rps * duration_s)
    samples: list[Sample] = []
    base_ms = 0.0
    interval_ms = 1000.0 / rps if rps > 0 else 1.0
    for i in range(total_n):
        if rng.random() < 0.005:
            latency_ms = rng.uniform(600.0, 1200.0)
        else:
            latency_ms = max(1.0, rng.gauss(200.0, 50.0))
        if rng.random() < 0.01:
            status = 599
            error = "synthetic-failure"
        else:
            status = 200
            error = None
        t_start = base_ms + i * interval_ms
        samples.append(Sample(
            t_start_ms=t_start,
            t_end_ms=t_start + latency_ms,
            status=status,
            latency_ms=latency_ms,
            error=error,
        ))
    return samples


# ---------------------------------------------------------------------------
# Live HTTP generator
# ---------------------------------------------------------------------------

async def _fire_one(client, target: str, t0_mono: float) -> Sample:
    t_start = (time.monotonic() - t0_mono) * 1000.0
    try:
        resp = await client.get(target, timeout=10.0)
        t_end = (time.monotonic() - t0_mono) * 1000.0
        return Sample(
            t_start_ms=t_start,
            t_end_ms=t_end,
            status=resp.status_code,
            latency_ms=t_end - t_start,
        )
    except Exception as exc:  # network/timeout/etc — count as error
        t_end = (time.monotonic() - t0_mono) * 1000.0
        return Sample(
            t_start_ms=t_start,
            t_end_ms=t_end,
            status=0,
            latency_ms=t_end - t_start,
            error=str(exc.__class__.__name__),
        )


async def live_load(target: str, rps: int, duration_s: float, concurrency: int) -> list[Sample]:
    """Fire requests at target RPS for duration seconds; cap in-flight at concurrency."""
    if not _HAS_HTTPX:
        raise RuntimeError(
            "httpx is required for live load testing. Install it or use --dry-run."
        )
    samples: list[Sample] = []
    sem = asyncio.Semaphore(concurrency)
    t0 = time.monotonic()
    interval = 1.0 / rps if rps > 0 else 0.01

    async with httpx.AsyncClient(http2=True) as client:
        tasks: list[asyncio.Task] = []

        async def _bounded():
            async with sem:
                s = await _fire_one(client, target, t0)
                samples.append(s)

        request_idx = 0
        deadline = t0 + duration_s
        while time.monotonic() < deadline:
            tasks.append(asyncio.create_task(_bounded()))
            request_idx += 1
            # Sleep-throttle to hit target RPS.
            await asyncio.sleep(interval)

        # Wait for in-flight to drain.
        await asyncio.gather(*tasks, return_exceptions=True)

    return samples


# ---------------------------------------------------------------------------
# Stats + verdict
# ---------------------------------------------------------------------------

def _percentile_ms(latencies_sorted: list[float], pct: float) -> float:
    """Linear-interpolated percentile for a sorted list."""
    if not latencies_sorted:
        return 0.0
    if len(latencies_sorted) == 1:
        return latencies_sorted[0]
    k = (len(latencies_sorted) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(latencies_sorted) - 1)
    if f == c:
        return latencies_sorted[f]
    return latencies_sorted[f] + (latencies_sorted[c] - latencies_sorted[f]) * (k - f)


@dataclass
class Verdict:
    verdict: str  # "PASS" | "FAIL"
    p99_ms: float
    p95_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    error_rate: float
    total_samples: int
    success_count: int
    error_count: int
    p99_budget_ms: float
    error_rate_budget: float
    duration_s: float
    rps: int
    target: str


def compute_verdict(
    samples: list[Sample],
    p99_budget_ms: float,
    error_rate_budget: float,
    duration_s: float,
    rps: int,
    target: str,
) -> Verdict:
    if not samples:
        return Verdict(
            verdict="FAIL",
            p99_ms=0.0, p95_ms=0.0, median_ms=0.0, min_ms=0.0, max_ms=0.0,
            error_rate=1.0,
            total_samples=0, success_count=0, error_count=0,
            p99_budget_ms=p99_budget_ms, error_rate_budget=error_rate_budget,
            duration_s=duration_s, rps=rps, target=target,
        )
    successes = [s for s in samples if s.is_success]
    errors = [s for s in samples if not s.is_success]
    latencies_sorted = sorted(s.latency_ms for s in samples)
    p99 = _percentile_ms(latencies_sorted, 99.0)
    p95 = _percentile_ms(latencies_sorted, 95.0)
    median = statistics.median(latencies_sorted)
    error_rate = len(errors) / len(samples)
    verdict = (
        "PASS"
        if p99 < p99_budget_ms and error_rate < error_rate_budget
        else "FAIL"
    )
    return Verdict(
        verdict=verdict,
        p99_ms=p99,
        p95_ms=p95,
        median_ms=median,
        min_ms=latencies_sorted[0],
        max_ms=latencies_sorted[-1],
        error_rate=error_rate,
        total_samples=len(samples),
        success_count=len(successes),
        error_count=len(errors),
        p99_budget_ms=p99_budget_ms,
        error_rate_budget=error_rate_budget,
        duration_s=duration_s,
        rps=rps,
        target=target,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="proxy_load_test.py",
        description=(
            "Day-Zero proxy load test. Fires HTTPS requests at a target URL and "
            "gates against p99 latency + error-rate budgets."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--target",
        default=LOCAL_MOCK_TARGET,
        help=(
            "Target URL or 'local-mock' (default: local-mock — never hits the "
            "network). Use --target https://api.altidus.world/vibemix/healthz "
            "for live runs."
        ),
    )
    p.add_argument("--rps", type=int, default=100, help="Requests per second (default: 100)")
    p.add_argument(
        "--duration",
        type=float,
        default=300.0,
        help="Test duration in seconds (default: 300)",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Max in-flight requests (default: 20)",
    )
    p.add_argument(
        "--p99-budget-ms",
        type=float,
        default=500.0,
        help="p99 latency budget in ms (default: 500)",
    )
    p.add_argument(
        "--error-rate-budget",
        type=float,
        default=0.01,
        help="Error rate budget as fraction (default: 0.01)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Synthesize samples instead of hitting the network",
    )
    p.add_argument(
        "--dry-run-seed",
        type=int,
        default=None,
        help="Seed for the synthetic generator (default: nondeterministic)",
    )
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit machine-readable JSON summary on stdout",
    )
    p.add_argument(
        "--artifact-dir",
        default=None,
        help=(
            "Directory to write the verdict JSON artifact "
            "(default: .planning/eval-runs/ if present)"
        ),
    )
    p.add_argument(
        "--no-artifact",
        action="store_true",
        help="Skip writing the verdict JSON artifact",
    )
    return p


def _resolve_artifact_dir(arg_dir: Optional[str]) -> Optional[pathlib.Path]:
    """Locate the artifact directory. Returns None if unavailable."""
    if arg_dir:
        return pathlib.Path(arg_dir)
    cwd = pathlib.Path.cwd()
    candidate = cwd / ".planning" / "eval-runs"
    if candidate.is_dir():
        return candidate
    return None


def write_artifact(verdict: "Verdict", artifact_dir: pathlib.Path) -> pathlib.Path:
    """Write the verdict JSON artifact to `artifact_dir`. Returns the path."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    out = artifact_dir / f"loadtest_{ts}.json"
    out.write_text(json.dumps(asdict(verdict), indent=2))
    return out


def _format_human_report(v: Verdict) -> str:
    lines = [
        "",
        f"=== Day-Zero proxy load test — {v.verdict} ===",
        f"target            : {v.target}",
        f"rps               : {v.rps}",
        f"duration          : {v.duration_s:.1f}s",
        f"total samples     : {v.total_samples}",
        f"successes         : {v.success_count}",
        f"errors            : {v.error_count}",
        f"error rate        : {v.error_rate * 100:.3f}%  (budget: {v.error_rate_budget * 100:.2f}%)",
        f"latency min       : {v.min_ms:.1f}ms",
        f"latency median    : {v.median_ms:.1f}ms",
        f"latency p95       : {v.p95_ms:.1f}ms",
        f"latency p99       : {v.p99_ms:.1f}ms  (budget: {v.p99_budget_ms:.1f}ms)",
        f"latency max       : {v.max_ms:.1f}ms",
        "",
    ]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)

    # `local-mock` target always runs synthetic samples (autonomous safety).
    is_local_mock = args.target == LOCAL_MOCK_TARGET
    if is_local_mock and not args.dry_run:
        print(
            "[local-mock] synthesizing samples — never hits the network",
            file=sys.stderr,
        )

    if args.dry_run or is_local_mock:
        print(
            f"[dry-run] synthesizing {int(args.rps * args.duration)} samples "
            f"(seed={args.dry_run_seed})",
            file=sys.stderr,
        )
        samples = synthesize_samples(args.rps, args.duration, args.dry_run_seed)
    else:
        if not _HAS_HTTPX:
            print(
                "ERROR: httpx is required for live load testing. "
                "Install it (pip install httpx) or use --dry-run.",
                file=sys.stderr,
            )
            return 2
        print(
            f"[live] firing {args.rps} RPS at {args.target} "
            f"for {args.duration}s, concurrency={args.concurrency}",
            file=sys.stderr,
        )
        samples = asyncio.run(
            live_load(args.target, args.rps, args.duration, args.concurrency)
        )

    verdict = compute_verdict(
        samples=samples,
        p99_budget_ms=args.p99_budget_ms,
        error_rate_budget=args.error_rate_budget,
        duration_s=args.duration,
        rps=args.rps,
        target=args.target,
    )

    # Human-readable goes to stderr (in JSON mode) or stdout (in human mode).
    if args.json_output:
        print(_format_human_report(verdict), file=sys.stderr)
        print(json.dumps(asdict(verdict)))
    else:
        print(_format_human_report(verdict))

    # Persist the verdict artifact unless explicitly suppressed.
    if not args.no_artifact:
        artifact_dir = _resolve_artifact_dir(args.artifact_dir)
        if artifact_dir is None:
            print(
                "[artifact] skipped — .planning/eval-runs/ not found "
                "(pass --artifact-dir to override)",
                file=sys.stderr,
            )
        else:
            out = write_artifact(verdict, artifact_dir)
            print(f"[artifact] wrote {out}", file=sys.stderr)

    return 0 if verdict.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
