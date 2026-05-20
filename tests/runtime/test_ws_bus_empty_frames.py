# SPDX-License-Identifier: Apache-2.0
"""BRINGUP-04 / BRINGUP-01 — ws_broadcast never emits empty ``{}`` frames.

A live tap of ``ws://127.0.0.1:8765`` this session showed intermittent empty
``{}`` text frames interleaved with real level frames. These tests bind a
REAL ``ws_broadcast`` server (no socket mocking) and connect a REAL
``websockets`` client, collect every TEXT frame over a sample window, and
assert the wire NEVER carries an empty / meter-less payload.

Two contracts are pinned here:

  * **test_ws_broadcast_emits_no_empty_frames** (BRINGUP-04) — over a sampled
    window every text frame decodes to a non-empty dict; every mascot frame
    (the flat frame WITHOUT a top-level ``type``) carries the meter keys
    ``music``/``voice``/``mic``; every typed ``ipc.session.snapshot`` frame
    carries a non-empty ``payload``. A non-zero frame-count guard prevents a
    silent no-op pass.

  * **test_boot_smoke_reaches_phase_silent_cleanly** (BRINGUP-01) — a default
    (idle) ``MusicState`` boots to a broadcasting state quickly: a mascot
    frame arrives within a bounded window of the client connecting, and its
    ``phase`` equals the ``MusicState`` idle/silent default — with zero empty
    frames over the window.

These are ``integration``-marked (they bind a real WS server/port), so they
ride the opt-in ``pytest -m integration`` lane.
"""

from __future__ import annotations

import asyncio
import json
import socket

import pytest
import websockets

from vibemix.audio import WS_HOST, Levels
from vibemix.runtime import ws_bus as ws_bus_mod
from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState

# A sample window long enough to capture many 30Hz mascot ticks (~15+) and
# multiple 15Hz snapshot frames, but short enough to keep the test fast.
_SAMPLE_WINDOW_S = 0.6
# Bounded "boot to broadcasting" window: a mascot frame must arrive within
# this long after the client connects (generous to avoid CI flake).
_BOOT_DEADLINE_S = 2.0


def _free_port() -> int:
    """Pick a currently-free localhost TCP port.

    The production bus binds the fixed WS_PORT (8765); binding that here would
    collide with a live ``cargo tauri dev`` session (the sidecar holds 8765)
    and is racy in CI. ws_broadcast reads ``WS_HOST``/``WS_PORT`` as module
    globals at call time, so the tests below monkeypatch ``ws_bus.WS_PORT`` to
    this ephemeral port — exercising the REAL server bind on a real socket
    without touching production behavior.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((WS_HOST, 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _is_mascot_frame(frame: dict) -> bool:
    """A mascot frame is the flat frame with NO top-level ``type`` field.

    The two emitters on the socket are (1) the flat mascot frame and (2) the
    typed ``ipc.session.snapshot`` envelope; the ``type`` key disambiguates.
    """
    return "type" not in frame


def assert_no_empty_or_meterless(frames: list[dict]) -> None:
    """Shared contract: NO frame is ``{}``; every mascot frame carries the
    three meter keys; every typed snapshot carries a non-empty payload.

    Used by both tests so the no-empty-frame invariant has a single source
    of truth.
    """
    for frame in frames:
        assert isinstance(frame, dict), f"frame is not a dict: {frame!r}"
        assert frame != {}, "ws_broadcast emitted an empty {} frame onto the wire"
        if _is_mascot_frame(frame):
            for key in ("music", "voice", "mic"):
                assert key in frame, (
                    f"mascot frame missing meter key {key!r}: {sorted(frame)}"
                )
        else:
            assert frame.get("type") == "ipc.session.snapshot", (
                f"unexpected typed frame: {frame.get('type')!r}"
            )
            payload = frame.get("payload")
            assert payload, f"typed snapshot has empty payload: {frame!r}"


async def _collect_frames(
    state: MusicState,
    *,
    window_s: float,
    port: int,
) -> list[dict]:
    """Bind a real ws_broadcast server, connect a real client, and collect
    every decoded TEXT frame over ``window_s`` seconds, then tear down.

    Returns the list of ``json.loads``-decoded frames (raises if any frame
    is not valid JSON — the wire must never carry a non-JSON text frame).
    """
    levels = Levels()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    server_task = asyncio.create_task(
        ws_broadcast(levels, state, manual_trigger, stop_event)
    )
    # Give websockets.serve a moment to bind the port before connecting.
    await asyncio.sleep(0.1)

    frames: list[dict] = []
    try:
        async with websockets.connect(f"ws://{WS_HOST}:{port}") as ws:
            deadline = asyncio.get_event_loop().time() + window_s
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                # Only TEXT frames are part of the contract; websockets hands
                # control (ping/pong) frames internally and never surfaces
                # them here, so any payload we receive must be app JSON.
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                frames.append(json.loads(raw))
    finally:
        stop_event.set()
        await server_task

    return frames


@pytest.mark.integration
def test_ws_broadcast_emits_no_empty_frames(monkeypatch):
    """BRINGUP-04: over a sampled window the bus emits ZERO ``{}`` frames and
    zero mascot frames missing the meter keys."""
    port = _free_port()
    monkeypatch.setattr(ws_bus_mod, "WS_PORT", port)

    state = MusicState()
    # Realistic broadcasting state so phase/deck resolve to non-default values.
    state.audible = True
    state.audible_deck = "B"
    state.phase = "groove"
    state.bpm = 128.0

    frames = asyncio.run(
        _collect_frames(state, window_s=_SAMPLE_WINDOW_S, port=port)
    )

    # Non-zero frame-count guard — a silent no-op (zero frames) must FAIL.
    assert len(frames) > 0, "collected zero frames — server never broadcast"
    # At least one mascot frame must have been observed (the 30Hz stream).
    assert any(_is_mascot_frame(f) for f in frames), (
        "no mascot frame observed in the sample window"
    )
    assert_no_empty_or_meterless(frames)


@pytest.mark.integration
def test_boot_smoke_reaches_phase_silent_cleanly(monkeypatch):
    """BRINGUP-01: a default (idle) MusicState boots to a broadcasting state
    quickly; the first mascot frames carry ``phase`` == the idle/silent
    default; zero empty frames over the window."""
    port = _free_port()
    monkeypatch.setattr(ws_bus_mod, "WS_PORT", port)

    idle_state = MusicState()
    idle_phase = idle_state.phase  # read the real default, do not hard-code

    async def _run() -> tuple[list[dict], float]:
        levels = Levels()
        manual_trigger = asyncio.Event()
        stop_event = asyncio.Event()
        server_task = asyncio.create_task(
            ws_broadcast(levels, idle_state, manual_trigger, stop_event)
        )
        await asyncio.sleep(0.1)

        collected: list[dict] = []
        first_mascot_at: float | None = None
        try:
            async with websockets.connect(f"ws://{WS_HOST}:{port}") as ws:
                connect_t = asyncio.get_event_loop().time()
                deadline = connect_t + _BOOT_DEADLINE_S
                while asyncio.get_event_loop().time() < deadline:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        break
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    frame = json.loads(raw)
                    collected.append(frame)
                    if first_mascot_at is None and _is_mascot_frame(frame):
                        first_mascot_at = asyncio.get_event_loop().time() - connect_t
                    # Once we have a mascot frame plus a couple more ticks, the
                    # boot signal is proven — stop early to keep the test fast.
                    if first_mascot_at is not None and len(collected) >= 6:
                        break
        finally:
            stop_event.set()
            await server_task
        return collected, (first_mascot_at if first_mascot_at is not None else -1.0)

    frames, first_mascot_at = asyncio.run(_run())

    # (a) the bus reached a broadcasting state within the bounded window.
    assert first_mascot_at >= 0.0, (
        f"no mascot frame within {_BOOT_DEADLINE_S}s of connecting"
    )
    assert first_mascot_at < _BOOT_DEADLINE_S, (
        f"mascot frame arrived too late: {first_mascot_at:.3f}s"
    )
    # (b) phase on the mascot frames equals the MusicState idle/silent default.
    mascot_frames = [f for f in frames if _is_mascot_frame(f)]
    assert mascot_frames, "no mascot frames collected in boot-smoke"
    for f in mascot_frames:
        assert f["phase"] == idle_phase, (
            f"expected idle phase {idle_phase!r}, got {f['phase']!r}"
        )
    # Sanity-pin the documented idle value so a future default change is loud.
    assert idle_phase == "silent", (
        f"MusicState idle phase changed from 'silent' to {idle_phase!r}"
    )
    # (c) zero empty / meter-less frames over the window.
    assert_no_empty_or_meterless(frames)
