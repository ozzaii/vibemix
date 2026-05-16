# SPDX-License-Identifier: Apache-2.0
"""Plan 29-02 Task 1: main.run orchestrator dispatch + cache-hit path."""

from __future__ import annotations

import hashlib
import json
import shutil
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief import EventsMissing, SessionTooShort
from vibemix.debrief.main import run


def _build_session(root: Path, name: str = "20260515-aaaaaa", duration_s: float = 600.0) -> Path:
    """Build a complete fixture session under ``root``."""
    sess = root / name
    sess.mkdir(parents=True, exist_ok=True)
    events = [
        {"t": 0.0, "kind": "session_start", "wall_clock_iso": "2026-05-15T11:21:39+00:00"},
        {"t": 100.0, "kind": "event", "type": "TRACK_CHANGE", "track": "Track A"},
        {"t": 100.5, "kind": "ai_text", "text": "Strong opener.", "latency_s": 1.2},
        {"t": 300.0, "kind": "event", "type": "MIX_MOVE", "phase": "build"},
        {"t": 300.5, "kind": "ai_text", "text": "Filter sweep clean.", "latency_s": 1.0},
        {"t": duration_s, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (sess / "evidence_registry.json").write_text(
        json.dumps(
            {
                "ev": {
                    "TRACK_CHANGE": [100.0],
                    "MIX_MOVE": [300.0],
                    "HEARTBEAT": [duration_s],
                }
            }
        ),
        encoding="utf-8",
    )
    wav_path = sess / "voice.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000 * 2)
    return sess


def test_run_with_cached_debrief_skips_gemini(tmp_path: Path):
    """When session_debrief.json + tldr.mp3 are present with matching
    sha256, ``run`` returns the cached state without calling Gemini."""
    root = tmp_path / "recordings"
    root.mkdir()
    sess = _build_session(root)

    mp3 = b"FAKEMP3BYTES" * 200
    sha = hashlib.sha256(mp3).hexdigest()
    (sess / "debrief_tldr.mp3").write_bytes(mp3)
    (sess / "session_debrief.json").write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "chapters": [{"id": "track-01", "start": 100.0, "end": 600.0,
                              "label": "Track 1: Track A", "kind": "track",
                              "citation_event_id": "ev:TRACK_CHANGE@100.000"}],
                "drills": [
                    {"situation": "S", "behavior": "B [ev:M@1]",
                     "impact": "I [ev:P@2]", "action_recommended": "A [track:t1]",
                     "citation": "[ev:M@1]"} for _ in range(3)
                ],
                "tldr_sha256": sha,
                "tldr_path": "debrief_tldr.mp3",
                "generated_at": "2026-05-15T12:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    client = MagicMock()
    state = run(sess, client=client, recordings_root=root, serve=False)
    assert state["cache_hit"] is True
    # No Gemini calls.
    client.models.generate_content.assert_not_called()


def test_run_first_time_generation_calls_gemini(tmp_path: Path, monkeypatch):
    """First-time run with no cache calls drills + tldr Gemini paths."""
    root = tmp_path / "recordings"
    root.mkdir()
    sess = _build_session(root)

    from vibemix.debrief.drills import Drill, Drills

    drills_response = SimpleNamespace(
        parsed=Drills(
            drills=[
                Drill(
                    situation=f"S{i}",
                    behavior=f"B [ev:MIX_MOVE@05:00]",
                    impact=f"I [ev:TRACK_CHANGE@01:40]",
                    action_recommended=f"A [ev:HEARTBEAT@10:00]",
                    citation="[ev:MIX_MOVE@05:00]",
                )
                for i in range(3)
            ]
        ),
        text="",
    )

    # Build a fake TTS PCM response.
    pcm = b"\x00\x00" * 24000  # 1 sec silence
    inline = SimpleNamespace(inline_data=SimpleNamespace(data=pcm))
    tts_response = SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=[inline]))]
    )

    text_response = SimpleNamespace(
        text="First cited [ev:MIX_MOVE@05:00]. Second [ev:TRACK_CHANGE@01:40]."
    )

    client = MagicMock()
    client.models.generate_content.side_effect = [
        drills_response,  # drills call
        text_response,    # tldr text
        tts_response,     # tldr tts
    ]
    state = run(sess, client=client, recordings_root=root, serve=False)
    assert state["cache_hit"] is False
    assert (sess / "debrief_tldr.mp3").exists()
    assert (sess / "session_debrief.json").exists()
    # All 3 Gemini calls happened.
    assert client.models.generate_content.call_count == 3


def test_run_invalid_session_dir_raises(tmp_path: Path):
    from vibemix.debrief import InvalidSessionDir

    root = tmp_path / "recordings"
    root.mkdir()
    with pytest.raises(InvalidSessionDir):
        run(
            tmp_path / "outside",
            client=MagicMock(),
            recordings_root=root,
            serve=False,
        )


def test_run_session_too_short_raises(tmp_path: Path):
    """Build a session whose events span < 5 minutes total."""
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-shorty"
    sess.mkdir()
    # All events within a 120s span.
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 50.0, "kind": "event", "type": "TRACK_CHANGE"},
        {"t": 120.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    wav_path = sess / "voice.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000)
    with pytest.raises(SessionTooShort):
        run(sess, client=MagicMock(), recordings_root=root, serve=False)


def test_run_missing_events_raises(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-zzzzzz"
    sess.mkdir()
    with pytest.raises(EventsMissing):
        run(sess, client=MagicMock(), recordings_root=root, serve=False)
