# SPDX-License-Identifier: Apache-2.0
"""DebriefWsServer history+broadcast: late frames reach connected clients;
late clients replay the full history."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from vibemix.debrief.ws_server import DebriefWsServer

websockets = pytest.importorskip("websockets")


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _minimal_state(tmp_path: Path) -> dict:
    sess = tmp_path / "20260515-aaaa"
    sess.mkdir(exist_ok=True)
    return {
        "session_dir": sess,
        "chapters": [],
        "drills": None,
        "debrief": None,
        "evidence_snapshot": {},
        "voice_meta": None,
        "duration_s": 600.0,
        "near_miss_payload": None,
        "tldr_mp3_path": sess / "debrief_tldr.mp3",
        "cache_hit": False,
    }


@pytest.mark.anyio("asyncio")
async def test_frames_emitted_after_connect_are_delivered(tmp_path: Path):
    port = _free_port()
    server = DebriefWsServer(port=port, state=_minimal_state(tmp_path))
    async with websockets.serve(server._handler, "127.0.0.1", port):
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            await asyncio.sleep(0.05)  # handler joins the broadcast set
            server.emit_error("llm_unavailable", "late frame")
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            assert msg["type"] == "ipc.debrief.error"
            assert msg["payload"]["reason"] == "llm_unavailable"


@pytest.mark.anyio("asyncio")
async def test_second_client_replays_full_history(tmp_path: Path):
    port = _free_port()
    server = DebriefWsServer(port=port, state=_minimal_state(tmp_path))
    server.enqueue_initial_frames()
    async with websockets.serve(server._handler, "127.0.0.1", port):
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws1:
            raw = await asyncio.wait_for(ws1.recv(), timeout=2.0)
            assert json.loads(raw)["type"] == "ipc.debrief.session-loaded"
        # First client gone — a reconnecting renderer still gets everything.
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws2:
            raw = await asyncio.wait_for(ws2.recv(), timeout=2.0)
            assert json.loads(raw)["type"] == "ipc.debrief.session-loaded"
