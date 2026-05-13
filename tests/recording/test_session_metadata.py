# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 02 — session.json writer + crashed-session boot sweep.

Five tests, mirroring 15-02-PLAN.md Task 1 behavior block:

  1. VoiceRecorder.__init__ writes session.json with all 16 fields per CONTEXT
     Area 1 + autonomous resolution #5 (session_json_version="1.0" first).
  2. VoiceRecorder.close() rewrites session.json atomically with ended_at_iso,
     ended_at_unix, duration_s, and the three byte counts populated.
  3. Atomic write recipe survives mid-rewrite OSError — original file content
     stays intact (never half-written JSON).
  4. sweep_crashed_sessions marks sessions with ended_at_iso=None AND mtime
     older than mtime_age_s as crashed=True; leaves the active (young) session
     and the cleanly-closed session untouched.
  5. sweep_crashed_sessions is idempotent — running twice is a no-op on the
     already-marked session.

Tests use the `tmp_recordings_dir` + `make_fake_session` fixtures from
conftest.py.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

import pytest

from vibemix import __version__ as VIBEMIX_VERSION
from vibemix.audio.recorder import (
    SESSION_JSON_VERSION,
    VoiceRecorder,
    _atomic_write_json,
    sweep_crashed_sessions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_session_json(session_dir: Path) -> dict:
    return json.loads((session_dir / "session.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1: __init__ writes the 16-field session.json
# ---------------------------------------------------------------------------


def test_voice_recorder_writes_session_json_at_init(tmp_path: Path) -> None:
    """VoiceRecorder(root=tmp_path) writes session.json with all 16 fields,
    session_json_version="1.0", crashed=False, ended_at_iso=None."""
    rec = VoiceRecorder(
        root=tmp_path,
        voice_id="kore",
        mode="coach",
        genre="tech-house",
        user_level="pro",
    )
    try:
        session_json = rec.session_dir / "session.json"
        assert session_json.exists(), "session.json missing after __init__"
        meta = json.loads(session_json.read_text(encoding="utf-8"))

        # Locked field set per CONTEXT Area 1 + autonomous resolution #5.
        expected_keys = {
            "session_json_version",
            "vibemix_version",
            "started_at_iso",
            "started_at_unix",
            "ended_at_iso",
            "ended_at_unix",
            "duration_s",
            "voice",
            "mode",
            "genre",
            "user_level",
            "event_count",
            "voice_wav_bytes",
            "input_wav_bytes",
            "events_jsonl_bytes",
            "crashed",
        }
        assert set(meta.keys()) == expected_keys, (
            f"session.json keys mismatch: extras={set(meta.keys()) - expected_keys}, "
            f"missing={expected_keys - set(meta.keys())}"
        )

        assert meta["session_json_version"] == "1.0"
        assert meta["vibemix_version"] == VIBEMIX_VERSION
        assert meta["ended_at_iso"] is None
        assert meta["ended_at_unix"] is None
        assert meta["duration_s"] is None
        assert meta["voice"] == "kore"
        assert meta["mode"] == "coach"
        assert meta["genre"] == "tech-house"
        assert meta["user_level"] == "pro"
        assert meta["event_count"] == 0
        assert meta["voice_wav_bytes"] == 0
        assert meta["input_wav_bytes"] == 0
        assert meta["events_jsonl_bytes"] == 0
        assert meta["crashed"] is False
        # started_at_iso parses (ISO-8601 with milliseconds + tz)
        assert isinstance(meta["started_at_iso"], str)
        datetime.fromisoformat(meta["started_at_iso"])
        assert isinstance(meta["started_at_unix"], (int, float))
    finally:
        rec.close()


# ---------------------------------------------------------------------------
# Test 2: close() finalizes session.json with ended_at + byte counts
# ---------------------------------------------------------------------------


def test_voice_recorder_finalizes_session_json_at_close(tmp_path: Path) -> None:
    """close() rewrites session.json: ended_at_iso/ended_at_unix populated,
    duration_s = ended - started, and the three *_bytes match st_size."""
    rec = VoiceRecorder(root=tmp_path)
    # Push some bytes so the WAV/JSONL files have non-zero size.
    rec.push_voice(b"\x00\x00" * 12000)  # 24000 bytes = 0.5s at 24kHz mono int16
    rec.push_input(b"\x01\x01" * 8000)  # 16000 bytes = 0.5s at 16kHz mono int16
    rec.log_event("trigger", reason="test")
    rec.log_event("trigger", reason="test-2")
    rec.close()

    meta = _read_session_json(rec.session_dir)
    assert meta["ended_at_iso"] is not None
    assert meta["ended_at_unix"] is not None
    assert meta["duration_s"] is not None
    assert meta["duration_s"] >= 0.0
    # Allow a tiny float slop on the duration check.
    assert (
        abs(meta["duration_s"] - (meta["ended_at_unix"] - meta["started_at_unix"]))
        < 0.01
    )

    # Byte counts == actual st_size at close (each file flushed before stat).
    voice_size = (rec.session_dir / "voice.wav").stat().st_size
    input_size = (rec.session_dir / "input.wav").stat().st_size
    events_size = (rec.session_dir / "events.jsonl").stat().st_size
    assert meta["voice_wav_bytes"] == voice_size
    assert meta["input_wav_bytes"] == input_size
    assert meta["events_jsonl_bytes"] == events_size

    # event_count is at least the two trigger events (session_start is on the
    # JSONL line 0 — implementation may or may not count it; we accept ≥2).
    assert meta["event_count"] >= 2

    # crashed stayed False — clean close.
    assert meta["crashed"] is False


# ---------------------------------------------------------------------------
# Test 3: Atomic write survives mid-rewrite OSError
# ---------------------------------------------------------------------------


def test_atomic_write_survives_mid_rewrite_oserror(
    tmp_recordings_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When os.replace raises mid-rewrite, the original session.json content
    must be intact (not truncated, not partially-written)."""
    target = tmp_recordings_dir / "session.json"
    original = {"session_json_version": "1.0", "marker": "original"}
    target.write_text(json.dumps(original), encoding="utf-8")

    # Now attempt an atomic rewrite that will fail mid-operation.
    failing_data = {"session_json_version": "1.0", "marker": "should-not-land"}

    import vibemix.audio.recorder as recorder_mod

    def _raise(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(recorder_mod.os, "replace", _raise)

    with pytest.raises(OSError):
        _atomic_write_json(target, failing_data)

    # Original file content must be intact.
    surviving = json.loads(target.read_text(encoding="utf-8"))
    assert surviving == original, (
        f"original session.json was corrupted by failed atomic write: {surviving}"
    )

    # The .tmp file may or may not still exist — that's an implementation
    # detail. What matters is the canonical target is unchanged.


# ---------------------------------------------------------------------------
# Test 4: sweep_crashed_sessions marks stale unended sessions, leaves rest
# ---------------------------------------------------------------------------


def test_sweep_crashed_sessions_marks_stale_unended(
    tmp_recordings_dir: Path,
    make_fake_session: Callable[..., Path],
) -> None:
    """sweep_crashed_sessions(root, mtime_age_s=30) marks crashed=True on
    sessions where ended_at_iso=None AND mtime > 30s old. Active (young) and
    cleanly-closed sessions are LEFT ALONE."""
    stale_unended = make_fake_session(
        name="20260513-200000", ended=False, age_seconds=120
    )
    active_unended = make_fake_session(
        name="20260513-210000", ended=False, age_seconds=0
    )
    clean_ended = make_fake_session(
        name="20260513-205500", ended=True, age_seconds=60
    )

    marked = sweep_crashed_sessions(tmp_recordings_dir, mtime_age_s=30)

    # Only the stale unended dir got marked.
    assert "20260513-200000" in marked
    assert "20260513-210000" not in marked
    assert "20260513-205500" not in marked

    stale_meta = _read_session_json(stale_unended)
    assert stale_meta["crashed"] is True
    assert stale_meta["ended_at_iso"] is not None
    assert stale_meta["ended_at_unix"] is not None
    assert stale_meta["duration_s"] is not None
    assert stale_meta["duration_s"] >= 0.0

    # Active session untouched.
    active_meta = _read_session_json(active_unended)
    assert active_meta["crashed"] is False
    assert active_meta["ended_at_iso"] is None

    # Cleanly-closed session untouched.
    clean_meta = _read_session_json(clean_ended)
    assert clean_meta["crashed"] is False
    assert clean_meta["ended_at_iso"] is not None


# ---------------------------------------------------------------------------
# Test 5: sweep_crashed_sessions is idempotent
# ---------------------------------------------------------------------------


def test_sweep_crashed_sessions_is_idempotent(
    tmp_recordings_dir: Path,
    make_fake_session: Callable[..., Path],
) -> None:
    """Running sweep twice on the same recordings/ — the second call must
    not re-mark a session that already has crashed=True."""
    make_fake_session(name="20260513-200000", ended=False, age_seconds=120)

    first_pass = sweep_crashed_sessions(tmp_recordings_dir, mtime_age_s=30)
    second_pass = sweep_crashed_sessions(tmp_recordings_dir, mtime_age_s=30)

    assert "20260513-200000" in first_pass
    # On the second pass, ended_at_iso is now set (crashed=True rewrite filled
    # it from mtime), so the session no longer matches the "ended_at_iso=None"
    # predicate — it's not re-marked.
    assert "20260513-200000" not in second_pass


# ---------------------------------------------------------------------------
# Sentinel: sweep handles legacy dirs without session.json (Pitfall 9)
# + JSON-parse-failure dirs (best-effort, no raise)
# ---------------------------------------------------------------------------


def test_sweep_skips_dirs_without_session_json(tmp_recordings_dir: Path) -> None:
    """Phase 2-13 legacy dirs have no session.json — sweep must not raise
    (RESEARCH Pitfall 9). Same for JSON-parse-failure dirs."""
    legacy_dir = tmp_recordings_dir / "20240101-120000"
    legacy_dir.mkdir()
    (legacy_dir / "input.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

    busted_dir = tmp_recordings_dir / "20240202-120000"
    busted_dir.mkdir()
    (busted_dir / "session.json").write_text("{not valid json", encoding="utf-8")
    # Set busted dir mtime old enough to be a sweep candidate if parseable.
    now = datetime.now().timestamp()
    os.utime(busted_dir / "session.json", (now - 120, now - 120))

    marked = sweep_crashed_sessions(tmp_recordings_dir, mtime_age_s=30)
    assert marked == [] or "20240101-120000" not in marked
    assert "20240202-120000" not in marked
