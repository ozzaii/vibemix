# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 06 — POC compatibility tests (REC-01/02/03/04).

Opens a recording produced by the shipping ``VoiceRecorder`` using the raw
``wave`` + ``json`` APIs that ``cohost_v4.py:771-850`` uses to read its own
sessions — no project helpers. The whole point of this file is to prove the
v4 POC reader shape can still consume the new recording layout AFTER
Phase 15-02 added session.json as an ADDITIVE artifact (the events.jsonl
first-line ``session_start`` marker still exists; session.json sits
alongside).

Invariants pinned:

    REC-01: session_dir name matches r"^\\d{8}-\\d{6}$".
    REC-02: input.wav opens with nchannels=1, sampwidth=2, framerate=16000.
    REC-03: voice.wav opens with nchannels=1, sampwidth=2, framerate=24000.
    REC-04: every events.jsonl line parses as JSON; first line kind ==
            "session_start" with wall_clock_iso + wall_clock_unix +
            session_dir fields.

    Additivity (Phase 15-02 contract): session.json exists alongside the
    JSONL header — does NOT replace it. session.json.started_at_unix ==
    first events.jsonl line.wall_clock_unix. session.json includes
    ``session_json_version`` field per autonomous resolution #5.
"""

from __future__ import annotations

import json
import re
import wave
from pathlib import Path
from typing import Iterator

import numpy as np
import pytest

from vibemix.audio.recorder import VoiceRecorder


# ---------------------------------------------------------------------------
# Fixture — one fresh recording produced by the shipping recorder
# ---------------------------------------------------------------------------


@pytest.fixture
def recorded_session(tmp_path: Path) -> Iterator[Path]:
    """Construct a real VoiceRecorder, push canned PCM + events, close.

    Yields the session_dir Path. The recorder writes:
      - voice.wav: 1.0s of zero-filled int16 PCM @24kHz
      - input.wav: 1.0s of zero-filled int16 PCM @16kHz
      - events.jsonl: session_start (line 0) + 3 logged events
      - session.json: Phase 15-02 finalized metadata
    """
    recorder = VoiceRecorder(
        root=tmp_path,
        voice_id="Aoede",
        mode="hype",
        genre="techno",
        user_level="intermediate",
    )
    # 1s of silence at each rate — zero-filled int16 mono.
    input_pcm = np.zeros(16000, dtype=np.int16).tobytes()
    voice_pcm = np.zeros(24000, dtype=np.int16).tobytes()
    recorder.push_input(input_pcm)
    recorder.push_voice(voice_pcm)
    recorder.log_event("trigger", reason="test1")
    recorder.log_event("trigger", reason="test2")
    recorder.log_event("ai_text", text="hi")
    recorder.close()
    yield recorder.session_dir


# ---------------------------------------------------------------------------
# Test 1 — REC-01: session_dir name format
# ---------------------------------------------------------------------------


def test_session_dir_name_matches_canonical_format(recorded_session: Path) -> None:
    """REC-01: ``recordings/<YYYYMMDD-HHMMSS>/`` is the canonical layout."""
    assert re.match(r"^\d{8}-\d{6}$", recorded_session.name), (
        f"session_dir name {recorded_session.name!r} does not match the "
        f"YYYYMMDD-HHMMSS regex required by cohost_v4.py:779."
    )


# ---------------------------------------------------------------------------
# Test 2 — REC-02: input.wav format (16kHz mono int16)
# ---------------------------------------------------------------------------


def test_input_wav_is_16khz_mono_int16(recorded_session: Path) -> None:
    """REC-02: input.wav opens via stdlib ``wave`` with the canonical format.

    Mirrors the cohost_v4.py reader shape — no project imports, just stdlib.
    """
    input_wav = recorded_session / "input.wav"
    assert input_wav.exists(), "input.wav should be written by VoiceRecorder"
    with wave.open(str(input_wav), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 16000


# ---------------------------------------------------------------------------
# Test 3 — REC-03: voice.wav format (24kHz mono int16)
# ---------------------------------------------------------------------------


def test_voice_wav_is_24khz_mono_int16(recorded_session: Path) -> None:
    """REC-03: voice.wav opens via stdlib ``wave`` with the canonical format."""
    voice_wav = recorded_session / "voice.wav"
    assert voice_wav.exists(), "voice.wav should be written by VoiceRecorder"
    with wave.open(str(voice_wav), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000


# ---------------------------------------------------------------------------
# Test 4 — REC-04: events.jsonl is parseable + session_start header intact
# ---------------------------------------------------------------------------


def test_events_jsonl_is_parseable_and_starts_with_session_start(
    recorded_session: Path,
) -> None:
    """REC-04: every line of events.jsonl is valid JSON; first line is the
    cohost_v4-shape ``session_start`` event.

    The session_start line MUST carry wall_clock_iso + wall_clock_unix +
    session_dir fields — these are what the v4 POC analysis tools key off.
    """
    events_path = recorded_session / "events.jsonl"
    assert events_path.exists(), "events.jsonl should be written by VoiceRecorder"

    with events_path.open(encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]

    assert len(lines) >= 1, "events.jsonl must contain at least the session_start line"

    parsed = [json.loads(line) for line in lines]  # raises on malformed line

    # First line is the session_start marker — the canonical v4 shape.
    first = parsed[0]
    assert first["kind"] == "session_start", (
        f"first events.jsonl line must be session_start; got kind={first.get('kind')!r}"
    )
    assert first["t"] == 0.0
    assert isinstance(first["wall_clock_iso"], str) and first["wall_clock_iso"]
    assert isinstance(first["wall_clock_unix"], float)
    assert first["wall_clock_unix"] > 0.0
    assert first["session_dir"] == recorded_session.name

    # Subsequent events should all have t >= 0 and a kind field.
    for rec in parsed[1:]:
        assert "t" in rec and isinstance(rec["t"], (int, float))
        assert rec["t"] >= 0.0
        assert "kind" in rec and isinstance(rec["kind"], str)


# ---------------------------------------------------------------------------
# Test 5 — Additivity: session.json sits alongside; JSONL header intact
# ---------------------------------------------------------------------------


def test_session_json_is_additive_to_events_jsonl_header(
    recorded_session: Path,
) -> None:
    """Phase 15-02 contract: session.json is ADDITIVE.

    The first events.jsonl line is still ``kind == "session_start"``.
    session.json contains the same wall-clock anchor: its
    ``started_at_unix`` matches the JSONL header's ``wall_clock_unix``.
    """
    session_json_path = recorded_session / "session.json"
    assert session_json_path.exists(), "session.json should be written by Plan 15-02"

    meta = json.loads(session_json_path.read_text(encoding="utf-8"))
    assert isinstance(meta, dict)

    # Required Phase 15-02 fields — surfaced to UI + sweep.
    assert "session_json_version" in meta
    assert meta["session_json_version"] == "1.0"
    assert "vibemix_version" in meta
    assert "started_at_iso" in meta
    assert "started_at_unix" in meta
    assert isinstance(meta["started_at_unix"], (int, float))
    assert "ended_at_iso" in meta
    assert meta["ended_at_iso"] is not None, (
        "close() must populate ended_at_iso via _finalize_session_meta"
    )
    assert "duration_s" in meta
    assert isinstance(meta["duration_s"], (int, float))
    assert meta["voice"] == "Aoede"
    assert meta["mode"] == "hype"
    assert meta["genre"] == "techno"
    assert meta["user_level"] == "intermediate"
    assert meta["crashed"] is False
    # event_count is the JSONL line count minus the session_start marker —
    # 3 logged events fixture-side.
    assert meta["event_count"] == 3

    # Additivity gate — JSONL header was NOT swapped out for session.json.
    events_path = recorded_session / "events.jsonl"
    with events_path.open(encoding="utf-8") as f:
        first_line = json.loads(f.readline())
    assert first_line["kind"] == "session_start", (
        "events.jsonl first line MUST still be session_start — Plan 15-02 "
        "must keep the POC header intact per CONTEXT Area 1."
    )

    # The wall-clock anchors line up — session.json is the SAME session.
    assert meta["started_at_unix"] == first_line["wall_clock_unix"], (
        f"session.json.started_at_unix ({meta['started_at_unix']}) must equal "
        f"events.jsonl session_start.wall_clock_unix ({first_line['wall_clock_unix']})"
    )
