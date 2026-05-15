# SPDX-License-Identifier: Apache-2.0
"""Plan 29-02 Task 2: DebriefWsServer progressive emit + tooltip RPC.

The full ws lifecycle (bind → connect → drain → recv tooltip-req →
reply → close) is exercised against an actual ``websockets.serve``
running on an ephemeral port.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from vibemix.debrief.chapters import ChapterRegion
from vibemix.debrief.drills import Drill, Drills
from vibemix.debrief.ws_server import DebriefWsServer

websockets = pytest.importorskip("websockets")


def _fixture_state(tmp_path: Path) -> dict:
    sess = tmp_path / "20260515-aaaa"
    sess.mkdir()
    chapters = [
        ChapterRegion(
            id="track-01",
            start=0.0,
            end=300.0,
            label="Track 1",
            kind="track",
            citation_event_id="ev:TRACK_CHANGE@0.000",
        ),
        ChapterRegion(
            id="track-02",
            start=300.0,
            end=600.0,
            label="Track 2",
            kind="track",
            citation_event_id="ev:TRACK_CHANGE@300.000",
        ),
    ]
    drills = Drills(
        drills=[
            Drill(
                situation=f"S{i}",
                behavior=f"B [ev:MIX_MOVE@01:0{i}]",
                impact=f"I [ev:PHASE@01:1{i}]",
                action_recommended=f"A [track:t{i}]",
                citation=f"[ev:MIX_MOVE@01:0{i}]",
            )
            for i in range(3)
        ]
    )
    debrief = {
        "schema_version": "v1",
        "tldr_sha256": "a" * 64,
        "tldr_path": "debrief_tldr.mp3",
    }
    evidence_snapshot = {
        "ev": {
            "MIX_MOVE": [63.0, 64.0, 65.0],
            "TRACK_CHANGE": [0.0, 300.0],
        }
    }
    return {
        "session_dir": sess,
        "chapters": chapters,
        "drills": drills,
        "debrief": debrief,
        "evidence_snapshot": evidence_snapshot,
        "voice_meta": None,
        "tldr_mp3_path": sess / "debrief_tldr.mp3",
        "cache_hit": False,
    }


def _free_port() -> int:
    """Reserve a free port at module-scope timing."""
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.anyio("asyncio")
async def test_progressive_emit_order(tmp_path: Path):
    """Client connects → receives session-loaded, chapter-list, drills,
    tldr-audio in order."""
    state = _fixture_state(tmp_path)
    port = _free_port()
    server = DebriefWsServer(port=port, state=state)
    server.enqueue_initial_frames()

    async def server_task():
        async with websockets.serve(server._handler, "127.0.0.1", port):
            await asyncio.sleep(2.0)  # window for the client test

    server_handle = asyncio.create_task(server_task())
    await asyncio.sleep(0.1)  # let server bind

    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            kinds: list[str] = []
            for _ in range(4):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                kinds.append(msg["type"])
            assert kinds == [
                "ipc.debrief.session-loaded",
                "ipc.debrief.chapter-list",
                "ipc.debrief.drills",
                "ipc.debrief.tldr-audio",
            ]
    finally:
        server_handle.cancel()
        try:
            await server_handle
        except asyncio.CancelledError:
            pass


@pytest.mark.anyio("asyncio")
async def test_citation_tooltip_request_roundtrip(tmp_path: Path):
    state = _fixture_state(tmp_path)
    port = _free_port()
    server = DebriefWsServer(port=port, state=state)
    server.enqueue_initial_frames()

    async def server_task():
        async with websockets.serve(server._handler, "127.0.0.1", port):
            await asyncio.sleep(2.0)

    server_handle = asyncio.create_task(server_task())
    await asyncio.sleep(0.1)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            # Drain the 4 initial frames.
            for _ in range(4):
                await asyncio.wait_for(ws.recv(), timeout=2.0)
            # Send tooltip request.
            from vibemix.ui_bus import DebriefCitationTooltipReq

            req = DebriefCitationTooltipReq.make(event_id="ev:MIX_MOVE@01:03").to_json()
            await ws.send(req)
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            assert msg["type"] == "ipc.debrief.citation-tooltip"
            assert msg["payload"]["found"] is True
            assert msg["payload"]["evidence_text"]
    finally:
        server_handle.cancel()
        try:
            await server_handle
        except asyncio.CancelledError:
            pass


@pytest.mark.anyio("asyncio")
async def test_emit_error_frame(tmp_path: Path):
    """Client receives an ipc.debrief.error frame when emit_error called."""
    state = _fixture_state(tmp_path)
    port = _free_port()
    server = DebriefWsServer(port=port, state=state)
    server.emit_error("events_missing", "test detail")

    async def server_task():
        async with websockets.serve(server._handler, "127.0.0.1", port):
            await asyncio.sleep(2.0)

    server_handle = asyncio.create_task(server_task())
    await asyncio.sleep(0.1)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            assert msg["type"] == "ipc.debrief.error"
            assert msg["payload"]["reason"] == "events_missing"
            assert msg["payload"]["message"] == "test detail"
    finally:
        server_handle.cancel()
        try:
            await server_handle
        except asyncio.CancelledError:
            pass


@pytest.mark.anyio("asyncio")
async def test_unknown_kind_returns_error_frame(tmp_path: Path):
    state = _fixture_state(tmp_path)
    port = _free_port()
    server = DebriefWsServer(port=port, state=state)

    async def server_task():
        async with websockets.serve(server._handler, "127.0.0.1", port):
            await asyncio.sleep(2.0)

    server_handle = asyncio.create_task(server_task())
    await asyncio.sleep(0.1)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            await ws.send(json.dumps({"type": "ipc.bogus.frame"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            assert msg["type"] == "ipc.debrief.error"
            assert msg["payload"]["reason"] == "unknown_kind"
    finally:
        server_handle.cancel()
        try:
            await server_handle
        except asyncio.CancelledError:
            pass
