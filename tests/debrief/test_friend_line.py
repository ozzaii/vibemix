# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio

from vibemix.debrief.friend_line import (
    build_gap_friend_line,
    build_morning_friend_lines,
    build_near_miss_friend_line,
    synthesize_friend_line_audio,
)
from vibemix.debrief.main import _friend_line_audio_relative_path
from vibemix.debrief.near_miss_detector import NearMissResult
from vibemix.debrief.persistence import FRIEND_LINE_MP3_FILENAME


def _near_miss(citation: str = "[mix:near_miss@42.000]") -> NearMissResult:
    return NearMissResult(
        t_center_s=42.0,
        window_start_s=36.0,
        window_end_s=46.0,
        depth_beats=0.16,
        recovery_bars=2.0,
        confidence=0.82,
        bpm=120.0,
        phase_error_beats_peak=0.16,
        citation=citation,
        event_type="MIX_MOVE",
        event_t_s=40.0,
    )


def test_near_miss_friend_line_resolves_detector_atom() -> None:
    line = build_near_miss_friend_line(_near_miss(), {})

    assert line is not None
    assert line.kind == "near_miss"
    assert "the mix" in line.text
    assert "deck" not in line.text.lower()
    assert "80 ms late" in line.text
    assert line.citation == "[mix:near_miss@42.000]"
    assert line.citation in line.receipt_text


def test_near_miss_friend_line_rejects_decorative_citation() -> None:
    line = build_near_miss_friend_line(_near_miss("[mix:near_miss@99.000]"), {})

    assert line is None


def test_gap_friend_line_uses_resolving_phase_event() -> None:
    events = [
        {"kind": "session_start", "t": 0.0},
        {"kind": "event", "type": "PHASE", "phase": "breakdown", "t": 60.0, "bpm": 120.0},
        {"kind": "event", "type": "PHASE", "phase": "peak", "t": 92.0, "bpm": 120.0},
    ]
    snapshot = {"ev": {"PHASE": [60.0, 92.0]}}

    line = build_gap_friend_line(events, snapshot)

    assert line is not None
    assert line.kind == "gap"
    assert "breakdown" in line.text
    assert "16 bars" in line.text
    assert line.citation == "[ev:PHASE@60.000]"


def test_gap_friend_line_rejects_unresolving_phase_event() -> None:
    events = [
        {"kind": "event", "type": "PHASE", "phase": "breakdown", "t": 60.0, "bpm": 120.0},
        {"kind": "event", "type": "PHASE", "phase": "peak", "t": 92.0, "bpm": 120.0},
    ]

    assert build_gap_friend_line(events, {"ev": {"PHASE": [12.0]}}) is None


def test_morning_friend_lines_honest_nulls_independently() -> None:
    payload = build_morning_friend_lines(
        near_miss=_near_miss(),
        events=[],
        evidence_snapshot={},
    )

    assert payload.near_miss is not None
    assert payload.gap is None
    assert payload.to_dict()["near_miss"]["kind"] == "near_miss"


def test_synthesize_friend_line_audio_uses_line_voice_seam() -> None:
    line = build_near_miss_friend_line(_near_miss(), {})
    assert line is not None
    calls = []

    async def fake_synthesizer(adapter, text):
        calls.append((adapter, text))
        return ("audio", 24_000)

    audio, sample_rate = asyncio.run(
        synthesize_friend_line_audio(
            line,
            adapter_factory=lambda: "adapter",
            line_synthesizer=fake_synthesizer,
        )
    )

    assert (audio, sample_rate) == ("audio", 24_000)
    assert calls == [("adapter", line.text)]


def test_friend_line_audio_relative_path_writes_optional_mp3(tmp_path) -> None:
    line = build_near_miss_friend_line(_near_miss(), {})
    assert line is not None

    relative = _friend_line_audio_relative_path(
        tmp_path,
        line,
        synthesizer=lambda text: f"mp3:{text}".encode(),
    )

    assert relative == FRIEND_LINE_MP3_FILENAME
    assert (tmp_path / FRIEND_LINE_MP3_FILENAME).read_bytes().startswith(b"mp3:I heard")


def test_friend_line_audio_relative_path_reuses_existing_file(tmp_path) -> None:
    line = build_near_miss_friend_line(_near_miss(), {})
    assert line is not None
    (tmp_path / FRIEND_LINE_MP3_FILENAME).write_bytes(b"old-mp3")

    def explode(_text: str) -> bytes:
        raise AssertionError("should not resynthesize")

    relative = _friend_line_audio_relative_path(tmp_path, line, synthesizer=explode)

    assert relative == FRIEND_LINE_MP3_FILENAME
    assert (tmp_path / FRIEND_LINE_MP3_FILENAME).read_bytes() == b"old-mp3"


def test_friend_line_audio_relative_path_fails_soft(tmp_path) -> None:
    line = build_near_miss_friend_line(_near_miss(), {})
    assert line is not None

    def fail(_text: str) -> bytes:
        raise RuntimeError("tts unavailable")

    relative = _friend_line_audio_relative_path(tmp_path, line, synthesizer=fail)

    assert relative is None
    assert not (tmp_path / FRIEND_LINE_MP3_FILENAME).exists()
