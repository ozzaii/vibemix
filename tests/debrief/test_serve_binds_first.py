# SPDX-License-Identifier: Apache-2.0
"""Bind-first serve: 8766 accepts while generation is still running, and
errors are served persistently — the retrying renderer can never miss them."""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from pathlib import Path

import pytest

import vibemix.debrief.main as main_mod
from vibemix.debrief.session_loader import EventsMissing

websockets = pytest.importorskip("websockets")


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _connect_with_retry(port: int, attempts: int = 40):
    for _ in range(attempts):
        try:
            return await websockets.connect(f"ws://127.0.0.1:{port}")
        except OSError:
            await asyncio.sleep(0.05)
    raise AssertionError("server never bound")


@pytest.mark.anyio("asyncio")
async def test_socket_accepts_while_generation_still_running(
    monkeypatch, tmp_path: Path
):
    release = threading.Event()
    started = threading.Event()

    def fake_generate(session_dir, *, client=None, recordings_root=None, progress=None):
        started.set()
        release.wait(timeout=10)
        state = {
            "session_dir": tmp_path / "s",
            "chapters": [],
            "drills": None,
            "debrief": None,
            "evidence_snapshot": {},
            "voice_meta": None,
            "duration_s": 300.0,
            "near_miss_payload": None,
            "tldr_mp3_path": tmp_path / "s" / "debrief_tldr.mp3",
            "cache_hit": False,
        }
        if progress is not None:
            progress("loaded", state)
        return state

    monkeypatch.setattr(main_mod, "_generate", fake_generate)
    port = _free_port()
    task = asyncio.create_task(
        main_mod._serve_and_generate("sess", recordings_root=tmp_path, port=port)
    )
    try:
        ws = await _connect_with_retry(port)
        assert started.wait(timeout=2)
        assert not release.is_set()  # connected BEFORE generation finished
        release.set()
        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        assert json.loads(raw)["type"] == "ipc.debrief.session-loaded"
        await ws.close()
    finally:
        release.set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.anyio("asyncio")
async def test_generation_error_is_served_persistently(monkeypatch, tmp_path: Path):
    def fake_generate(session_dir, *, client=None, recordings_root=None, progress=None):
        raise EventsMissing(tmp_path / "s")

    monkeypatch.setattr(main_mod, "_generate", fake_generate)
    port = _free_port()
    task = asyncio.create_task(
        main_mod._serve_and_generate("sess", recordings_root=tmp_path, port=port)
    )
    try:
        # Connect LATE — past where the old 2s one-shot error server died.
        await asyncio.sleep(2.5)
        ws = await _connect_with_retry(port)
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "ipc.debrief.error"
        assert msg["payload"]["reason"] == "events_missing"
        await ws.close()
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
