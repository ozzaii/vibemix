# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 06 — 60-min synthetic soak test.

Runs via ``pytest -m slow tests/recording/test_60min_soak.py``.
Deselected from the default test run (`pytest -m "not slow"`).

Asserts REC-01/02/03/04 invariants hold under a full-duration session:

  - input.wav: 60s ± 1s duration via ``wave.open().getnframes() / 16000``
  - voice.wav: 60s ± 1s duration via ``wave.open().getnframes() / 24000``
  - events.jsonl: 200 logged + 1 session_start header = 201 lines; every
    line parses as JSON; ``t`` values monotonically non-decreasing across
    the whole file
  - session.json: ``started_at_unix == first JSONL line's wall_clock_unix``;
    ``ended_at_iso`` not None (close finalizer ran); ``duration_s`` is the
    wall-clock duration of the synchronous loop (NOT a function of WAV
    frame counts — the test feeds frames as fast as it can; the
    finalizer's duration comes from ``time.time()`` deltas).
  - ``session_json_version`` field present (autonomous resolution #5)
  - ``tracemalloc`` peak < 200MB — RESEARCH Pitfall 6 belt-and-braces

The soak streams in 100ms chunks (1600 frames @16kHz, 2400 frames @24kHz)
so wall-clock stays <60s and peak RSS stays bounded — the chunk buffers
are pre-allocated once and reused, so allocator pressure is dominated by
the wave-module internal buffering rather than test-side growth.

Why two assertions for duration:
  * input.wav / voice.wav duration is a function of the bytes written —
    36000 chunks × 100ms == 60s exactly. ±1s tolerance covers any
    final-chunk rounding from wave.close()'s RIFF length patch.
  * session.json's ``duration_s`` is wall-clock — how long the test loop
    took. That's also ~60s but tracks differently from WAV frames.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import tracemalloc
import wave
from pathlib import Path

import numpy as np
import pytest

from vibemix.audio.recorder import VoiceRecorder


# ---------------------------------------------------------------------------
# Constants — RESEARCH Pitfall 6 chunking math
# ---------------------------------------------------------------------------

CHUNK_MS = 100
TOTAL_DURATION_S = 60 * 60  # 60 minutes
NUM_CHUNKS = (TOTAL_DURATION_S * 1000) // CHUNK_MS  # 36000

INPUT_RATE = 16000
VOICE_RATE = 24000

INPUT_FRAMES_PER_CHUNK = (INPUT_RATE * CHUNK_MS) // 1000  # 1600
VOICE_FRAMES_PER_CHUNK = (VOICE_RATE * CHUNK_MS) // 1000  # 2400

# 200 log_event calls spread uniformly across 36000 chunk iterations →
# log every 180 chunks.
TOTAL_EVENTS = 200
EVENT_EVERY = NUM_CHUNKS // TOTAL_EVENTS  # 180

DURATION_TOLERANCE_S = 1.0
MEMORY_BUDGET_BYTES = 200 * 1000 * 1000  # 200MB


# ---------------------------------------------------------------------------
# Test 1 — the soak. session_json_version field check lives in here too.
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_60min_soak_wav_jsonl_session_json_invariants(tmp_path: Path) -> None:
    """60-minute synthetic recording — pins WAV durations, JSONL monotonicity,
    session.json wall-clock match, and tracemalloc memory ceiling."""
    tracemalloc.start()
    try:
        recorder = VoiceRecorder(
            root=tmp_path,
            voice_id="Aoede",
            mode="hype",
            genre="techno",
            user_level="intermediate",
        )

        # Pre-allocate ONE chunk per rate — reused across 36000 iterations.
        # np.zeros() returns a fresh buffer; .tobytes() copies into the
        # immutable bytes payload that wave.writeframes consumes.
        chunk_input = np.zeros(INPUT_FRAMES_PER_CHUNK, dtype=np.int16).tobytes()
        chunk_voice = np.zeros(VOICE_FRAMES_PER_CHUNK, dtype=np.int16).tobytes()

        for i in range(NUM_CHUNKS):
            recorder.push_input(chunk_input)
            recorder.push_voice(chunk_voice)
            if i % EVENT_EVERY == 0:
                recorder.log_event("synthetic", iter=i)

        recorder.close()
        session_dir = recorder.session_dir

        # -------------------------------------------------------------------
        # input.wav — 60s ± 1s duration
        # -------------------------------------------------------------------
        with wave.open(str(session_dir / "input.wav"), "rb") as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            assert w.getframerate() == INPUT_RATE
            input_frames = w.getnframes()
        input_duration = input_frames / float(INPUT_RATE)
        assert abs(input_duration - TOTAL_DURATION_S) <= DURATION_TOLERANCE_S, (
            f"input.wav duration {input_duration:.3f}s "
            f"deviates >{DURATION_TOLERANCE_S}s from 60min"
        )

        # -------------------------------------------------------------------
        # voice.wav — 60s ± 1s duration
        # -------------------------------------------------------------------
        with wave.open(str(session_dir / "voice.wav"), "rb") as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            assert w.getframerate() == VOICE_RATE
            voice_frames = w.getnframes()
        voice_duration = voice_frames / float(VOICE_RATE)
        assert abs(voice_duration - TOTAL_DURATION_S) <= DURATION_TOLERANCE_S, (
            f"voice.wav duration {voice_duration:.3f}s "
            f"deviates >{DURATION_TOLERANCE_S}s from 60min"
        )

        # -------------------------------------------------------------------
        # events.jsonl — 201 lines, all parseable, monotonic `t`
        # -------------------------------------------------------------------
        events_path = session_dir / "events.jsonl"
        lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # 200 logged events + 1 session_start header = 201.
        assert len(lines) == TOTAL_EVENTS + 1, (
            f"events.jsonl line count {len(lines)} != {TOTAL_EVENTS + 1} "
            f"(expected {TOTAL_EVENTS} logged + 1 session_start header)"
        )

        parsed = [json.loads(ln) for ln in lines]  # raises on malformed line

        # Monotonic `t` across the whole file (session_start is t=0.0).
        prev_t = -float("inf")
        for idx, rec in enumerate(parsed):
            t = rec["t"]
            assert isinstance(t, (int, float)), f"line {idx}: t={t!r} not numeric"
            assert t >= prev_t, (
                f"events.jsonl line {idx}: t={t} < previous t={prev_t} "
                f"(monotonic non-decreasing violated)"
            )
            prev_t = t

        # First line is the canonical session_start header.
        first = parsed[0]
        assert first["kind"] == "session_start"
        assert first["t"] == 0.0
        assert isinstance(first["wall_clock_unix"], float)

        # -------------------------------------------------------------------
        # session.json — wall-clock anchor matches; finalizer ran
        # -------------------------------------------------------------------
        meta_path = session_dir / "session.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        assert "session_json_version" in meta
        assert meta["session_json_version"] == "1.0"
        assert meta["started_at_unix"] == first["wall_clock_unix"], (
            f"session.json.started_at_unix ({meta['started_at_unix']}) != "
            f"events.jsonl session_start.wall_clock_unix ({first['wall_clock_unix']})"
        )
        assert meta["ended_at_iso"] is not None, (
            "close() must populate ended_at_iso via _finalize_session_meta — "
            "absent value would mark the session as crashed on next-boot sweep."
        )
        assert isinstance(meta["duration_s"], (int, float))
        assert meta["duration_s"] >= 0.0
        # event_count comes from a fresh JSONL line count (line_count - 1
        # for the session_start marker), per _finalize_session_meta.
        assert meta["event_count"] == TOTAL_EVENTS, (
            f"session.json.event_count {meta['event_count']} != {TOTAL_EVENTS}"
        )
        assert meta["crashed"] is False

        # -------------------------------------------------------------------
        # tracemalloc — peak < 200MB
        # -------------------------------------------------------------------
        _current, peak = tracemalloc.get_traced_memory()
        assert peak < MEMORY_BUDGET_BYTES, (
            f"tracemalloc peak {peak / 1_000_000:.1f}MB "
            f"exceeded budget {MEMORY_BUDGET_BYTES / 1_000_000:.0f}MB"
        )
    finally:
        tracemalloc.stop()


# ---------------------------------------------------------------------------
# Test 2 — sanity check: the slow test is deselected by default
# ---------------------------------------------------------------------------


def test_slow_marker_deselects_soak_from_default_pytest_run() -> None:
    """Running `pytest -m "not slow" --collect-only` against THIS file
    deselects the soak. Belt-and-braces guarantee that the default CI
    matrix does not accidentally execute the 60-min loop.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "not slow",
            "-q",
            str(Path(__file__)),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Either the test is deselected (visible in stdout) OR pytest reports
    # "no tests ran" — both are valid signals that the slow marker is
    # filtering the soak out.
    out = (result.stdout + result.stderr).lower()
    assert "deselect" in out or "no tests" in out or "no tests ran" in out, (
        "pytest -m 'not slow' should deselect the soak test; "
        f"got rc={result.returncode}, stdout/stderr did not mention "
        f"deselection.\nFULL OUTPUT:\n{out[:2000]}"
    )
