# SPDX-License-Identifier: Apache-2.0
"""EvidenceRegistry mutation-driven cache refresh — Plan 41-02.

Pins:
  - Pitfall 2 — callback-storm during heavy mixing. The cancel-and-reschedule
    pattern collapses N mutations within a debounce window into a single
    cache.refresh() call.
  - The wall-clock refresh_loop is GONE — refresh fires only when evidence
    actually mutates. These tests verify the debounce + min-interval guards
    behave correctly.

Test execution uses short debounce + min-interval values (0.05s / 0.30s) so
the suite stays sub-second. The production wiring uses the
``DEFAULT_MUTATION_DEBOUNCE_S`` = 5.0 + ``DEFAULT_MIN_REFRESH_INTERVAL_S`` =
30.0 constants — those are pinned in ``test_default_constants`` below.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from vibemix.state.evidence_registry import (
    DEFAULT_MIN_REFRESH_INTERVAL_S,
    DEFAULT_MUTATION_DEBOUNCE_S,
    EvidenceRegistry,
)


# ---------- defaults pinned ----------


def test_default_constants() -> None:
    """Production wiring uses these two values — pin them here so a future
    refactor can't quietly change them. Pitfall 2 explicitly calls for 5s
    debounce + 30s min-interval."""
    assert DEFAULT_MUTATION_DEBOUNCE_S == 5.0
    assert DEFAULT_MIN_REFRESH_INTERVAL_S == 30.0


# ---------- no callback wired → noop ----------


def test_mutation_with_no_callback_is_noop() -> None:
    """Default constructor (no on_mutation) — write() still works and does
    NOT raise even though no scheduler runs."""

    async def _drive() -> None:
        reg = EvidenceRegistry()
        reg.write("ev", "K@1.0", 1.0)
        # No exception, no scheduled handle.
        assert reg._pending_refresh_handle is None  # type: ignore[attr-defined]
        # And the registry still recorded the observation.
        snap = reg.snapshot()
        assert snap["ev"]["K@1.0"] == (1.0,)

    asyncio.run(_drive())


def test_mutation_without_running_loop_is_noop() -> None:
    """Writing from synchronous code (no running loop) must not raise even
    when on_mutation is wired — the scheduler swallows the RuntimeError."""
    calls: list[float] = []

    async def _cb() -> None:
        calls.append(0.0)

    # No asyncio.run wrapper — bare sync call.
    reg = EvidenceRegistry(on_mutation=_cb)
    reg.write("ev", "K@1.0", 1.0)
    # Did not raise; nothing scheduled (no loop to schedule on); callback
    # never fired.
    assert reg._pending_refresh_handle is None  # type: ignore[attr-defined]
    assert calls == []


# ---------- debounce ----------


def test_single_mutation_schedules_refresh_after_debounce() -> None:
    """One write() → callback fires exactly once after the debounce window
    elapses (no spurious fire before the timer expires)."""
    call_count = 0

    async def _cb() -> None:
        nonlocal call_count
        call_count += 1

    async def _drive() -> None:
        nonlocal call_count
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.30,
        )
        reg.write("ev", "K@1.0", 1.0)
        # Before debounce elapses: zero calls.
        await asyncio.sleep(0.02)
        assert call_count == 0
        # After debounce elapses: exactly one call.
        await asyncio.sleep(0.10)
        assert call_count == 1

    asyncio.run(_drive())


def test_burst_of_mutations_only_fires_once_post_burst() -> None:
    """30 sequential write() calls within the debounce window → callback
    fires EXACTLY ONCE after the burst settles. Closes T-41-02-01."""
    call_count = 0

    async def _cb() -> None:
        nonlocal call_count
        call_count += 1

    async def _drive() -> None:
        nonlocal call_count
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.10,
            min_refresh_interval_s=0.50,
        )
        # 30 rapid mutations.
        for i in range(30):
            reg.write("ev", f"K@{i}", float(i))
            await asyncio.sleep(0.001)  # tiny yield so the loop can run timers
        # Still inside the debounce window from the LAST write — no fire yet.
        assert call_count == 0
        # Wait for the debounce to elapse.
        await asyncio.sleep(0.20)
        assert call_count == 1

    asyncio.run(_drive())


def test_callback_exception_does_not_kill_registry() -> None:
    """If on_mutation raises, the next mutation still schedules + fires a
    fresh refresh — exception isolation, no scheduler corruption."""
    call_count = 0

    async def _cb() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated callback failure")

    async def _drive() -> None:
        nonlocal call_count
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.10,
        )
        reg.write("ev", "K@1.0", 1.0)
        await asyncio.sleep(0.10)
        assert call_count == 1  # fired + raised internally
        # Second mutation must still schedule + fire (min-interval has
        # elapsed since last fire).
        await asyncio.sleep(0.15)
        reg.write("ev", "K@2.0", 2.0)
        await asyncio.sleep(0.10)
        assert call_count == 2

    asyncio.run(_drive())


# ---------- min-interval guard ----------


def test_min_refresh_interval_guard_delays_when_under_window() -> None:
    """If the callback fired RECENTLY, a new mutation reschedules to honor
    the min-interval guard (waits longer than the debounce). Pitfall 2 —
    sustained mutation churn must not re-create the explicit cache more
    than once per min_refresh_interval_s."""
    call_times: list[float] = []

    async def _cb() -> None:
        # Use loop time so we can measure the gap between fires.
        loop = asyncio.get_running_loop()
        call_times.append(loop.time())

    async def _drive() -> None:
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.40,
        )
        reg.write("ev", "K@1.0", 1.0)
        await asyncio.sleep(0.10)  # first fire happens here (~0.05s in)
        assert len(call_times) == 1

        # Second mutation while well inside the min-interval window.
        # Debounce alone would say "fire at +0.05s"; min-interval says
        # "fire at +0.40s from previous fire". Min-interval must win.
        t_second_write = asyncio.get_running_loop().time()
        reg.write("ev", "K@2.0", 2.0)
        # Wait long enough for the debounce-only schedule to fire.
        await asyncio.sleep(0.10)
        # If min-interval was honored, the second fire is STILL pending.
        assert len(call_times) == 1, (
            "min-interval guard violated — second fire happened too early"
        )
        # Eventually the second fire lands (min_interval - elapsed since
        # first fire ≈ 0.40 - 0.10 = 0.30s).
        await asyncio.sleep(0.40)
        assert len(call_times) == 2
        # Gap between first and second fire ≥ min_refresh_interval_s
        # (within a small scheduler-jitter margin).
        gap = call_times[1] - call_times[0]
        assert gap >= 0.35, f"min-interval guard too loose; gap={gap}s"
        # And the second fire happened after t_second_write + (min_interval
        # - already-elapsed) which is meaningfully later than the debounce.
        assert call_times[1] - t_second_write >= 0.25

    asyncio.run(_drive())


# ---------- __main__.py wiring smoke ----------


def test_main_no_create_task_for_refresh_loop() -> None:
    """Grep-style assertion against __main__.py source: no asyncio.create_task
    spawn of cache.refresh_loop must remain. Plan 41-02 deletes the wall-
    clock task entirely."""
    main_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "vibemix"
        / "__main__.py"
    )
    src = main_path.read_text(encoding="utf-8")
    assert "cache.refresh_loop(" not in src, (
        "stale cache.refresh_loop(...) spawn still present in __main__.py"
    )
    # Positive assertion — the new wiring must be there.
    assert "on_mutation=lambda: cache.refresh()" in src, (
        "EvidenceRegistry(on_mutation=lambda: cache.refresh()) wiring "
        "missing from __main__.py — Plan 41-02 mutation-driven refresh "
        "must be wired"
    )


def test_main_wires_evidence_registry_to_cache_refresh() -> None:
    """Smoke-light integration: construct cache + registry as __main__.py
    does, push a mutation, and confirm the registry calls cache.refresh.
    Uses a fake cache so we don't round-trip the Gemini API."""
    refresh_calls = 0

    class _FakeCache:
        async def refresh(self) -> None:
            nonlocal refresh_calls
            refresh_calls += 1

    fake_cache = _FakeCache()

    async def _drive() -> None:
        nonlocal refresh_calls
        # Match the __main__.py wiring pattern exactly.
        reg = EvidenceRegistry(
            on_mutation=lambda: fake_cache.refresh(),
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.10,
        )
        reg.write("ev", "K@1.0", 1.0)
        await asyncio.sleep(0.15)
        assert refresh_calls == 1

    asyncio.run(_drive())


# ---------- clear() interactions ----------


def test_register_library_schedules_refresh() -> None:
    """Bulk mutation via register_library() also triggers a debounced
    refresh — the cache body depends on what tracks are in the registry."""
    call_count = 0

    async def _cb() -> None:
        nonlocal call_count
        call_count += 1

    async def _drive() -> None:
        nonlocal call_count
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.10,
        )

        class _FakeLib:
            tracks = {"t1": object(), "t2": object()}

        count = reg.register_library(_FakeLib(), t_session=0.0)
        assert count == 2
        await asyncio.sleep(0.15)
        assert call_count == 1

    asyncio.run(_drive())


def test_register_library_empty_does_not_schedule() -> None:
    """Empty / wrong-shape library → no refresh scheduled (nothing changed)."""
    call_count = 0

    async def _cb() -> None:
        nonlocal call_count
        call_count += 1

    async def _drive() -> None:
        nonlocal call_count
        reg = EvidenceRegistry(
            on_mutation=_cb,
            mutation_debounce_s=0.05,
            min_refresh_interval_s=0.10,
        )

        class _EmptyLib:
            tracks: dict[str, object] = {}

        assert reg.register_library(_EmptyLib(), t_session=0.0) == 0
        await asyncio.sleep(0.15)
        assert call_count == 0

    asyncio.run(_drive())
