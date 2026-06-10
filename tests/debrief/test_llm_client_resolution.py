# SPDX-License-Identifier: Apache-2.0
"""Debrief LLM client resolution mirrors the live brain (direct-first,
self-provisioned proxy auth) and degrades to local-only frames — never a
whole-window crash for the default packaged proxy-mode user."""

from __future__ import annotations

import asyncio
import json
import wave
from pathlib import Path

import pytest

from vibemix.debrief.main import _build_debrief_client, run
from vibemix.debrief.tldr import DebriefGenerationError


def _build_session(root: Path, name: str = "20260515-aaaaaa") -> Path:
    sess = root / name
    sess.mkdir(parents=True, exist_ok=True)
    events = [
        {"t": 0.0, "kind": "session_start", "wall_clock_iso": "2026-05-15T11:21:39+00:00"},
        {"t": 100.0, "kind": "event", "type": "TRACK_CHANGE", "track": "Track A"},
        {"t": 100.5, "kind": "ai_text", "text": "Strong opener.", "latency_s": 1.2},
        {"t": 600.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (sess / "evidence_registry.json").write_text(
        json.dumps({"ev": {"TRACK_CHANGE": [100.0], "HEARTBEAT": [600.0]}}),
        encoding="utf-8",
    )
    with wave.open(str(sess / "voice.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000 * 2)
    return sess


def test_direct_key_builds_direct_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    assert _build_debrief_client() is not None


def test_proxy_mode_self_provisions_jwt(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")
    monkeypatch.setattr(
        "vibemix.agent.install_uuid.get_or_create_install_uuid", lambda: "u" * 32
    )

    async def fake_jwt(install_uuid, proxy_base_url, client_version):
        assert install_uuid == "u" * 32
        return "jwt-test-token"

    monkeypatch.setattr("vibemix.agent.jwt_cache.get_or_refresh_jwt", fake_jwt)
    assert _build_debrief_client() is not None


def test_no_creds_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "proxy")

    def boom():
        raise RuntimeError("keychain down")

    monkeypatch.setattr(
        "vibemix.agent.install_uuid.get_or_create_install_uuid", boom
    )
    assert _build_debrief_client() is None


def test_direct_mode_without_key_returns_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VIBEMIX_LLM_MODE", "direct")
    assert _build_debrief_client() is None


def test_run_serve_false_raises_typed_llm_unavailable(monkeypatch, tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = _build_session(root)
    monkeypatch.setattr("vibemix.debrief.main._build_debrief_client", lambda: None)
    with pytest.raises(DebriefGenerationError) as ei:
        run(sess, recordings_root=root, serve=False)
    assert ei.value.reason == "llm_unavailable"


def test_degraded_serve_state_enqueues_local_frames_plus_llm_error(tmp_path):
    from vibemix.debrief.main import _enqueue_frames_for_state
    from vibemix.debrief.ws_server import DebriefWsServer

    sess = tmp_path / "20260515-aaaa"
    sess.mkdir()
    state = {
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
        "llm_unavailable": True,
    }
    server = DebriefWsServer(port=8766, state=state)
    _enqueue_frames_for_state(server, state)
    frames = []
    while True:
        try:
            frames.append(json.loads(server._queue.get_nowait()))
        except asyncio.QueueEmpty:
            break
    kinds = [f["type"] for f in frames]
    assert kinds[0] == "ipc.debrief.session-loaded"
    assert "ipc.debrief.chapter-list" in kinds
    assert kinds[-1] == "ipc.debrief.error"
    assert frames[-1]["payload"]["reason"] == "llm_unavailable"
