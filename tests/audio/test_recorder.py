# SPDX-License-Identifier: Apache-2.0
"""Tests for vibemix.audio.VoiceRecorder.

Verbatim port from cohost_v4.py:771-850 with the configurable-root
+ 0o700-perms improvements per 02-PATTERNS.md anti-patterns 4 and
RESEARCH.md Security V8.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

from vibemix.audio import VoiceRecorder
from vibemix.audio.constants import INPUT_SR_TARGET, OUTPUT_SR


def _find_session_dir(root: Path) -> Path:
    """The recordings dir contains exactly one timestamp subdir after one VoiceRecorder()."""
    subdirs = [p for p in root.iterdir() if p.is_dir()]
    assert len(subdirs) == 1, f"expected 1 session dir, got {len(subdirs)}: {subdirs}"
    return subdirs[0]


# ===== REC-01: 0o700 perms =====


def test_voice_recorder_creates_session_dir_with_0700_perms(tmp_path: Path) -> None:
    """Session dir has mode 0o700 (Kaan's voice = privacy-sensitive). RESEARCH.md V8."""
    rec = VoiceRecorder(root=tmp_path)
    session = _find_session_dir(tmp_path)
    try:
        mode = session.stat().st_mode & 0o777
        assert mode == 0o700, f"expected 0o700, got {oct(mode)}"
    finally:
        rec.close()


# ===== REC-02: input.wav header =====


def test_voice_recorder_writes_input_wav_with_correct_header(tmp_path: Path) -> None:
    """input.wav is mono, sampwidth=2 (int16), framerate=INPUT_SR_TARGET=16000."""
    rec = VoiceRecorder(root=tmp_path)
    pcm = np.full(1600, 1234, dtype=np.int16).tobytes()
    rec.push_input(pcm)
    rec.close()

    session = _find_session_dir(tmp_path)
    with wave.open(str(session / "input.wav"), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == INPUT_SR_TARGET
        assert w.getframerate() == 16000  # belt + braces


# ===== REC-03: voice.wav 24kHz =====


def test_voice_recorder_writes_voice_wav_with_24khz_framerate(tmp_path: Path) -> None:
    """voice.wav is mono, sampwidth=2, framerate=OUTPUT_SR=24000."""
    rec = VoiceRecorder(root=tmp_path)
    rec.push_voice(np.full(2400, 5678, dtype=np.int16).tobytes())
    rec.close()

    session = _find_session_dir(tmp_path)
    with wave.open(str(session / "voice.wav"), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == OUTPUT_SR
        assert w.getframerate() == 24000


# ===== REC-04: events.jsonl session_start =====


def test_events_jsonl_first_line_is_session_start(tmp_path: Path) -> None:
    """Line 1 of events.jsonl is a JSON `session_start` record per v4:794-801."""
    rec = VoiceRecorder(root=tmp_path)
    rec.close()

    session = _find_session_dir(tmp_path)
    with open(session / "events.jsonl", encoding="utf-8") as f:
        line = f.readline()
    rec_dict = json.loads(line)
    assert rec_dict["t"] == 0.0
    assert rec_dict["kind"] == "session_start"
    assert "wall_clock_iso" in rec_dict
    assert "wall_clock_unix" in rec_dict
    assert "session_dir" in rec_dict


# ===== REC-05: log_event appends with relative t =====


def test_log_event_appends_jsonl_with_relative_t(tmp_path: Path) -> None:
    """log_event writes `{t: seconds_from_start, kind, **fields}` after session_start."""
    rec = VoiceRecorder(root=tmp_path)
    rec.log_event("trigger", reason="test", count=3)
    rec.close()

    session = _find_session_dir(tmp_path)
    lines = (session / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2  # session_start + trigger
    last = json.loads(lines[-1])
    assert last["kind"] == "trigger"
    assert last["reason"] == "test"
    assert last["count"] == 3
    assert isinstance(last["t"], float)
    assert last["t"] >= 0.0


# ===== REC-06: configurable root =====


def test_voice_recorder_configurable_root_writes_to_custom_dir(tmp_path: Path) -> None:
    """`VoiceRecorder(root=...)` overrides the default `cwd()/recordings` path.

    Fixes the v4:773 anti-pattern that would write WAVs into site-packages on a
    packaged install (02-PATTERNS.md §AntiPatterns-4).
    """
    custom_root = tmp_path / "custom" / "deep" / "nested"
    rec = VoiceRecorder(root=custom_root)
    assert custom_root.exists()
    assert rec.session_dir.parent == custom_root
    rec.close()


# ===== REC-07: push_voice empty bytes no-op =====


def test_push_voice_empty_bytes_no_op(tmp_path: Path) -> None:
    """Empty bytes early-return — no exception, no write. v4:807-808."""
    rec = VoiceRecorder(root=tmp_path)
    rec.push_voice(b"")
    rec.push_input(b"")
    rec.close()
    # File still exists and is a valid empty WAV
    session = _find_session_dir(tmp_path)
    assert (session / "voice.wav").exists()
    assert (session / "input.wav").exists()


# ===== REC-08: close is idempotent / safe =====


def test_close_is_safe_to_call_twice(tmp_path: Path) -> None:
    """close() wraps all three handle-close in try/except — second close
    must not raise. v4:838-850."""
    rec = VoiceRecorder(root=tmp_path)
    rec.close()
    rec.close()  # must not raise
