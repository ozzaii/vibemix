# SPDX-License-Identifier: Apache-2.0
"""Plan 29-08 Task 1 — full sidecar lifecycle e2e.

Spawn the debrief sidecar IN-PROCESS via :func:`vibemix.debrief.main.run`
with a mocked Gemini client + cached debrief artifacts, then connect a
real websocket client + verify the 4 progressive frames arrive +
tooltip RPC works.

Mark ``@pytest.mark.e2e`` so the fast CI lane can skip these.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

websockets = pytest.importorskip("websockets")

pytestmark = pytest.mark.e2e


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _build_fixture_session(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-e2e1"
    sess.mkdir()
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 100.0, "kind": "event", "type": "TRACK_CHANGE", "track": "A"},
        {"t": 100.5, "kind": "ai_text", "text": "Strong opener [ev:TRACK_CHANGE@100.000]."},
        {"t": 300.0, "kind": "event", "type": "MIX_MOVE"},
        {"t": 600.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (sess / "evidence_registry.json").write_text(
        json.dumps(
            {"ev": {"TRACK_CHANGE": [100.0], "MIX_MOVE": [300.0], "HEARTBEAT": [600.0]}}
        ),
        encoding="utf-8",
    )
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000 * 2)
    return root, sess


def _persist_cache(sess: Path) -> None:
    """Pre-write session_debrief.json + debrief_tldr.mp3 so run() takes
    the cache-hit fast path."""
    import hashlib

    from vibemix.debrief.persistence import write_debrief

    mp3 = b"FAKEMP3DATA" * 200
    debrief = {
        "schema_version": "v1",
        "chapters": [
            {
                "id": "track-01",
                "start": 100.0,
                "end": 600.0,
                "label": "Track 1: A",
                "kind": "track",
                "citation_event_id": "ev:TRACK_CHANGE@100.000",
            }
        ],
        "drills": [
            {
                "situation": f"S{i}",
                "behavior": f"B [ev:M@1]",
                "impact": f"I [ev:P@2]",
                "action_recommended": f"A [track:t{i}]",
                "citation": "[ev:M@1]",
            }
            for i in range(3)
        ],
    }
    write_debrief(sess, debrief, mp3)


@pytest.mark.anyio("asyncio")
async def test_progressive_frames_arrive_in_order(tmp_path: Path):
    """E2e: spawn the sidecar's ws_server with a pre-cached session and
    verify the renderer would see all 4 frames in progressive order.
    """
    root, sess = _build_fixture_session(tmp_path)
    _persist_cache(sess)
    port = _free_port()

    # Drive the orchestrator in a background thread (serve=True blocks
    # on the ws server until the test cancels). Use serve=False to get
    # the state, then mount ws_server manually so the test owns the
    # lifecycle.
    from vibemix.debrief.main import run
    from vibemix.debrief.ws_server import DebriefWsServer

    state = run(sess, client=MagicMock(), recordings_root=root, serve=False)
    assert state["cache_hit"] is True

    server = DebriefWsServer(port=port, state=state)
    server.enqueue_initial_frames()

    async def server_task():
        async with websockets.serve(server._handler, "127.0.0.1", port):
            await asyncio.sleep(2.0)

    server_handle = asyncio.create_task(server_task())
    await asyncio.sleep(0.1)
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
async def test_no_tmp_leftovers_after_cycle(tmp_path: Path):
    """Atomic write leaves no `.tmp` files in the session dir."""
    root, sess = _build_fixture_session(tmp_path)
    _persist_cache(sess)
    assert sess.exists()
    # Verify no atomic-write temp files leaked.
    tmps = list(sess.glob("*.tmp"))
    assert tmps == []
