# SPDX-License-Identifier: Apache-2.0
"""Contracts for the live Course 3 lens socket probe."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
from pathlib import Path

import websockets
from scripts import live_course3_lens_probe as probe

from vibemix.audio import WS_HOST


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((WS_HOST, 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _flat_frame(lens: dict) -> dict:
    return {
        "music": 0.1,
        "audible": True,
        "deck": "A",
        "phase": "groove",
        "bpm": 128.0,
        "bpm_confidence": 0.9,
        "deck_state": {
            "A": {
                "title": "Ready",
                "track_id": "track-1",
                "confidence": 0.85,
            }
        },
        "voice": 0.0,
        "mic": 0.0,
        "course3_lens": lens,
    }


def test_extract_course3_lens_ignores_typed_ipc_frames() -> None:
    assert probe.extract_course3_lens({"type": "ipc.session.snapshot"}) is None
    lens = {
        "session_active": False,
        "phrase_position_confidence": 0.0,
        "next_phrase_at": None,
        "next_phrase_cue_id": None,
    }
    assert probe.extract_course3_lens(_flat_frame(lens)) == lens


def test_extract_course3_context_keeps_flat_frame_evidence() -> None:
    lens = {
        "session_active": False,
        "phrase_position_confidence": 0.0,
        "next_phrase_at": None,
        "next_phrase_cue_id": None,
    }
    context = probe.extract_course3_context(_flat_frame(lens))

    assert context is not None
    assert context["music"] == 0.1
    assert context["audible"] is True
    assert context["deck"] == "A"
    assert context["deck_state"]["A"]["track_id"] == "track-1"


def test_lens_has_count_in_requires_active_cue_backed_boundary() -> None:
    assert probe.lens_has_count_in(
        {
            "session_active": True,
            "phrase_position_confidence": 0.85,
            "next_phrase_at": 108.0,
            "next_phrase_cue_id": "track:breakdown@64.0",
        }
    )
    assert not probe.lens_has_count_in(
        {
            "session_active": True,
            "phrase_position_confidence": 0.5,
            "next_phrase_at": 108.0,
            "next_phrase_cue_id": "track:breakdown@64.0",
        }
    )
    assert not probe.lens_has_count_in(
        {
            "session_active": True,
            "phrase_position_confidence": 0.85,
            "next_phrase_at": 108.0,
            "next_phrase_cue_id": None,
        }
    )


def test_probe_help_runs_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/live_course3_lens_probe.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "Course 3 live lens evidence" in proc.stdout


def test_probe_passes_when_server_sends_count_in_lens() -> None:
    async def run() -> None:
        port = _free_port()
        frame = _flat_frame(
            {
                "session_active": True,
                "phrase_position_confidence": 0.85,
                "next_phrase_at": 108.0,
                "next_phrase_cue_id": "track:breakdown@64.0",
            }
        )

        async def handler(ws):
            await ws.send(json.dumps(frame))
            await asyncio.sleep(0.05)

        server = await websockets.serve(handler, WS_HOST, port)
        try:
            summary = await probe.run_course3_lens_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=2.0,
                require_count_in=True,
            )
        finally:
            server.close()
            await server.wait_closed()

        assert summary["passed"] is True
        assert summary["active_seen"] is True
        assert summary["count_in_seen"] is True
        assert summary["last_lens"] == frame["course3_lens"]
        assert summary["audible_seen"] is True
        assert summary["deck_values"] == ["A"]
        assert summary["citable_deck_state_seen"] is True
        assert summary["diagnostics"]["blockers"] == []

    asyncio.run(run())


def test_probe_can_start_course3_lesson_before_watching_lens() -> None:
    async def run() -> None:
        port = _free_port()
        received: list[dict] = []
        lens = {
            "session_active": True,
            "phrase_position_confidence": 0.85,
            "next_phrase_at": 108.0,
            "next_phrase_cue_id": "track:breakdown@64.0",
        }

        async def handler(ws):
            raw = await ws.recv()
            received.append(json.loads(raw))
            await ws.send(
                json.dumps(
                    {
                        "type": "ipc.learn.lesson_loaded",
                        "payload": {"lesson_id": "L3.01"},
                    }
                )
            )
            await ws.send(json.dumps(_flat_frame(lens)))
            await asyncio.sleep(0.05)

        server = await websockets.serve(handler, WS_HOST, port)
        try:
            summary = await probe.run_course3_lens_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=2.0,
                require_count_in=True,
                start_lesson_id="L3.01",
            )
        finally:
            server.close()
            await server.wait_closed()

        assert received[0]["type"] == "ipc.learn.start_lesson"
        assert received[0]["payload"] == {"lesson_id": "L3.01", "level": "fresh"}
        assert summary["passed"] is True
        assert summary["start_sent"] is True
        assert summary["lesson_loaded"] is True
        assert summary["start_lesson_id"] == "L3.01"

    asyncio.run(run())


def test_probe_diagnostics_explain_audible_audio_with_no_deck() -> None:
    async def run() -> None:
        port = _free_port()
        lens = {
            "session_active": False,
            "phrase_position_confidence": 0.0,
            "next_phrase_at": None,
            "next_phrase_cue_id": None,
            "blockers": ["waiting_for_deck", "waiting_for_deck_track", "waiting_for_cue"],
            "operator_action": {
                "prompt": "Open one channel.",
                "steps": [
                    "Open one deck channel so the coach can attribute deck A or B.",
                    "Keep the master up while the live lens listens.",
                ],
            },
        }
        frame = _flat_frame(lens)
        frame["deck"] = "none"
        frame["deck_state"] = {}

        async def handler(ws):
            await ws.send(json.dumps(frame))
            await asyncio.sleep(0.05)

        server = await websockets.serve(handler, WS_HOST, port)
        try:
            summary = await probe.run_course3_lens_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=2.0,
                require_count_in=True,
            )
        finally:
            server.close()
            await server.wait_closed()

        assert summary["passed"] is False
        assert summary["max_music"] == 0.1
        assert summary["audible_seen"] is True
        assert summary["deck_values"] == []
        assert summary["lens_blockers"] == [
            "waiting_for_cue",
            "waiting_for_deck",
            "waiting_for_deck_track",
        ]
        assert "audible deck stayed none" in summary["diagnostics"]["blockers"]
        assert "deck_state stayed empty" in summary["diagnostics"]["blockers"]
        assert "no cue-backed next phrase count-in was observed" in summary["diagnostics"]["blockers"]
        assert summary["operator_action"]["prompt"] == "Open one channel."
        assert summary["diagnostics"]["operator_action"]["steps"][0].startswith(
            "Open one deck channel"
        )

    asyncio.run(run())


def test_probe_preserves_observed_lens_operator_action() -> None:
    async def run() -> None:
        port = _free_port()
        lens = {
            "session_active": True,
            "phrase_position_confidence": 0.0,
            "next_phrase_at": None,
            "next_phrase_cue_id": None,
            "blockers": ["waiting_for_audio", "waiting_for_cue"],
            "operator_action": {
                "prompt": "Press play on deck.",
                "steps": [
                    "Load and play a real Rekordbox library track.",
                    "Raise the playing channel fader and master until the status changes.",
                ],
            },
        }
        frame = _flat_frame(lens)
        frame["music"] = 0.0
        frame["audible"] = False
        frame["deck"] = "none"
        frame["deck_state"] = {}

        async def handler(ws):
            await ws.send(json.dumps(frame))
            await asyncio.sleep(0.05)

        server = await websockets.serve(handler, WS_HOST, port)
        try:
            summary = await probe.run_course3_lens_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=2.0,
                require_count_in=True,
            )
        finally:
            server.close()
            await server.wait_closed()

        assert summary["passed"] is False
        assert summary["operator_action"] == {
            "prompt": "Press play on deck.",
            "steps": [
                "Load and play a real Rekordbox library track.",
                "Raise the playing channel fader and master until the status changes.",
            ],
        }
        assert summary["diagnostics"]["operator_action"] == summary["operator_action"]

    asyncio.run(run())
