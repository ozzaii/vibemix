# SPDX-License-Identifier: Apache-2.0
"""Tests for vibemix.audio.VoiceRecorder.

Verbatim port from cohost_v4.py:771-850 with the configurable-root
+ 0o700-perms improvements per 02-PATTERNS.md anti-patterns 4 and
RESEARCH.md Security V8.
"""

from __future__ import annotations

import json
import threading
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


def test_push_input_does_not_write_wav_on_caller_thread(tmp_path: Path, mocker) -> None:
    """Audio callbacks enqueue PCM; the recorder thread owns WAV writes."""
    rec = VoiceRecorder(root=tmp_path)
    pcm = np.full(1600, 1234, dtype=np.int16).tobytes()
    entered_write = threading.Event()
    release_write = threading.Event()
    returned = threading.Event()
    original_write = rec.input_wav.writeframesraw

    def blocking_write(data: bytes) -> None:
        entered_write.set()
        release_write.wait(timeout=1.0)
        original_write(data)

    mocker.patch.object(rec.input_wav, "writeframesraw", side_effect=blocking_write)

    def push() -> None:
        rec.push_input(pcm)
        returned.set()

    t = threading.Thread(target=push)
    try:
        t.start()
        assert returned.wait(timeout=0.2), "push_input blocked on wave.writeframes"
        assert entered_write.wait(timeout=1.0), "writer thread never consumed queued PCM"
    finally:
        release_write.set()
        t.join(timeout=1.0)
        rec.close()


def test_recorder_batches_short_input_writes(tmp_path: Path, mocker, monkeypatch) -> None:
    """Short callback bursts coalesce into fewer disk writes."""
    import vibemix.audio.recorder as rec_mod

    monkeypatch.setattr(rec_mod, "_WAV_BATCH_WAIT_S", 0.2)
    rec = VoiceRecorder(root=tmp_path)
    pcm = np.full(160, 1234, dtype=np.int16).tobytes()
    writes: list[int] = []
    original_write = rec.input_wav.writeframesraw

    def record_write(data: bytes) -> None:
        writes.append(len(data))
        original_write(data)

    mocker.patch.object(rec.input_wav, "writeframesraw", side_effect=record_write)

    try:
        rec.push_input(pcm)
        rec.push_input(pcm)
        rec.push_input(pcm)
    finally:
        rec.close()

    assert writes == [len(pcm) * 3]


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


# ===== REC-collision: two sessions in the same second get distinct dirs =====


def test_two_recorders_in_same_second_get_distinct_dirs(tmp_path, monkeypatch):
    """Two sessions starting in the same wall-clock second must NOT collide.

    The session dir is a second-granularity timestamp. A manual restart,
    double-launch, or crash-recovery relaunch within one second hit
    ``session_dir.mkdir()`` (no exist_ok) and raised FileExistsError, aborting
    boot (caught live 2026-05-30 on the frozen sidecar). Each session must keep
    its OWN dir (exist_ok=True would let them clobber each other's recordings).
    """
    from datetime import datetime as _dt

    import vibemix.audio.recorder as rec_mod

    fixed = _dt(2026, 5, 30, 20, 24, 21)

    class _FrozenDatetime(_dt):
        @classmethod
        def now(cls, *args, **kwargs):  # type: ignore[override]
            return fixed

    monkeypatch.setattr(rec_mod, "datetime", _FrozenDatetime)
    r1 = rec_mod.VoiceRecorder(root=tmp_path)
    r2 = rec_mod.VoiceRecorder(root=tmp_path)  # same second — must not raise
    try:
        assert r1.session_dir != r2.session_dir, "second session reused the first's dir"
        assert r1.session_dir.exists()
        assert r2.session_dir.exists()
    finally:
        r1.close()
        r2.close()
