# SPDX-License-Identifier: Apache-2.0
"""Plan 20-05 — unit tests for ``vibemix.coach.citation_ipc_shim.CitationIpcShim``.

The shim satisfies the duck-typed ``await ipc_bus.emit(dict)`` contract in
``coach_loop`` so the Plan 20-04 publish gate fires in the v2.0 live binary.
v2.x replaces the in-process deque buffer with a real multiplexed WS emitter
that pipes the SessionCitation envelope to the mascot WS clients.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest


def test_shim_01_constructs_with_default_maxlen() -> None:
    """SHIM-01: ``CitationIpcShim()`` constructs without args; default
    maxlen is a sane bounded value (16 ≤ maxlen ≤ 1024)."""
    from vibemix.coach.citation_ipc_shim import CitationIpcShim

    shim = CitationIpcShim()
    assert shim is not None
    # The bound is implementation-side; we only check it's non-trivial and
    # not unbounded (deque(maxlen=None) is unbounded and would leak).
    assert 16 <= shim._buffer.maxlen <= 1024


def test_shim_02_emit_is_awaitable_async_method() -> None:
    """SHIM-02: ``emit`` is an async method — coach_loop ``await``s it."""
    from vibemix.coach.citation_ipc_shim import CitationIpcShim

    shim = CitationIpcShim()
    assert inspect.iscoroutinefunction(shim.emit), (
        "CitationIpcShim.emit must be an async method"
    )


def test_shim_03_emit_appends_to_buffer() -> None:
    """SHIM-03: ``await shim.emit({"a": 1})`` appends the dict to the
    internal buffer; ``snapshot()`` returns a tuple of buffered dicts in
    insertion order."""
    from vibemix.coach.citation_ipc_shim import CitationIpcShim

    shim = CitationIpcShim()

    async def driver() -> None:
        await shim.emit({"a": 1})
        await shim.emit({"a": 2})

    asyncio.run(driver())
    snap = shim.snapshot()
    assert snap == ({"a": 1}, {"a": 2})
    assert len(shim) == 2


def test_shim_04_bounded_deque_evicts_oldest_when_full() -> None:
    """SHIM-04: 100 emits → buffer length capped at the configured maxlen
    (default ≤ 1024). Oldest entries evicted FIFO."""
    from vibemix.coach.citation_ipc_shim import CitationIpcShim

    shim = CitationIpcShim(maxlen=8)

    async def driver() -> None:
        for i in range(100):
            await shim.emit({"i": i})

    asyncio.run(driver())
    assert len(shim) == 8
    snap = shim.snapshot()
    # FIFO eviction: the surviving entries are the last 8 (i=92..99).
    assert snap[0] == {"i": 92}
    assert snap[-1] == {"i": 99}


def test_shim_05_snapshot_is_frozen_tuple_not_buffer_reference() -> None:
    """SHIM-05: ``snapshot()`` returns a tuple, not a deque/list reference.
    Mutating the returned object must not affect the buffer."""
    from vibemix.coach.citation_ipc_shim import CitationIpcShim

    shim = CitationIpcShim()

    async def driver() -> None:
        await shim.emit({"x": 1})

    asyncio.run(driver())
    snap = shim.snapshot()
    assert isinstance(snap, tuple), "snapshot() must return a tuple"
    # Tuples are immutable; if a future change returns a list, this fails.
    with pytest.raises((AttributeError, TypeError)):
        snap.append({"y": 2})  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# __main__.py wiring assertions (source-grep continuation of test_main_anti_slop_wiring)
# ---------------------------------------------------------------------------


def _main_src() -> str:
    from pathlib import Path

    return Path("src/vibemix/__main__.py").read_text()


def test_wire16_main_imports_citation_ipc_shim() -> None:
    """W16: __main__.py imports CitationIpcShim from
    vibemix.coach.citation_ipc_shim."""
    src = _main_src()
    assert "CitationIpcShim" in src, "CitationIpcShim import missing"


def test_wire17_main_constructs_citation_ipc_shim_conditionally() -> None:
    """W17: __main__.py constructs ``CitationIpcShim()`` gated by
    ``anti_slop_enabled`` — when disabled, the shim is None so
    coach_loop's citation_wired flag evaluates False (publish-gate dormant
    on the legacy path)."""
    src = _main_src()
    import re

    pattern = re.compile(r"CitationIpcShim\(\)\s+if\s+anti_slop_enabled\s+else\s+None")
    assert pattern.search(src), (
        "CitationIpcShim must be conditionally constructed: "
        "`CitationIpcShim() if anti_slop_enabled else None`"
    )


def test_wire18_coach_loop_receives_ipc_bus_kwarg() -> None:
    """W18: ``coach_loop(...)`` call contains ``ipc_bus=`` kwarg."""
    src = _main_src()
    assert "ipc_bus=" in src, "coach_loop must receive ipc_bus= kwarg"


def test_wire19_coach_loop_receives_citation_telemetry_kwarg() -> None:
    """W19: ``coach_loop(...)`` call contains ``citation_telemetry=`` kwarg."""
    src = _main_src()
    assert "citation_telemetry=" in src, (
        "coach_loop must receive citation_telemetry= kwarg"
    )


def test_wire20_citation_telemetry_closure_returns_required_keys() -> None:
    """W20: The citation_telemetry callable returns a dict with the four
    keys SessionCitation.make() consumes:
    slop_ratio / stripped_rate_15s / last_unverified_response / bypass_active.
    Source-grep all four key strings inside the closure body."""
    src = _main_src()
    # Find the closure definition (heuristic — search around "_citation_telemetry"):
    idx = src.find("_citation_telemetry")
    assert idx != -1, "_citation_telemetry closure missing"
    # Inspect a forward window of ~1500 chars to cover the body.
    body = src[idx : idx + 1500]
    for key in (
        '"slop_ratio"',
        '"stripped_rate_15s"',
        '"last_unverified_response"',
        '"bypass_active"',
    ):
        assert key in body, f"closure body missing key {key}"


def test_wire21_telemetry_closure_uses_non_destructive_bypass_check() -> None:
    """W21: ``bypass_active`` MUST NOT call ``should_bypass()`` — that's the
    destructive one-shot latch. Source-grep the closure body for
    ``should_bypass`` and assert it's absent."""
    src = _main_src()
    idx = src.find("_citation_telemetry")
    assert idx != -1, "_citation_telemetry closure missing"
    body = src[idx : idx + 1500]
    assert "should_bypass" not in body, (
        "citation_telemetry closure must not call should_bypass() "
        "(destructive one-shot latch — would consume the bypass on every "
        "2s telemetry tick)"
    )


def test_wire22_telemetry_reads_stripped_rate_threshold_from_constants() -> None:
    """W22: The closure compares ``rate > STRIPPED_RATE_THRESHOLD`` (the
    constant from vibemix.coach.constants) — NOT a magic 0.4 literal. This
    keeps the threshold change locked to one source of truth."""
    src = _main_src()
    assert "STRIPPED_RATE_THRESHOLD" in src, (
        "STRIPPED_RATE_THRESHOLD constant must be imported "
        "(no magic 0.4 literal)"
    )
