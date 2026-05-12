# SPDX-License-Identifier: Apache-2.0
"""Plan 13-08 — sidecar→localhost-receive dispatch latency.

Pins the SIDECAR-SIDE half of the MASCOT-08 latency budget (AI event →
animation transition start < 100ms). The webview-side half is covered
by ``tauri/ui/src/mascot/state-machine-fixtures.test.ts`` (dispatch +
plan + applyTransition are pure functions; their p99 is well under 1ms
in vitest).

What this measures:
    1. A real ``websockets.serve`` on a free port (NOT 8765 — avoids
       collision with a running app or with other parallel test runs).
    2. A real ``websockets.connect`` client subscribes.
    3. The server emits 100 synthetic frames at 30Hz, each carrying its
       emit timestamp (``perf_counter_ns()``).
    4. The client records the receive timestamp the moment the frame
       lands.
    5. Asserts ``p95(t_recv - t_emit) < 50ms`` (server-to-client on
       localhost). The 50ms budget is the SIDECAR-SIDE share of the
       100ms total — the webview JS dispatch + state-machine apply adds
       at most another 10ms, leaving 40ms slack.

What this does NOT measure:
    - Browser webview latency (covered by vitest pure-function tests).
    - LiveKit ↔ Gemini round-trips (different latency budget, owned by
      Plan 4 / 5).
    - 30Hz sustained throughput over an hour (UAT-only — see
      13-08-MANUAL-SMOKE.md #1).

Marked ``@pytest.mark.integration`` so the fast unit-test run can skip
it. Run explicitly:

    python -m pytest tests/integration/test_mascot_dispatch_latency.py \
        -m integration -x -q
"""

from __future__ import annotations

import asyncio
import json
import socket
import time
from contextlib import closing

import pytest
import websockets


# ── Tuning ───────────────────────────────────────────────────────────────────

#: Number of synthetic frames the server emits. 100 frames @ 30Hz = ~3.3s of
#: wall-clock — enough samples to give the p95 statistical meaning without
#: making the test slow.
FRAME_COUNT: int = 100

#: Frame cadence (Hz). Mirrors ws_broadcast in src/vibemix/runtime/ws_bus.py.
EMIT_HZ: int = 30

#: p95 latency budget in milliseconds (sidecar-side half of MASCOT-08's 100ms
#: total). The webview JS dispatch + state-machine apply adds at most another
#: 10ms in measured tests; 40ms slack is healthy.
P95_BUDGET_MS: float = 50.0

#: Server bind host. Mirrors ws_bus's localhost-only invariant.
BIND_HOST: str = "127.0.0.1"


# ── Helpers ──────────────────────────────────────────────────────────────────


def find_free_port() -> int:
    """Bind a transient socket to port 0 to discover a free TCP port.

    Why not just hardcode 8765: this test may run while a real vibemix
    process owns 8765, or in parallel with other test runs. ``bind(0)``
    asks the kernel for an ephemeral port; closing the socket releases
    it before websockets.serve binds (race-tolerable on localhost — the
    kernel almost never reassigns within microseconds).
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((BIND_HOST, 0))
        return s.getsockname()[1]


def _percentile(samples: list[float], pct: float) -> float:
    """Compute the ``pct`` percentile of ``samples`` (0..100).

    Uses linear interpolation between the two nearest ranks. No
    numpy dep — keeps the test importable in CI environments that strip
    optional deps.
    """
    if not samples:
        raise ValueError("_percentile: empty sample list")
    if pct < 0 or pct > 100:
        raise ValueError(f"_percentile: pct out of range: {pct}")
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    # Linear-interpolation rank computation.
    rank = (pct / 100.0) * (n - 1)
    lo_idx = int(rank)
    hi_idx = min(lo_idx + 1, n - 1)
    frac = rank - lo_idx
    return sorted_samples[lo_idx] * (1 - frac) + sorted_samples[hi_idx] * frac


async def _run_latency_probe(port: int) -> list[float]:
    """Server emits FRAME_COUNT frames @EMIT_HZ; client records latencies.

    Returns a list of per-frame latencies in milliseconds. Each latency
    is ``t_recv - t_emit`` where both timestamps come from
    ``time.perf_counter_ns()`` — a monotonic, high-resolution clock not
    subject to NTP adjustment mid-test.

    The server task and the client task run concurrently on the same
    event loop. Both share the same ``time.perf_counter_ns()`` clock
    (process-wide), so the latencies are directly comparable.
    """

    received_latencies_ms: list[float] = []
    client_connected = asyncio.Event()

    async def server_handler(ws):
        """One-shot server: emit FRAME_COUNT frames at EMIT_HZ then exit."""
        client_connected.set()
        period_s = 1.0 / EMIT_HZ
        for i in range(FRAME_COUNT):
            t_emit_ns = time.perf_counter_ns()
            payload = json.dumps({"seq": i, "t_emit_ns": t_emit_ns})
            await ws.send(payload)
            # Schedule the next frame on EMIT_HZ cadence. asyncio.sleep
            # absorbs any small handler-internal jitter without
            # accumulating drift across frames.
            await asyncio.sleep(period_s)

    server = await websockets.serve(server_handler, BIND_HOST, port)

    try:
        async with websockets.connect(f"ws://{BIND_HOST}:{port}") as client:
            await asyncio.wait_for(client_connected.wait(), timeout=5.0)
            # Drain FRAME_COUNT frames; record latency for each.
            for _ in range(FRAME_COUNT):
                raw = await asyncio.wait_for(client.recv(), timeout=2.0)
                t_recv_ns = time.perf_counter_ns()
                if not isinstance(raw, str):
                    continue
                msg = json.loads(raw)
                t_emit_ns = msg.get("t_emit_ns")
                if not isinstance(t_emit_ns, int):
                    continue
                latency_ms = (t_recv_ns - t_emit_ns) / 1_000_000.0
                received_latencies_ms.append(latency_ms)
    finally:
        server.close()
        await server.wait_closed()

    return received_latencies_ms


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_mascot_dispatch_latency_p95_under_50ms():
    """p95 sidecar→localhost-receive latency must clear the 50ms budget.

    Closes MASCOT-08 (animation event-time latency) on the sidecar
    side. The webview-side dispatch is verified separately by the
    vitest fixture replay (pure-function plan + apply are <1ms per
    call; the in-webview rAF tick adds ≤16ms at 60fps).

    Total budget breakdown (from CONTEXT.md Area 6):
        - sidecar emit → localhost receive: < 50ms p95 (THIS TEST)
        - webview dispatch + plan + apply:  < 10ms p99 (vitest)
        - rAF schedule jitter (60fps):      ≤ 16.7ms worst-case
        - crossfade kickoff:                ≤ 16.7ms worst-case
        ────────────────────────────────────────────────────────
        Total event-to-visual-transition:   ≤ 93ms — under 100ms.
    """
    port = find_free_port()
    latencies_ms = asyncio.run(_run_latency_probe(port))

    # Sanity: we expect FRAME_COUNT samples. If many were dropped, the
    # measurement is unreliable.
    assert len(latencies_ms) >= int(FRAME_COUNT * 0.95), (
        f"too few samples collected: {len(latencies_ms)} / {FRAME_COUNT} "
        f"(>5% drop suggests the WS connection was unstable; "
        f"latency numbers are not meaningful)"
    )

    p50 = _percentile(latencies_ms, 50)
    p95 = _percentile(latencies_ms, 95)
    p99 = _percentile(latencies_ms, 99)
    p_max = max(latencies_ms)

    # Helpful diagnostic output on failure (and on -v passing).
    print(
        f"\n[dispatch-latency] samples={len(latencies_ms)} "
        f"p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms max={p_max:.2f}ms "
        f"budget=p95<{P95_BUDGET_MS:.0f}ms"
    )

    assert p95 < P95_BUDGET_MS, (
        f"sidecar dispatch latency p95={p95:.2f}ms exceeds {P95_BUDGET_MS:.0f}ms budget "
        f"(samples={len(latencies_ms)}, p50={p50:.2f}ms, p99={p99:.2f}ms, max={p_max:.2f}ms). "
        f"This blocks MASCOT-08 — investigate whether the EMIT_HZ loop is starving, "
        f"or whether localhost networking is contended (e.g., another vibemix process "
        f"is on the same port)."
    )


@pytest.mark.integration
def test_mascot_dispatch_latency_helpers_well_formed():
    """Smoke-test the helper math so a real-test regression doesn't get
    masked by a broken percentile / port helper.

    Cheap (no network), but lives under the integration marker so it
    runs in the same opt-in batch as the real latency probe.
    """
    # Percentile sanity.
    assert _percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == pytest.approx(5.5)
    assert _percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == pytest.approx(9.55)
    assert _percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0) == 1
    assert _percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 100) == 10

    # Port helper returns a valid TCP port (1..65535) and is free at call
    # time (re-bind succeeds immediately).
    port = find_free_port()
    assert 1024 < port < 65536
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        # Should not raise — the port was just released by find_free_port.
        s.bind((BIND_HOST, port))
