# SPDX-License-Identifier: Apache-2.0
"""Phase 20-04 Task 2 — coach_loop periodic ipc.session.citation publish.

Mirrors the test_coach.py async harness pattern (fast-forward asyncio.sleep
via mocker, deterministic time.time, stop_event after N ticks). Asserts the
publish gate fires only when both ipc_bus + citation_telemetry are non-None,
debounces to 1 emit per CITATION_PUBLISH_INTERVAL_S, and survives telemetry
exceptions without spamming.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.coach import CITATION_PUBLISH_INTERVAL_S, coach_loop

_REAL_SLEEP = asyncio.sleep


def _make_stop_after(n_sleeps: int, stop_event: asyncio.Event):
    """Same harness as tests/runtime/test_coach.py — stop after N sleep calls."""
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)
        if len(sleep_calls) >= n_sleeps:
            stop_event.set()
        await _REAL_SLEEP(0)

    return fake_sleep, sleep_calls


def _auto_time(start: float = 1000.0, step: float = 0.1):
    """Auto-advancing time — each call returns prev + step."""
    state = {"t": start}

    def _now() -> float:
        cur = state["t"]
        state["t"] += step
        return cur

    return _now


# ---------------------------------------------------------------------------
# CITATION-01 — ipc_bus is None → no publish, legacy path preserved
# ---------------------------------------------------------------------------


def test_no_publish_when_ipc_bus_none(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """coach_loop with both kwargs default-None → legacy Plan 19-05 path
    runs unchanged; no exception."""
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(3, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
        )
    )

    # Legacy path — no detect calls expected (event_detector returns None
    # default), no exception, no in_flight residue.
    assert trigger_state.get("in_flight") is False


# ---------------------------------------------------------------------------
# CITATION-02 — ipc_bus set but telemetry None → still no publish
# ---------------------------------------------------------------------------


def test_no_publish_when_telemetry_none(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """When citation_telemetry is None, ipc_bus.emit is NEVER called even if
    ipc_bus is non-None — both must be wired before any publish fires."""
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(5, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    ipc_bus = MagicMock()
    ipc_bus.emit = AsyncMock(return_value=None)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ipc_bus=ipc_bus,
            citation_telemetry=None,
        )
    )

    ipc_bus.emit.assert_not_awaited()


# ---------------------------------------------------------------------------
# CITATION-03 — periodic publish at >= CITATION_PUBLISH_INTERVAL_S cadence
# ---------------------------------------------------------------------------


def test_periodic_publish_fires_at_2s_interval(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """With both kwargs wired and time advancing past
    CITATION_PUBLISH_INTERVAL_S, the gate fires; cadence ≤1 per interval."""
    # Advance time by 1.0s per tick (10 ticks → 10s of sim time).
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(11, stop_event)  # 1 warmup + 10 ticks
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch(
        "vibemix.runtime.coach.time.time",
        side_effect=_auto_time(start=1000.0, step=1.0),
    )

    ipc_bus = MagicMock()
    ipc_bus.emit = AsyncMock(return_value=None)
    telemetry = MagicMock(
        return_value={
            "slop_ratio": 0.1,
            "stripped_rate_15s": 0.05,
            "last_unverified_response": None,
            "bypass_active": False,
        }
    )

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ipc_bus=ipc_bus,
            citation_telemetry=telemetry,
        )
    )

    # Loop ran for ~10s of sim time at 1.0s/tick. Cadence ≤1 emit per
    # CITATION_PUBLISH_INTERVAL_S=2.0s → expect ≤6 emits, ≥1 emit.
    assert ipc_bus.emit.await_count >= 1
    expected_max = int(10 / CITATION_PUBLISH_INTERVAL_S) + 1
    assert ipc_bus.emit.await_count <= expected_max, (
        f"emits={ipc_bus.emit.await_count} exceeds debounce ceiling {expected_max}"
    )

    # Every emit was an ipc.session.citation message dict.
    for call in ipc_bus.emit.await_args_list:
        msg = call.args[0]
        assert msg["type"] == "ipc.session.citation"


# ---------------------------------------------------------------------------
# CITATION-04 — publish payload top-level + payload key shape
# ---------------------------------------------------------------------------


def test_publish_payload_shape(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """The dict passed to ipc_bus.emit must carry the locked envelope
    (type/ts/payload) + 4-field payload."""
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(6, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch(
        "vibemix.runtime.coach.time.time",
        side_effect=_auto_time(start=1000.0, step=1.0),
    )

    ipc_bus = MagicMock()
    ipc_bus.emit = AsyncMock(return_value=None)
    telemetry = MagicMock(
        return_value={
            "slop_ratio": 0.4,
            "stripped_rate_15s": 0.2,
            "last_unverified_response": "sample",
            "bypass_active": False,
        }
    )

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ipc_bus=ipc_bus,
            citation_telemetry=telemetry,
        )
    )

    assert ipc_bus.emit.await_count >= 1
    msg = ipc_bus.emit.await_args_list[0].args[0]
    assert set(msg.keys()) == {"type", "ts", "payload"}
    assert set(msg["payload"].keys()) == {
        "slop_ratio",
        "stripped_rate_15s",
        "last_unverified_response",
        "bypass_active",
    }


# ---------------------------------------------------------------------------
# CITATION-05 — telemetry exception is swallowed; loop continues
# ---------------------------------------------------------------------------


def test_publish_swallows_telemetry_exception(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """A raising telemetry callable must NOT crash coach_loop; the publish
    gate's try/except + debounce-on-error keeps the loop running cleanly."""
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(8, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch(
        "vibemix.runtime.coach.time.time",
        side_effect=_auto_time(start=1000.0, step=1.0),
    )

    ipc_bus = MagicMock()
    ipc_bus.emit = AsyncMock(return_value=None)
    telemetry = MagicMock(side_effect=RuntimeError("synthetic telemetry blow-up"))

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    # Must NOT raise.
    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ipc_bus=ipc_bus,
            citation_telemetry=telemetry,
        )
    )

    # ipc_bus.emit was never invoked because telemetry raised before construct.
    ipc_bus.emit.assert_not_awaited()
    # And the telemetry callable WAS invoked at least once.
    assert telemetry.call_count >= 1


# ---------------------------------------------------------------------------
# CITATION-06 — bypass_active=True + last_unverified_response preserved
# ---------------------------------------------------------------------------


def test_publish_handles_bypass_active_true(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """When the linter is in bypass mode, the payload must preserve both
    the active flag AND the unverified-response text for the UI badge +
    expandable detail line."""
    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(6, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch(
        "vibemix.runtime.coach.time.time",
        side_effect=_auto_time(start=1000.0, step=1.0),
    )

    ipc_bus = MagicMock()
    ipc_bus.emit = AsyncMock(return_value=None)
    telemetry = MagicMock(
        return_value={
            "slop_ratio": 0.7,
            "stripped_rate_15s": 0.42,
            "last_unverified_response": "this drop is wild — no evidence",
            "bypass_active": True,
        }
    )

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ipc_bus=ipc_bus,
            citation_telemetry=telemetry,
        )
    )

    assert ipc_bus.emit.await_count >= 1
    msg = ipc_bus.emit.await_args_list[0].args[0]
    assert msg["payload"]["bypass_active"] is True
    assert msg["payload"]["last_unverified_response"] == (
        "this drop is wild — no evidence"
    )
