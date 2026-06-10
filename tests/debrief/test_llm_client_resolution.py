# SPDX-License-Identifier: Apache-2.0
"""Debrief LLM client resolution mirrors the live brain (direct-first,
self-provisioned proxy auth) and degrades to local-only frames — never a
whole-window crash for the default packaged proxy-mode user."""

from __future__ import annotations

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


def test_generate_stages_fire_before_llm_unavailable_raise(monkeypatch, tmp_path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = _build_session(root)
    monkeypatch.setattr("vibemix.debrief.main._build_debrief_client", lambda: None)
    from vibemix.debrief.main import _generate

    stages: list[str] = []
    with pytest.raises(DebriefGenerationError) as ei:
        _generate(sess, recordings_root=root, progress=lambda s, st: stages.append(s))
    assert ei.value.reason == "llm_unavailable"
    assert stages == ["loaded", "near_miss", "chapters"]
